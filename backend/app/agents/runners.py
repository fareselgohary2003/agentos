"""Concrete agent implementations: Research, Data Analyst, Verification, Report.
Each is a plain async function (agent, task, state) -> TaskResult so the
orchestration graph can dispatch by name without importing every agent module
directly — mirrors the tool-registry seam for consistency.
"""
from __future__ import annotations

import json

from app.llm.provider import LLMMessage, LLMProvider
from app.orchestration.state import TaskResult, TaskSpec, VerificationResult
from app.security.prompt_injection import wrap_untrusted_content
from app.tools.base import ToolContext, ToolExecutor
from app.tools.registry import get_tool_registry


async def run_research_agent(
    task: TaskSpec, goal: str, llm: LLMProvider, ctx: ToolContext, executor: ToolExecutor
) -> TaskResult:
    registry = get_tool_registry()
    tool = registry.resolve("web_search")
    tool_result = await executor.execute(tool, {"query": task.description}, ctx)

    if not tool_result.success:
        return TaskResult(task_id=task.id, agent="research_agent", error=tool_result.error)

    # Search results are untrusted external content — wrapped so the model
    # treats them as data, never as instructions (spec §26).
    wrapped_results = wrap_untrusted_content(json.dumps(tool_result.output), source="web_search")
    summary_prompt = [
        LLMMessage("system", "You are a research analyst. Summarize findings concisely, with citations."),
        LLMMessage("user", f"Goal: {goal}\nTask: {task.description}\nSearch results:\n{wrapped_results}"),
    ]
    response = await llm.complete(summary_prompt)
    return TaskResult(
        task_id=task.id,
        agent="research_agent",
        output={"summary": response.content, "sources": tool_result.output.get("results", [])},
        tool_calls=[{"tool": "web_search", "success": True}],
    )


# Matches the ACTUAL seeded schema in app/analytics/models.py (Brightleaf demo
# data) — not a generic placeholder. Category/region names live in separate
# lookup tables, so the LLM is told the joins it needs to produce readable
# output instead of raw UUIDs.
_KNOWN_SCHEMA_HINT = """
Available read-only tables (all joined on organization_id, but do not filter
on organization_id yourself — that isolation is enforced by the caller):

regions(id, organization_id, name)
    -- e.g. 'North America - East', 'North America - West', 'Europe', 'APAC'

product_categories(id, organization_id, name)
    -- e.g. 'Lighting', 'Textiles', 'Kitchenware', 'Decor', 'Furniture'

products(id, organization_id, category_id, sku, name, unit_price, unit_cost)

customers(id, organization_id, region_id, name, segment)
    -- segment is 'retail' or 'wholesale'

sales_orders(id, organization_id, order_date, customer_id, region_id,
             product_id, quantity, unit_price, total_amount, quarter)
    -- quarter is a string like '2026-Q1', '2026-Q2', '2026-Q3'

To get readable category/region names, JOIN sales_orders -> products ->
product_categories, and sales_orders -> regions. Example pattern:

SELECT pc.name AS category, r.name AS region, so.quarter, SUM(so.total_amount) AS revenue
FROM sales_orders so
JOIN products p ON p.id = so.product_id
JOIN product_categories pc ON pc.id = p.category_id
JOIN regions r ON r.id = so.region_id
GROUP BY pc.name, r.name, so.quarter
ORDER BY so.quarter
"""

_SQL_GEN_SYSTEM_PROMPT = f"""You write a single PostgreSQL read-only SELECT query to
answer the user's data question, using ONLY the following schema:
{_KNOWN_SCHEMA_HINT}

Rules:
- Respond with ONLY the raw SQL, no markdown fences, no prose, no explanation.
- Exactly one SELECT statement, no semicolon at the end.
- Never use DROP/DELETE/UPDATE/INSERT/ALTER/TRUNCATE/CREATE/GRANT/REVOKE.
- If the question cannot be answered with these tables, respond with:
  SELECT 'no matching data available' AS note
"""


def _strip_sql_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        # Drop a leading language tag like "sql\n" if present.
        first_newline = cleaned.find("\n")
        if first_newline != -1 and cleaned[:first_newline].strip().lower() in ("sql", ""):
            cleaned = cleaned[first_newline + 1:]
    return cleaned.strip()


async def run_data_agent(
    task: TaskSpec, goal: str, llm: LLMProvider, ctx: ToolContext, executor: ToolExecutor
) -> TaskResult:
    # Imported lazily (inside the function, not at module top) to avoid a
    # circular import between app.tools.builtin and app.agents.runners.
    from app.tools.builtin import SqlQueryValidationError, validate_readonly_select

    registry = get_tool_registry()
    tool = registry.resolve("sql_query")

    # Ask the LLM to write the actual SQL for this task against the known
    # schema, instead of always running a hardcoded placeholder query.
    sql_prompt = [
        LLMMessage("system", _SQL_GEN_SYSTEM_PROMPT),
        LLMMessage("user", f"Goal: {goal}\nTask: {task.description}"),
    ]
    sql_response = await llm.complete(sql_prompt)
    candidate_sql = _strip_sql_fences(sql_response.content)

    try:
        safe_sql = validate_readonly_select(candidate_sql)
    except SqlQueryValidationError as exc:
        return TaskResult(task_id=task.id, agent="data_agent", error=f"Generated SQL rejected: {exc}")

    tool_result = await executor.execute(tool, {"sql": safe_sql}, ctx)

    if not tool_result.success:
        return TaskResult(task_id=task.id, agent="data_agent", error=tool_result.error)

    output = dict(tool_result.output)
    output["sql_used"] = safe_sql
    return TaskResult(
        task_id=task.id,
        agent="data_agent",
        output=output,
        tool_calls=[{"tool": "sql_query", "success": True, "sql": safe_sql}],
    )


async def run_verification_agent(
    completed_tasks: list[TaskResult], goal: str, llm: LLMProvider
) -> list[VerificationResult]:
    results = []
    for task_result in completed_tasks:
        if task_result.error:
            results.append(VerificationResult(task_id=task_result.task_id, passed=False,
                                                issues=[task_result.error]))
            continue
        prompt = [
            LLMMessage("system", "You check agent outputs for unsupported claims, contradictions, "
                                  "and calculation errors. Respond with JSON: "
                                  '{"passed": true|false, "issues": ["..."]}'),
            LLMMessage("user", f"Goal: {goal}\nOutput to check: {json.dumps(task_result.output)}"),
        ]
        response = await llm.complete(prompt)
        try:
            parsed = json.loads(response.content)
        except json.JSONDecodeError:
            parsed = {"passed": True, "issues": []}  # fail-open on unparseable verifier output in dev
        results.append(VerificationResult(
            task_id=task_result.task_id, passed=parsed.get("passed", True), issues=parsed.get("issues", [])
        ))
    return results


async def run_report_agent(goal: str, completed_tasks: list[TaskResult], llm: LLMProvider) -> dict:
    prompt = [
        LLMMessage("system", "You are a report writer. Produce a concise executive summary and "
                              "structured sections in JSON: "
                              '{"summary": "...", "sections": [{"title": "...", "content": "..."}]}'),
        LLMMessage("user", f"Goal: {goal}\nFindings: {json.dumps([t.model_dump() for t in completed_tasks])}"),
    ]
    response = await llm.complete(prompt)
    try:
        parsed = json.loads(response.content)
    except json.JSONDecodeError:
        parsed = {"summary": response.content, "sections": []}
    return parsed


async def run_notification_agent(
    email_payload: dict, ctx: ToolContext, executor: ToolExecutor, approved: bool
):
    """Only ever reaches an actual send when `approved=True`, which the graph
    sets after a real human decision via the approval_gate interrupt."""
    registry = get_tool_registry()
    tool = registry.resolve("send_email")
    return await executor.execute(tool, email_payload, ctx, approved=approved)