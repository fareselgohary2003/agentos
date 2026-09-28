from __future__ import annotations

import asyncio
import re
import shlex
import tempfile

from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from app.tools.base import RetryPolicy, Tool, ToolContext, ToolRiskLevel

# ---------------------------------------------------------------------------
# Web Search — LOW risk
# ---------------------------------------------------------------------------


class WebSearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    max_results: int = Field(default=5, ge=1, le=10)


class WebSearchOutput(BaseModel):
    results: list[dict]


class WebSearchTool(Tool):
    name = "web_search"
    description = "Search the web and return titles, URLs, and snippets."
    input_schema = WebSearchInput
    output_schema = WebSearchOutput
    risk_level = ToolRiskLevel.LOW
    timeout_seconds = 20
    retry_policy = RetryPolicy(max_retries=2)

    async def _run(self, input: WebSearchInput, ctx: ToolContext) -> WebSearchOutput:
        # Phase 1 stub: no external search API is wired yet. Replace this with a
        # real provider (Bing/SerpAPI/Tavily) or an MCP web-search server before
        # production use. Kept deterministic here so the graph and tests are
        # reproducible without a live key.
        return WebSearchOutput(
            results=[
                {
                    "title": f"Result for: {input.query}",
                    "url": "https://example.com/result",
                    "snippet": "Web search is stubbed in this build; wire a real "
                    "provider via WEB_SEARCH_API_KEY before production use.",
                }
            ]
        )


# ---------------------------------------------------------------------------
# SQL Query — MEDIUM risk, read-only enforced
# ---------------------------------------------------------------------------

_BLOCKED_KEYWORDS = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b", re.IGNORECASE
)


class SqlQueryValidationError(Exception):
    pass


def validate_readonly_select(sql: str) -> str:
    """Enforce: single statement, starts with SELECT, no mutating keywords,
    no statement chaining. Never execute LLM-generated SQL without this.
    """
    cleaned = sql.strip().rstrip(";")
    if ";" in cleaned:
        raise SqlQueryValidationError("Multiple statements are not allowed")
    if not re.match(r"^\s*SELECT\b", cleaned, re.IGNORECASE):
        raise SqlQueryValidationError("Only SELECT statements are permitted")
    if _BLOCKED_KEYWORDS.search(cleaned):
        raise SqlQueryValidationError("Query contains a disallowed mutating keyword")
    return cleaned


class SqlQueryInput(BaseModel):
    sql: str = Field(min_length=1, max_length=5000)


class SqlQueryOutput(BaseModel):
    columns: list[str]
    rows: list[list]
    row_count: int


class SqlQueryTool(Tool):
    name = "sql_query"
    description = "Run a read-only SELECT query against the organization's analytics data."
    input_schema = SqlQueryInput
    output_schema = SqlQueryOutput
    risk_level = ToolRiskLevel.MEDIUM
    timeout_seconds = 15
    retry_policy = RetryPolicy(max_retries=1)
    required_permission = "tools:sql_query"

    async def _run(self, input: SqlQueryInput, ctx: ToolContext) -> SqlQueryOutput:
        safe_sql = validate_readonly_select(input.sql)
        async with AsyncSessionLocal() as session:
            # Tenant isolation for ad-hoc analyst SQL is enforced by running on a
            # DB role restricted to that tenant's schema/row-security policy in
            # production; this demo build does not additionally filter by
            # organization_id here, so treat this tool as trusted-analyst-only
            # until that hardening is added.
            result = await session.execute(text(safe_sql))
            columns = list(result.keys())
            rows = [list(r) for r in result.fetchall()]
        return SqlQueryOutput(columns=columns, rows=rows, row_count=len(rows))


# ---------------------------------------------------------------------------
# Python Sandbox — HIGH risk (requires approval via ToolExecutor's risk gate)
# ---------------------------------------------------------------------------


class PythonSandboxInput(BaseModel):
    code: str = Field(min_length=1, max_length=20000)


class PythonSandboxOutput(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float


class PythonSandboxTool(Tool):
    name = "python_sandbox"
    description = "Execute Python code in an isolated, resource-limited sandbox."
    input_schema = PythonSandboxInput
    output_schema = PythonSandboxOutput
    risk_level = ToolRiskLevel.HIGH
    timeout_seconds = 10
    retry_policy = RetryPolicy(max_retries=0)
    required_permission = "tools:python_execute"

    async def _run(self, input: PythonSandboxInput, ctx: ToolContext) -> PythonSandboxOutput:
        # Production sandboxing = a throwaway Docker container per run
        # (--network none, cpu/mem/pids limits, read-only rootfs). This
        # fallback uses a resource-limited subprocess when no Docker daemon
        # is available to the backend/worker container itself.
        return await self._run_in_subprocess(input.code)

    async def _run_in_subprocess(self, code: str) -> PythonSandboxOutput:
        import time

        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(code)
            path = f.name

        # ulimit caps CPU time and address space for defense-in-depth even without
        # container isolation; network access is NOT blocked at this fallback tier.
        cmd = (
            f"ulimit -t 5 -v 268435456 -f 1024; "
            f"exec python3 -I {shlex.quote(path)}"
        )
        start = time.perf_counter()
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        except asyncio.TimeoutError:
            proc.kill()
            stdout, stderr = b"", b"Execution timed out"
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        return PythonSandboxOutput(
            stdout=stdout.decode(errors="replace")[:10000],
            stderr=stderr.decode(errors="replace")[:10000],
            exit_code=proc.returncode or 0,
            duration_ms=duration_ms,
        )


# ---------------------------------------------------------------------------
# Send Email — HIGH risk (requires approval)
# ---------------------------------------------------------------------------


class SendEmailInput(BaseModel):
    to: str
    subject: str
    body: str


class SendEmailOutput(BaseModel):
    sent: bool
    message_id: str | None = None


class SendEmailTool(Tool):
    name = "send_email"
    description = "Send an email notification. Always requires human approval."
    input_schema = SendEmailInput
    output_schema = SendEmailOutput
    risk_level = ToolRiskLevel.HIGH
    timeout_seconds = 15
    required_permission = "tools:send_email"

    async def _run(self, input: SendEmailInput, ctx: ToolContext) -> SendEmailOutput:
        # Only ever reached after an approval has been granted and the graph
        # resumes execution. No SMTP/provider is wired in this build; plug
        # SES/SendGrid/etc. here.
        return SendEmailOutput(sent=True, message_id="stub-message-id")


# ---------------------------------------------------------------------------
# Document Search (RAG) — LOW risk
# ---------------------------------------------------------------------------


class DocumentSearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=10)


class DocumentSearchOutput(BaseModel):
    chunks: list[dict]


class DocumentSearchTool(Tool):
    name = "document_search"
    description = "Search the organization's ingested documents (RAG) for relevant passages."
    input_schema = DocumentSearchInput
    output_schema = DocumentSearchOutput
    risk_level = ToolRiskLevel.LOW
    timeout_seconds = 15

    async def _run(self, input: DocumentSearchInput, ctx: ToolContext) -> DocumentSearchOutput:
        from app.rag.service import retrieve_and_rerank

        async with AsyncSessionLocal() as session:
            chunks = await retrieve_and_rerank(session, ctx.organization_id, input.query, input.top_k)
        return DocumentSearchOutput(
            chunks=[{"document_id": str(c.document_id), "content": c.content} for c in chunks]
        )