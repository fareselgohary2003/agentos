# AgentOS — Enterprise Autonomous AI Workforce Platform

AgentOS lets an organization create, orchestrate, monitor, and evaluate AI agents that plan and
execute multi-step goals — research, data analysis, code execution, reporting — with human
approval gates, full auditability, and multi-tenant isolation.

**Status: Phase 1 of 12** (see `docs/architecture/00-design.md` for the full phased roadmap and
architecture decisions). This delivery covers the foundation: auth, multi-tenant IAM/RBAC,
audit logging, health checks, and the repo/Docker/CI skeleton the rest of the platform builds on.

## Architecture

See [`docs/architecture/00-design.md`](docs/architecture/00-design.md) for bounded contexts,
database schema, the `AgentState` LangGraph schema, the `Tool`/MCP interfaces, and the security
model. Diagrams for later phases live under `docs/architecture/`.

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL, Redis, Celery, LangGraph/LangChain
- **Frontend**: Next.js, TypeScript, Tailwind CSS
- **Infra**: Docker, Docker Compose, GitHub Actions (added Phase 12)

## Local Development

```bash
cp .env.example .env          # fill in JWT_SECRET at minimum; LLM keys optional for Phase 1
docker compose up --build
```

- API: http://localhost:8000 (docs at `/docs`)
- Frontend: http://localhost:3000
- Health: `GET /health`, `GET /ready`, `GET /metrics`

## Database Migrations

```bash
cd backend
alembic upgrade head                      # apply
alembic revision --autogenerate -m "msg"  # create a new migration
```

## Running Tests

```bash
cd backend
pip install -e ".[dev]"
createdb agentos_test   # or run against a disposable Postgres container
pytest -v
```

Covers: registration, login/JWT issuance, RBAC seeding, refresh tokens, and — critically —
cross-tenant data isolation (`tests/test_tenant_isolation.py`).

## Environment Variables

See [`.env.example`](.env.example). No provider is hardcoded: set `LLM_PROVIDER` /
`LLM_MODEL` and the matching `*_API_KEY`. Never commit a filled-in `.env`.

## What's in Phase 1 vs. Later Phases

| Phase | Scope |
|---|---|
| **1 (this delivery)** | Repo/Docker/DB skeleton, JWT auth, multi-tenant RBAC, audit log write-path, Next.js shell |
| 2 | Agent abstraction, Supervisor + Planner (LangGraph) |
| 3 | Research / Data Analyst / Verification / Report agents |
| 4 | Tool registry + MCP servers |
| 5 | Memory system |
| 6 | Human-in-the-loop approvals |
| 7 | Sandboxed code execution |
| 8 | Observability (OpenTelemetry, Prometheus, Grafana, LangSmith) |
| 9 | Evaluation framework + CI regression gating |
| 10 | Multi-tenancy hardening, security tests |
| 11 | Async distributed workers (real Celery task graph) |
| 12 | Production deployment, full CI/CD |

## Demo Company Seed Data

A complete, self-consistent fictional small company — **Brightleaf Home Goods**
(38-employee home décor e-commerce retailer) — can be seeded end-to-end:

```bash
cd backend
export DATABASE_URL=postgresql+asyncpg://agentos:agentos@localhost:5432/agentos
python -m scripts.seed_demo_company
```

This populates: the organization + 7 users across all 5 roles (password
`BrightleafDemo123` for all), 4 regions, 5 product categories, 23 products,
15 customers, ~390 sales orders across Q1-Q3 2026 with a real, queryable
story baked in (a 61% Q3 revenue crash in Lighting × North America - East,
coinciding with a competitor's price cuts — verified by direct SQL query
against the seeded data), all 8 agents + 4 tools + 5 prompts in their
catalogs, a complete workflow execution trace (4 tasks, outputs, tool calls,
LLM cost records) sitting in `awaiting_approval` status with one real pending
`ApprovalRequest`, plus sample documents, memories, audit logs, and an
evaluation record.

Log in as `sarah@brightleafhome.com` (OWNER) or `marcus@brightleafhome.com`
(ADMIN, can decide approvals) via `POST /api/auth/login`.

## Orchestration (Phase 2-3 delivered)

`app/orchestration/graph.py` implements the full LangGraph supervisor:
UNDERSTAND → PLAN → EXECUTE (concurrent, per spec §10) → VERIFY → REPLAN?
→ REPORT. Verified end-to-end with a scripted `MockProvider` (no API key
needed) including the replan branch actually triggering and recovering.
Point `LLM_PROVIDER`/`LLM_MODEL` at a real provider to run it for real.

`app/tools/` implements the Tool interface + risk-gated `ToolExecutor` (HIGH/
CRITICAL tools return `requires_approval` instead of executing) with 4 real
tools, including a read-only-enforced SQL tool verified against the seeded
sales data and a working `MCPToolAdapter` proven end-to-end against
`mcp-servers/filesystem/server.py` over real subprocess JSON-RPC.

`app/approvals/` implements the human-in-the-loop request/decide flow, and
`app/memory/` implements retrieve→rank→filter→inject (keyword-based; swap in
pgvector once embeddings are added — see `docs/architecture/00-design.md`).

### What's intentionally still a stub

- `web_search` returns a fixed placeholder — wire a real search API/MCP server.
- `python_sandbox` falls back to a `ulimit`-capped subprocess since this
  environment has no Docker daemon; swap in the Docker-per-run implementation
  described in `docs/architecture/00-design.md §7` wherever one is available.
- Observability stack (OpenTelemetry/Prometheus/Grafana dashboards) and CI/CD
  pipelines need real infrastructure this sandboxed build environment doesn't
  have; the schema/design for them is in the architecture doc. `.github/workflows/ci.yml`
  is written and its steps (tests, regression gate) are individually verified
  to work, but the workflow itself has not been run on GitHub's runners.
- Live execution status uses polling (3s interval) instead of a WebSocket/SSE
  push feed — functionally equivalent, less efficient at scale.
- `mcp-servers/web` and `mcp-servers/notifications` (email) need real API keys
  (`SEARCH_API_KEY`, an SMTP/SES credential) this environment doesn't have —
  they return a clearly labeled "not configured" response rather than faking
  success. `mcp-servers/github` and `mcp-servers/postgres` are fully real —
  tested live against the GitHub API and this project's own Postgres.
- Docker images are written correctly but never `docker build`-ed here (no
  Docker daemon in this sandboxed environment) — a first real build may
  surface small fixes.

### What's now genuinely proven, not just written (closed in this pass)

- **The full async execution loop is real end-to-end**: a real Redis server +
  a real `celery worker` process (not called directly — actually consuming
  from the Redis queue) + a real FastAPI process, tested together: submitting
  a goal via `POST /api/goals/execute` returns immediately, the separate
  worker process picks it up, runs the LangGraph supervisor, and persists the
  result — verified via the API showing the updated status afterward.
- **Human-in-the-loop is a real LangGraph `interrupt()`**, not a status flag we
  set by convention. `approval_gate_node` calls `interrupt()`; the graph
  genuinely suspends there with `AsyncPostgresSaver` checkpointing the state to
  Postgres.
- **Restart survival is proven, not assumed**: the graph was paused in one
  Python process, then resumed via `Command(resume=...)` in a *second,
  completely separate* Python process with no shared memory — it picked up
  exactly where it left off and completed. This is the actual guarantee the
  spec's "workflow must survive process restarts" (§18) asks for.
- **The full approval loop closes for real**: `POST /api/goals/execute` →
  real worker pauses at the interrupt → `GET /api/approvals` shows it →
  `POST /api/approvals/{id}/approve` → real worker resumes via
  `Command(resume=...)` → execution reaches `done`. Tested with the worker,
  API, Redis, and Postgres all running as separate real processes.
- Caught and fixed two real bugs in the process: the Celery worker process
  never imported `app.iam.models` (so SQLAlchemy raised `NoReferencedTableError`
  resolving `organizations` as an FK target — fixed via
  `app/core/register_models.py`, imported by every entrypoint), and asyncpg
  connections being reused across a stale event loop when Celery reruns
  `asyncio.run()` in the same long-lived worker process (fixed by disposing
  the engine's pool after each task).



- Tenant isolation is enforced at the repository layer (`app/core/base_repository.py`), not just
  the API layer — see `docs/architecture/00-design.md §7`.
- Passwords are hashed with Argon2; refresh tokens are stored hashed and rotated.
- No secrets are hardcoded; everything comes from environment variables (`.env`, never committed).

## License

See [`LICENSE`](LICENSE).
