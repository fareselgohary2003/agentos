# AgentOS — Architecture Design (Phase 0)

## 1. Bounded Contexts

| Context | Responsibility |
|---|---|
| **IAM** | Organizations, Users, Roles, Permissions, API Keys, JWT/session |
| **Agent Registry** | Agent definitions, versions, prompts, tool bindings |
| **Orchestration** | LangGraph supervisor graph, planning, replanning, task DAG |
| **Tooling / MCP** | Tool registry, MCP server adapters, permission + risk enforcement |
| **Execution** | Workflow executions, task executions, sandboxed code runs |
| **Memory & RAG** | Short/episodic/semantic/org/user memory, document ingestion + retrieval |
| **Human-in-the-loop** | Approval requests, pause/resume |
| **Observability** | Traces, metrics, LLM usage/cost, audit log |
| **Evaluation** | Datasets, evaluators, regression gating in CI |

Each context = its own `app/<context>` package with `models/`, `schemas/`, `services/`, `api/` inside it (see repo structure §7). No context imports another context's internals directly — only through its `services` interface. This keeps it a modular monolith now, splittable into services later without a rewrite.

## 2. High-Level Runtime Flow

```
Client → FastAPI (stateless) → enqueue WorkflowExecution → 202 {execution_id, status:"queued"}
                                        │
                                        ▼
                              Celery worker picks it up
                                        │
                                        ▼
                         LangGraph Supervisor graph runs
                    (UNDERSTAND→PLAN→DELEGATE→EXECUTE→OBSERVE→
                     VERIFY→REPLAN?→APPROVE?→FINALIZE)
                                        │
                     state checkpointed to Postgres after every node
                                        │
                         events published to Redis pub/sub
                                        │
                                        ▼
                    FastAPI WebSocket/SSE endpoint relays events to client
```

Checkpointing after every LangGraph node (via a Postgres-backed checkpointer) is what makes pause/resume (approval gate) and crash-recovery work — the worker can die and a new one resumes from last checkpoint.

## 3. Database Schema (Phase 1 scope in bold, rest arrives in later phases)

All tables (except `organizations` itself) carry `organization_id UUID NOT NULL REFERENCES organizations(id)` and every query is filtered by it at the **repository layer**, not just at the API layer — enforced by a `TenantScopedRepository` base class that refuses to build a query without a tenant id.

```
organizations(id, name, slug, plan, is_active, created_at, updated_at)
users(id, organization_id, email, hashed_password, full_name, is_active, created_at, updated_at)
roles(id, organization_id, name, is_system)                -- OWNER/ADMIN/MANAGER/MEMBER/VIEWER seeded per org
permissions(id, code, description)                          -- global catalog, e.g. "agent:create"
role_permissions(role_id, permission_id)
user_roles(user_id, role_id)
api_keys(id, organization_id, user_id, name, hashed_key, scopes, last_used_at, revoked_at, created_at)
refresh_tokens(id, user_id, token_hash, expires_at, revoked_at)

agents(id, organization_id, name, description, system_prompt_ref, model, temperature,
       max_iterations, allowed_tools JSONB, status, created_at, updated_at)
agent_versions(id, agent_id, version, config JSONB, created_at, created_by)

tools(id, organization_id NULLABLE, name, description, input_schema JSONB,
      output_schema JSONB, risk_level, timeout_seconds, retry_policy JSONB, is_enabled)
tool_permissions(tool_id, role_id)

prompts(id, name, version, description, template, variables JSONB, created_at)

workflows(id, organization_id, name, definition JSONB, created_by, created_at, updated_at)
workflow_versions(id, workflow_id, version, definition JSONB, created_at)
workflow_executions(id, organization_id, workflow_id, user_id, goal, status,
                     plan JSONB, checkpoint JSONB, started_at, finished_at, error)
tasks(id, workflow_execution_id, external_id, agent, description, dependencies JSONB,
      required_tools JSONB, priority, status, retry_count)
task_executions(id, task_id, agent_run_id, tool_calls JSONB, output JSONB,
                status, started_at, finished_at, error)

memories(id, organization_id, user_id NULLABLE, scope, content, embedding VECTOR,
         metadata JSONB, created_at)
documents(id, organization_id, title, source, owner_id, storage_key, permissions JSONB, created_at)
document_chunks(id, document_id, organization_id, content, embedding VECTOR, metadata JSONB)

approvals(id, organization_id, workflow_execution_id, task_id, action, payload JSONB,
          risk_level, status, requested_by_agent, decided_by_user_id, decided_at, expires_at)

audit_logs(id, organization_id, user_id NULLABLE, action, resource, metadata JSONB,
           ip_address, created_at)                           -- INSERT-only, no UPDATE/DELETE grants

llm_usage(id, organization_id, user_id, agent_id, workflow_execution_id, provider, model,
          input_tokens, output_tokens, total_tokens, estimated_cost_usd, latency_ms, created_at)

evaluations(id, organization_id, agent_id, dataset_name, results JSONB, score, created_at)
```

Indexes: every FK column above, plus `(organization_id, created_at)` composite on the high-write tables (`audit_logs`, `llm_usage`, `task_executions`) for dashboard queries.

## 4. AgentState (LangGraph state schema)

```python
class AgentState(TypedDict):
    organization_id: str
    user_id: str
    conversation_id: str
    workflow_execution_id: str
    goal: str
    plan: Plan | None
    current_task_id: str | None
    completed_tasks: list[TaskResult]
    failed_tasks: list[TaskResult]
    tool_results: list[ToolResult]
    agent_outputs: dict[str, Any]
    verification_results: list[VerificationResult]
    pending_approval: ApprovalRequest | None
    approvals: list[ApprovalDecision]
    memories: list[MemoryItem]
    final_output: Report | None
    execution_metadata: ExecutionMetadata   # correlation ids, retry counts, cost so far
```

All non-primitive fields are Pydantic models, not raw dicts — the graph never passes untyped data between nodes. `execution_metadata` carries `request_id`, `workflow_id`, `execution_id`, `agent_run_id`, `tool_call_id` for tracing.

## 5. Tool Interface

```python
class ToolRiskLevel(str, Enum):
    LOW = "low"; MEDIUM = "medium"; HIGH = "high"; CRITICAL = "critical"

class Tool(Protocol):
    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    risk_level: ToolRiskLevel
    timeout_seconds: int
    retry_policy: RetryPolicy

    async def run(self, input: BaseModel, ctx: ToolContext) -> ToolResult: ...
```

`ToolContext` carries `organization_id`, `user_id`, `agent_id`, and a capability token — a tool cannot act outside the org/permissions it was invoked with. Every tool call goes through a `ToolExecutor` that: validates input against `input_schema` → checks `RoleHasToolPermission` → checks risk level (HIGH/CRITICAL → create `ApprovalRequest` and suspend) → runs with timeout+retry → validates output against `output_schema` → logs to `task_executions`/`audit_logs`.

## 6. MCP Architecture

Agents never import a tool implementation directly. They call `ToolRegistry.resolve(name)`, which returns either a local `Tool` or an `MCPToolAdapter` that speaks MCP over stdio/HTTP to one of the `mcp-servers/*` processes. The registry is populated at startup from a config (`tools` table + static manifest), so swapping GitHub's MCP server for a different implementation touches zero agent code.

```
Agent → ToolRegistry.resolve("github.search_issues")
      → MCPToolAdapter(server="github") → JSON-RPC call → mcp-servers/github
      → validated ToolResult back to agent
```

## 7. Security Model

- **AuthN**: JWT access (15 min) + refresh (7 days, rotated & hashed at rest) + API keys (hashed, scoped) for service-to-service.
- **AuthZ**: RBAC via `roles`/`permissions`/`role_permissions`; a `require_permission("agent:create")` FastAPI dependency checked on every mutating route.
- **Tenant isolation**: `TenantScopedRepository` requires `organization_id` to construct any query; there is no code path that queries tenant tables without it. Covered by dedicated cross-tenant-access tests (§36 of spec).
- **Prompt injection defense**: retrieved content (web pages, documents, tool output) is wrapped in a `<untrusted_data>` envelope in prompts and the system prompt explicitly instructs the model that content inside it is data, never instructions; a lightweight classifier flags suspicious patterns ("ignore previous instructions", etc.) and strips/flags before it reaches planning.
- **SQL agent**: LLM never executes raw SQL. It emits a structured `SqlQueryProposal`, which is parsed with `sqlglot`, rejected if it isn't a single `SELECT`, checked against an allow-list of tables the caller's role can read, then run on a read-only DB role.
- **Code sandbox**: Docker-in-Docker (or gVisor) container per run, `--network none`, CPU/mem/pids limits, read-only rootfs except `/tmp`, destroyed after execution.
- **Secrets**: never in code or DB in plaintext beyond hashed forms; provider keys only as env vars injected into the container at runtime.

## 8. Workflow Execution Model

- `WorkflowExecution` = one LangGraph run. State persisted via a Postgres checkpointer after every node.
- HIGH/CRITICAL tool calls or explicit "approval" nodes create an `ApprovalRequest`, flip execution status to `awaiting_approval`, and **the Celery task returns** — no thread is blocked waiting. A separate `POST /approvals/{id}/approve` endpoint re-enqueues a "resume" Celery task that reloads the checkpoint and continues the graph. This is what makes approval survive process restarts.
- Independent tasks in the plan (no shared dependency) are executed concurrently via `asyncio.gather` inside the EXECUTE node, not sequentially.
- Failure handling: task failure → Supervisor checks retry budget → alternate tool → alternate agent → else replan (loop back to PLAN with failure context) → else escalate to human approval to abort/redirect.

## 9. Repository Structure

See the monorepo layout from the spec (§4) — implemented as scaffolded below. Key addition: each backend bounded-context folder under `app/` is self-contained (`models.py`/`schemas.py`/`service.py`/`router.py`) rather than one global `models/` dumping ground, e.g.:

```
backend/app/
  iam/            (organizations, users, roles, permissions, api_keys, auth)
  agents/
  tools/
  mcp/
  orchestration/  (langgraph graph + nodes)
  execution/
  memory/
  approvals/
  observability/
  evaluation/
  core/           (config, db session, security primitives, base repository)
  main.py
```

## 10. Phase 1 Scope (this delivery)

- Repo scaffold (monorepo, docker-compose, .env.example).
- Postgres schema for `organizations, users, roles, permissions, role_permissions, user_roles, refresh_tokens, api_keys, audit_logs` via Alembic.
- FastAPI app: health/ready/metrics endpoints, structured logging, request-id middleware.
- Auth: register, login, refresh, logout, password hashing (argon2), JWT issuance, `get_current_user` + `require_permission` dependencies, RBAC seed (5 system roles).
- Organizations CRUD (OWNER-scoped) with tenant isolation enforced at repository layer.
- Audit log write-path wired into auth events.
- Next.js frontend skeleton: `/login`, `/dashboard` shell, API client, auth context, Tailwind theme (dark/light).
- Backend + frontend Dockerfiles, docker-compose with healthchecks, pytest suite covering register/login/RBAC/tenant-isolation.

Everything else (agents, LangGraph, MCP, memory, RAG, sandbox, evaluation, observability stack, CI) is Phase 2+ per the spec's own phasing, built on this foundation.
