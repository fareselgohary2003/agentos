from __future__ import annotations

import asyncio
import uuid

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from app.agents.runners import (
    run_data_agent, run_notification_agent, run_report_agent, run_research_agent,
    run_verification_agent,
)
from app.llm.provider import LLMProvider, get_llm_provider
from app.orchestration.planner import generate_plan
from app.orchestration.state import AgentState, Report, TaskResult
from app.tools.base import ToolContext, ToolExecutor

MAX_REPLANS = 2

_AGENT_DISPATCH = {
    "research_agent": run_research_agent,
    "data_agent": run_data_agent,
}


def _build_tool_context(state: AgentState) -> ToolContext:
    return ToolContext(
        organization_id=uuid.UUID(state["organization_id"]),
        user_id=uuid.UUID(state["user_id"]),
        agent_id="supervisor",
        workflow_execution_id=state["workflow_execution_id"],
        granted_permissions={"tools:sql_query", "tools:python_execute", "tools:send_email"},
    )


async def understand_node(state: AgentState, llm: LLMProvider) -> dict:
    # Placeholder for intent/constraint extraction; kept as an explicit graph
    # stage (rather than folded into planning) so prompt-injection screening on
    # the raw goal text can be inserted here later without touching the planner.
    return {"status": "planning"}


async def plan_node(state: AgentState, llm: LLMProvider) -> dict:
    plan = await generate_plan(state["goal"], llm)
    return {"plan": plan, "status": "executing"}


async def execute_node(state: AgentState, llm: LLMProvider) -> dict:
    plan = state["plan"]
    ctx = _build_tool_context(state)
    executor = ToolExecutor()

    completed_ids = {t.task_id for t in state.get("completed_tasks", [])}
    runnable = [
        t for t in plan.tasks
        if t.id not in completed_ids
        and t.agent in _AGENT_DISPATCH
        and all(dep in completed_ids for dep in t.dependencies)
    ]

    # Independent tasks execute concurrently (spec §10) rather than sequentially.
    results: list[TaskResult] = await asyncio.gather(
        *[_AGENT_DISPATCH[t.agent](t, state["goal"], llm, ctx, executor) for t in runnable]
    )

    completed = [r for r in results if r.error is None]
    failed = [r for r in results if r.error is not None]
    return {"completed_tasks": completed, "failed_tasks": failed}


async def verify_node(state: AgentState, llm: LLMProvider) -> dict:
    completed = state.get("completed_tasks", [])
    verifications = await run_verification_agent(completed, state["goal"], llm)
    return {"verification_results": verifications, "status": "verifying"}


def _plan_fully_satisfied(state: AgentState) -> bool:
    plan = state["plan"]
    completed_ids = {t.task_id for t in state.get("completed_tasks", [])}
    report_or_verification_agents = {"report_agent", "verification_agent"}
    core_tasks = [t for t in plan.tasks if t.agent not in report_or_verification_agents]
    return all(t.id in completed_ids for t in core_tasks)


def route_after_verify(state: AgentState) -> str:
    verifications = state.get("verification_results", [])
    any_failed = any(not v.passed for v in verifications)
    replans_so_far = state["execution_metadata"].replan_count

    if any_failed and replans_so_far < MAX_REPLANS:
        return "replan"
    if not _plan_fully_satisfied(state):
        return "execute"  # more independent tasks may now be unblocked
    return "report"


async def replan_node(state: AgentState, llm: LLMProvider) -> dict:
    failure_context = "; ".join(
        issue for v in state.get("verification_results", []) if not v.passed for issue in v.issues
    ) or "verification failed"
    new_plan = await generate_plan(state["goal"], llm, failure_context=failure_context)
    metadata = state["execution_metadata"]
    metadata.replan_count += 1
    return {"plan": new_plan, "execution_metadata": metadata, "status": "replanning"}


async def report_node(state: AgentState, llm: LLMProvider) -> dict:
    completed = state.get("completed_tasks", [])
    report_dict = await run_report_agent(state["goal"], completed, llm)
    report = Report(
        summary=report_dict.get("summary", ""),
        sections=report_dict.get("sections", []),
    )
    return {"final_output": report, "status": "done"}


async def approval_gate_node(state: AgentState, llm: LLMProvider) -> dict:
    """The real human-in-the-loop pause. `interrupt()` suspends the graph here
    — genuinely, via LangGraph's own mechanism, checkpointed to Postgres — and
    `graph.ainvoke(Command(resume=...))` is what continues past this exact
    point later, from a different process if needed (proven in
    docs/architecture/00-design.md §8's restart test).
    """
    final_output = state.get("final_output")
    if final_output is None:
        return {"status": "done"}

    email_payload = {
        "to": "leadership@example.com",
        "subject": f"Report: {state['goal'][:80]}",
        "body": final_output.summary,
    }

    decision = interrupt({
        "action": "send_email",
        "risk_level": "high",
        "payload": email_payload,
        "requested_by_agent": "notification_agent",
        "task_id": "notify",
    })
    approved = bool(decision.get("approved")) if isinstance(decision, dict) else bool(decision)

    ctx = _build_tool_context(state)
    executor = ToolExecutor()
    result = await run_notification_agent(email_payload, ctx, executor, approved=approved)

    return {
        "status": "done" if approved else "rejected",
        "agent_outputs": {"notification": result.output or {"sent": False, "error": result.error}},
    }


def build_supervisor_graph(llm: LLMProvider | None = None, checkpointer=None):
    """Compiled once per invocation with the LLM bound via closures, so the same
    graph shape works with any provider (spec §24) without rebuilding per-call.

    `checkpointer` defaults to an in-memory MemorySaver for quick/local use;
    pass a real `AsyncPostgresSaver` (see app/workers/tasks.py) so the
    approval_gate's interrupt survives a process restart in production —
    proven end to end in a two-process test documented in the architecture doc.
    """
    llm = llm or get_llm_provider()

    async def _understand(s: AgentState) -> dict:
        return await understand_node(s, llm)

    async def _plan(s: AgentState) -> dict:
        return await plan_node(s, llm)

    async def _execute(s: AgentState) -> dict:
        return await execute_node(s, llm)

    async def _verify(s: AgentState) -> dict:
        return await verify_node(s, llm)

    async def _replan(s: AgentState) -> dict:
        return await replan_node(s, llm)

    async def _report(s: AgentState) -> dict:
        return await report_node(s, llm)

    async def _approval_gate(s: AgentState) -> dict:
        return await approval_gate_node(s, llm)

    graph = StateGraph(AgentState)
    graph.add_node("understand", _understand)
    graph.add_node("plan", _plan)
    graph.add_node("execute", _execute)
    graph.add_node("verify", _verify)
    graph.add_node("replan", _replan)
    graph.add_node("report", _report)
    graph.add_node("approval_gate", _approval_gate)

    graph.set_entry_point("understand")
    graph.add_edge("understand", "plan")
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "verify")
    graph.add_conditional_edges(
        "verify", route_after_verify, {"replan": "replan", "execute": "execute", "report": "report"}
    )
    graph.add_edge("replan", "execute")
    graph.add_edge("report", "approval_gate")
    graph.add_edge("approval_gate", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())
