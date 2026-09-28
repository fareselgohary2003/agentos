"""Celery application stub for Phase 1.

Real workflow-execution tasks (LangGraph supervisor runs, replanning,
approval resume) are added in Phase 11 once orchestration (Phase 2-3)
exists. This exists now so `docker-compose up` brings up a working
worker container from day one.
"""
from celery import Celery

from app.core import register_models  # noqa: F401 (ensures all SQLAlchemy models load before any task runs)
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "agentos", broker=settings.REDIS_URL, backend=settings.REDIS_URL,
    include=["app.workers.tasks"],  # registers execute_workflow / resume_workflow_after_approval
)
celery_app.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"])


@celery_app.task(name="agentos.ping")
def ping() -> str:
    return "pong"
