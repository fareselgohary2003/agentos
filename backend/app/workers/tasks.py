"""Wires WorkflowExecution rows -> the LangGraph supervisor -> persisted
results, using a real Postgres-backed checkpointer so a pause at the
approval_gate genuinely survives a worker restart (proven end-to-end with a
two-process test — see docs/architecture/00-design.md §8).
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command
from sqlalchemy import select

from app.approvals.service import create_approval_request
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.execution.models import Task, TaskExecution, WorkflowExecution
from app.llm.provider import get_llm_provider
from app.orchestration.graph import build_supervisor_graph
from app.orchestration.state import ExecutionMetadata
from app.workers.celery_app import celery_app

settings = get_settings()

# AsyncPostgresSaver wants a plain libpq DSN, not SQLAlchemy's asyncpg URL scheme.
_CHECKPOINTER_DSN = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


def _initial_state(execution: WorkflowExecution) -> dict:
    return {
        "organization_id": str(execution.organization_id),
        "user_id": str(execution.user_id),
        "conversation_id": str(uuid.uuid4()),
        "workflow_execution_id": str(execution.id),
        "goal": execution.goal,
        "completed_tasks": [],
        "failed_tasks": [],
        "execution_metadata": ExecutionMetadata(
            request_id=str(uuid.uuid4()),
            workflow_id=str(execution.workflow_id) if execution.workflow_id else "ad-hoc",
            execution_id=str(execution.id),
        ),
    }


async def _persist_run_result(db, execution: WorkflowExecution, final_state: dict) -> None:
    plan = final_state.get("plan")
    execution.plan = plan.model_dump() if plan else {}

    completed = final_state.get("completed_tasks", [])
    failed = final_state.get("failed_tasks", [])
    by_id = {t.task_id: t for t in completed + failed}

    if plan:
        existing = await db.execute(
            select(Task.external_id).where(Task.workflow_execution_id == execution.id)
        )
        already_persisted = {row[0] for row in existing.all()}
        for task_spec in plan.tasks:
            if task_spec.id in already_persisted:
                continue  # avoid duplicate rows across a pause->resume of the same execution
            task_row = Task(
                workflow_execution_id=execution.id,
                external_id=task_spec.id,
                agent=task_spec.agent,
                description=task_spec.description,
                dependencies=task_spec.dependencies,
                required_tools=task_spec.required_tools,
                status="done" if task_spec.id in {t.task_id for t in completed} else (
                    "failed" if task_spec.id in {t.task_id for t in failed} else "skipped"),
            )
            db.add(task_row)
            await db.flush()
            if task_spec.id in by_id:
                task_result = by_id[task_spec.id]
                db.add(TaskExecution(
                    task_id=task_row.id,
                    agent_run_id=str(uuid.uuid4()),
                    tool_calls=task_result.tool_calls,
                    output=task_result.output or {},
                    status="completed" if task_result.error is None else "failed",
                    error=task_result.error,
                    finished_at=datetime.now(timezone.utc),
                ))

    interrupts = final_state.get("__interrupt__")
    if interrupts:
        # A genuine LangGraph interrupt — the graph is paused for real, not a
        # convention we're inferring after the fact.
        payload = interrupts[0].value
        await create_approval_request(
            db, execution.organization_id, str(execution.id),
            payload.get("task_id", "unknown"), payload.get("action", "unknown"),
            payload.get("payload", {}), payload.get("risk_level", "high"),
            payload.get("requested_by_agent", "supervisor"),
        )
        execution.status = "awaiting_approval"
    else:
        execution.status = final_state.get("status", "done")
        execution.finished_at = datetime.now(timezone.utc)

        final_output = final_state.get("final_output")
        if final_output:
            execution.plan = {**execution.plan, "final_output": final_output.model_dump()}


async def _run_execution_async(execution_id: str) -> None:
    async with AsyncSessionLocal() as db:
        execution = await db.get(WorkflowExecution, uuid.UUID(execution_id))
        if execution is None:
            return
        execution.status = "executing"
        execution.started_at = datetime.now(timezone.utc)
        await db.commit()

        llm = get_llm_provider()
        config = {"configurable": {"thread_id": str(execution.id)}}

        try:
            async with AsyncPostgresSaver.from_conn_string(_CHECKPOINTER_DSN) as checkpointer:
                await checkpointer.setup()
                graph = build_supervisor_graph(llm=llm, checkpointer=checkpointer)
                final_state = await graph.ainvoke(_initial_state(execution), config=config)
        except Exception as exc:
            execution.status = "failed"
            execution.error = str(exc)
            execution.finished_at = datetime.now(timezone.utc)
            await db.commit()
            return

        await _persist_run_result(db, execution, final_state)
        await db.commit()


@celery_app.task(name="agentos.execute_workflow")
def execute_workflow_task(execution_id: str) -> str:
    """Celery entrypoint. Kept as a thin sync wrapper around the async graph
    run, per Celery's own recommended pattern for async work in a worker.

    Disposes the SQLAlchemy engine's connection pool after each run: asyncpg
    connections are bound to the event loop that created them, and each
    `asyncio.run()` call gets a brand-new loop, so a pooled connection from a
    previous task in this same long-lived worker process would otherwise be
    reused on a dead loop (caught for real: RuntimeError "attached to a
    different loop" when a resume task ran after an execute task in the same
    worker process).
    """
    from app.core.database import engine

    asyncio.run(_run_execution_async(execution_id))
    asyncio.run(engine.dispose())
    return execution_id


@celery_app.task(name="agentos.resume_workflow_after_approval")
def resume_workflow_after_approval_task(execution_id: str, approved: bool) -> str:
    """Reloads the checkpoint for `execution_id` from Postgres — genuinely,
    even in a brand-new worker process — and resumes the graph exactly at the
    interrupted approval_gate node via LangGraph's Command(resume=...).
    """
    from app.core.database import engine

    asyncio.run(_resume_async(execution_id, approved))
    asyncio.run(engine.dispose())
    return execution_id
    return execution_id


async def _resume_async(execution_id: str, approved: bool) -> None:
    async with AsyncSessionLocal() as db:
        execution = await db.get(WorkflowExecution, uuid.UUID(execution_id))
        if execution is None:
            return

        llm = get_llm_provider()
        config = {"configurable": {"thread_id": str(execution.id)}}

        try:
            async with AsyncPostgresSaver.from_conn_string(_CHECKPOINTER_DSN) as checkpointer:
                graph = build_supervisor_graph(llm=llm, checkpointer=checkpointer)
                final_state = await graph.ainvoke(
                    Command(resume={"approved": approved}), config=config
                )
        except Exception as exc:
            execution.status = "failed"
            execution.error = str(exc)
            execution.finished_at = datetime.now(timezone.utc)
            await db.commit()
            return

        await _persist_run_result(db, execution, final_state)
        await db.commit()
