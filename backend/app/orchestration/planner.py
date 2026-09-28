import json

from app.llm.provider import LLMMessage, LLMProvider
from app.orchestration.state import Plan, TaskSpec

PLANNER_SYSTEM_PROMPT = """You are the Planner for an autonomous multi-agent system.
Break the user's goal into a JSON plan of tasks. Each task must specify which
agent should handle it. Available agents: research_agent, data_agent,
verification_agent, report_agent. Independent tasks (no shared dependency)
will run concurrently, so only add a dependency when a task genuinely needs
another task's output.

Respond with ONLY JSON in this exact shape, no prose:
{
  "tasks": [
    {"id": "task_1", "agent": "research_agent", "description": "...", "dependencies": []}
  ]
}
"""


def _fallback_plan(goal: str) -> Plan:
    """Used if the LLM response isn't valid JSON — keeps the workflow moving
    with a conservative single-research-task plan rather than failing outright."""
    return Plan(
        goal=goal,
        tasks=[
            TaskSpec(id="task_1", agent="research_agent", description=goal, dependencies=[]),
            TaskSpec(id="task_2", agent="report_agent", description="Summarize findings",
                     dependencies=["task_1"]),
        ],
    )


async def generate_plan(goal: str, llm: LLMProvider, failure_context: str | None = None) -> Plan:
    user_content = f"Goal: {goal}"
    if failure_context:
        user_content += f"\n\nA previous attempt failed with: {failure_context}\nAdjust the plan accordingly."

    messages = [LLMMessage("system", PLANNER_SYSTEM_PROMPT), LLMMessage("user", user_content)]
    response = await llm.complete(messages)

    try:
        parsed = json.loads(response.content)
        tasks = [TaskSpec(**t) for t in parsed["tasks"]]
        return Plan(goal=goal, tasks=tasks)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return _fallback_plan(goal)
