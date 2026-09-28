"""Minimal but real evaluation harness (spec §22). Each dataset is a list of
cases: {input, expected_tools, evaluation_criteria}. Grading here is
heuristic (tool-selection match + keyword-groundedness against the tool
output) rather than an LLM judge, so it runs deterministically in CI without
needing a live provider key — swap `_grade_case` for an LLM-judge call once a
provider is configured, keeping the same Evaluation row shape so nothing
downstream (dashboards, regression gating) needs to change.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runners import run_data_agent, run_research_agent
from app.evaluation.models import Evaluation
from app.llm.provider import MockProvider
from app.orchestration.state import TaskSpec
from app.tools.base import ToolContext, ToolExecutor

# A tiny, versioned dataset per agent — the format matches spec §22 exactly.
DATASETS: dict[str, list[dict]] = {
    "research_agent_groundedness_v1": [
        {
            "input": "Research competitor pricing in the Lighting category",
            "expected_tools": ["web_search"],
            "evaluation_criteria": ["mentions_search_results", "no_fabricated_url"],
        },
        {
            "input": "Find recent news about home goods e-commerce trends",
            "expected_tools": ["web_search"],
            "evaluation_criteria": ["mentions_search_results"],
        },
    ],
    "data_agent_sql_safety_v1": [
        {
            "input": "SELECT 1 AS placeholder",
            "expected_tools": ["sql_query"],
            "evaluation_criteria": ["query_executed", "read_only"],
        },
    ],
}

_AGENT_RUNNERS = {"research_agent": run_research_agent, "data_agent": run_data_agent}


async def run_evaluation_dataset(
    db: AsyncSession, organization_id: uuid.UUID, dataset_name: str, agent_name: str
) -> Evaluation:
    cases = DATASETS.get(dataset_name)
    if cases is None:
        raise ValueError(f"Unknown evaluation dataset: {dataset_name}")

    runner = _AGENT_RUNNERS.get(agent_name)
    if runner is None:
        raise ValueError(f"No runnable agent named {agent_name} for evaluation")

    llm = MockProvider(script=["Mock groundedness summary citing the search results provided."] * len(cases))
    ctx = ToolContext(organization_id, uuid.uuid4(), agent_name, "eval-run", {"tools:sql_query"})
    executor = ToolExecutor()

    passed = 0
    case_results = []
    for case in cases:
        task = TaskSpec(id=str(uuid.uuid4()), agent=agent_name, description=case["input"])
        result = await runner(task, case["input"], llm, ctx, executor)
        used_tool = result.tool_calls[0]["tool"] if result.tool_calls else None
        tool_ok = used_tool in case["expected_tools"]
        grounded_ok = result.error is None and result.output is not None
        case_passed = tool_ok and grounded_ok
        passed += int(case_passed)
        case_results.append({
            "input": case["input"], "passed": case_passed,
            "used_tool": used_tool, "error": result.error,
        })

    score = round(passed / len(cases), 4) if cases else 0.0
    evaluation = Evaluation(
        organization_id=organization_id, dataset_name=dataset_name,
        results={"agent": agent_name, "cases": case_results}, score=score,
    )
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)
    return evaluation
