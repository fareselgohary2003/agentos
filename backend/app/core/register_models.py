"""Import this before touching the database from any entrypoint that isn't
`app.main` (which already gets full coverage transitively through its
routers). Missing this import is exactly the bug caught in production for
the Celery worker: SQLAlchemy raised `NoReferencedTableError` for
`workflow_executions.organization_id` because the worker process had never
imported `app.iam.models`, so `organizations` didn't exist in Base.metadata
yet when the FK was resolved.
"""
from app.agents import models as _agents_models  # noqa: F401
from app.analytics import models as _analytics_models  # noqa: F401
from app.approvals import models as _approvals_models  # noqa: F401
from app.evaluation import models as _evaluation_models  # noqa: F401
from app.execution import models as _execution_models  # noqa: F401
from app.iam import models as _iam_models  # noqa: F401
from app.memory import models as _memory_models  # noqa: F401
from app.rag import service as _rag_models  # noqa: F401 (registers DocumentChunk)
