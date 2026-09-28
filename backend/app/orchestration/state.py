"""Typed state passed between every LangGraph node. Never pass raw dicts
between nodes — always these Pydantic models, per spec §45 (Agent State Safety)."""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel


class TaskSpec(BaseModel):
    id: str
    description: str
    agent: str  # "research_agent" | "data_agent" | "verification_agent" | "report_agent"
    dependencies: list[str] = []
    required_tools: list[str] = []
    priority: int = 1
    status: str = "pending"  # pending | running | done | failed
    retry_count: int = 0


class Plan(BaseModel):
    goal: str
    tasks: list[TaskSpec]


class TaskResult(BaseModel):
    task_id: str
    agent: str
    output: dict | None = None
    error: str | None = None
    tool_calls: list[dict] = []


class VerificationResult(BaseModel):
    task_id: str
    passed: bool
    issues: list[str] = []


class ApprovalDecision(BaseModel):
    approval_id: str
    approved: bool


class ExecutionMetadata(BaseModel):
    request_id: str
    workflow_id: str
    execution_id: str
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    replan_count: int = 0


class Report(BaseModel):
    summary: str
    sections: list[dict] = []
    format: str = "markdown"


def _merge_dicts(a: dict, b: dict) -> dict:
    return {**a, **b}


class AgentState(TypedDict, total=False):
    organization_id: str
    user_id: str
    conversation_id: str
    workflow_execution_id: str
    goal: str
    plan: Plan | None
    current_task_id: str | None
    completed_tasks: Annotated[list[TaskResult], operator.add]
    failed_tasks: Annotated[list[TaskResult], operator.add]
    tool_results: Annotated[list[dict], operator.add]
    agent_outputs: Annotated[dict[str, Any], _merge_dicts]
    verification_results: Annotated[list[VerificationResult], operator.add]
    pending_approval: dict | None
    approvals: Annotated[list[ApprovalDecision], operator.add]
    memories: list[dict]
    final_output: Report | None
    execution_metadata: ExecutionMetadata
    status: str  # planning | executing | verifying | awaiting_approval | replanning | done | failed
