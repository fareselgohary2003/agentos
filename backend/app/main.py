import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings
from app.core.database import check_db_ready
from app.core.logging import configure_logging, get_logger
from app.core.security_middleware import RateLimitMiddleware
from app.agents.router import router as agents_router
from app.approvals.router import router as approvals_router
from app.evaluation.router import router as evaluations_router
from app.execution.monitoring_router import router as monitoring_router
from app.execution.router import router as execution_router
from app.iam.audit_router import router as audit_router
from app.iam.organizations_router import router as organizations_router
from app.iam.router import router as auth_router
from app.memory.router import router as memory_router
from app.rag.router import router as documents_router
from app.tools.router import router as tools_router

settings = get_settings()
configure_logging(settings.DEBUG)
logger = get_logger(__name__)

app = FastAPI(title=settings.APP_NAME, version="0.1.0")

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_and_timing(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    return response


app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(approvals_router)
app.include_router(agents_router)
app.include_router(execution_router)
app.include_router(tools_router)
app.include_router(memory_router)
app.include_router(evaluations_router)
app.include_router(documents_router)
app.include_router(audit_router)
app.include_router(monitoring_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.APP_NAME}


@app.get("/ready")
async def ready():
    db_ok = await check_db_ready()
    status_code = "ready" if db_ok else "not_ready"
    return {"status": status_code, "checks": {"postgres": db_ok}}


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    # Placeholder text-exposition endpoint; replaced by prometheus-fastapi-instrumentator
    # once the observability stack lands in Phase 8.
    return "# AgentOS metrics endpoint placeholder\n"
