from __future__ import annotations

import abc
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel


class ToolRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RetryPolicy:
    max_retries: int = 2
    backoff_seconds: float = 1.0


@dataclass
class ToolContext:
    organization_id: uuid.UUID
    user_id: uuid.UUID
    agent_id: str
    workflow_execution_id: str
    granted_permissions: set[str]


@dataclass
class ToolResult:
    tool_call_id: str
    tool_name: str
    success: bool
    output: dict | None
    error: str | None
    duration_ms: float
    requires_approval: bool = False


class Tool(abc.ABC):
    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    risk_level: ToolRiskLevel = ToolRiskLevel.LOW
    timeout_seconds: int = 30
    retry_policy: RetryPolicy = RetryPolicy()
    required_permission: str | None = None  # e.g. "tools:send_email"

    @abc.abstractmethod
    async def _run(self, input: BaseModel, ctx: ToolContext) -> BaseModel: ...


class ToolPermissionError(Exception):
    pass


class ToolExecutor:
    """Single choke point every tool call goes through: validate -> permission check
    -> risk gate (HIGH/CRITICAL requires approval, handled by the orchestration layer,
    which sees `requires_approval=True` and pauses instead of executing) -> timeout+retry
    -> output validation.
    """

    def __init__(self, on_approval_required=None):
        self._on_approval_required = on_approval_required

    async def execute(
        self, tool: Tool, raw_input: dict, ctx: ToolContext, approved: bool = False
    ) -> ToolResult:
        tool_call_id = str(uuid.uuid4())
        start = time.perf_counter()

        try:
            validated_input = tool.input_schema.model_validate(raw_input)
        except Exception as exc:  # pydantic ValidationError
            return ToolResult(tool_call_id, tool.name, False, None, f"Invalid input: {exc}", 0)

        if tool.required_permission and tool.required_permission not in ctx.granted_permissions:
            return ToolResult(
                tool_call_id, tool.name, False, None,
                f"Missing permission: {tool.required_permission}", 0,
            )

        if tool.risk_level in (ToolRiskLevel.HIGH, ToolRiskLevel.CRITICAL) and not approved:
            # HIGH/CRITICAL tools never auto-execute; the orchestration graph
            # calls LangGraph's real interrupt() and pauses until a human
            # approves — see app/orchestration/graph.py's approval_gate_node.
            # `approved=True` (passed only after a real approval decision) is
            # what lets this same call proceed past this gate on resume.
            return ToolResult(
                tool_call_id, tool.name, False, None, None, 0, requires_approval=True
            )

        last_error: str | None = None
        for attempt in range(tool.retry_policy.max_retries + 1):
            try:
                output = await asyncio.wait_for(
                    tool._run(validated_input, ctx), timeout=tool.timeout_seconds
                )
                tool.output_schema.model_validate(output.model_dump())
                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                return ToolResult(tool_call_id, tool.name, True, output.model_dump(), None, duration_ms)
            except asyncio.TimeoutError:
                last_error = f"Tool timed out after {tool.timeout_seconds}s"
            except Exception as exc:
                last_error = str(exc)
            if attempt < tool.retry_policy.max_retries:
                await asyncio.sleep(tool.retry_policy.backoff_seconds * (attempt + 1))

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        return ToolResult(tool_call_id, tool.name, False, None, last_error, duration_ms)
