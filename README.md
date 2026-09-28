# AgentOS — Enterprise Autonomous AI Workforce Platform

AgentOS is an enterprise-grade multi-agent AI platform designed to create, orchestrate, execute, monitor, and evaluate autonomous AI workflows for complex business objectives.

The platform allows organizations to define a business goal in natural language and have an AI Supervisor analyze the objective, create an execution plan, delegate tasks to specialized agents, execute the required tools, verify results, request human approval when necessary, and produce a final business-oriented response or report.

AgentOS is designed around the concept of an autonomous AI workforce rather than a single AI assistant. Multiple specialized agents collaborate through a controlled orchestration layer while the platform maintains security, tenant isolation, auditability, approvals, execution state, memory, and monitoring.

# Core Architecture

The central component of AgentOS is the Supervisor and Planner implemented using LangGraph.

A workflow follows a structured execution lifecycle:

UNDERSTAND → PLAN → EXECUTE → VERIFY → REPLAN → REPORT

The Supervisor receives the user's objective, understands the required outcome, generates a structured execution plan, determines which agents and tools are required, executes tasks concurrently when possible, verifies intermediate results, replans when the results are insufficient, and finally produces the completed output.

The execution state is represented through a persistent workflow state that allows long-running workflows to pause, resume, and survive process restarts.

# AI Agent Workforce

AgentOS provides an extensible agent architecture that allows specialized agents to perform different types of work.

The platform includes the foundation for agents responsible for research, data analysis, verification, reporting, tool execution, and other business-specific capabilities.

Agents operate as part of a coordinated workflow rather than as isolated chatbots. The Supervisor determines when an agent is required, what task it should perform, and how its output should contribute to the final objective.

# LangGraph Orchestration

The orchestration layer is built around LangGraph and implements the complete workflow lifecycle.

The system supports planning, concurrent task execution, verification, replanning, reporting, checkpointing, and human interruption.

Human approval is implemented using LangGraph's interrupt mechanism rather than a simple application-level status flag. Workflow state is checkpointed in PostgreSQL, allowing execution to resume after an approval decision.

The platform has been tested with real FastAPI, Redis, Celery, PostgreSQL, and worker processes running independently.

The approval lifecycle is implemented end-to-end:

POST /api/goals/execute → workflow execution → approval interruption → approval request → human decision → workflow resume → completed execution.

The workflow can also resume from a separate Python process without relying on shared in-memory state.

# Tool System and MCP

AgentOS contains a centralized Tool interface and Tool Registry for managing agent capabilities.

Tools can be classified according to execution risk. High-risk and critical tools can be blocked behind human approval before execution.

The platform includes MCP integration through an MCP Tool Adapter and provides MCP servers for filesystem, GitHub, PostgreSQL, web, and notification capabilities.

The PostgreSQL tool includes read-only enforcement for safe database analysis.

The GitHub and PostgreSQL MCP integrations have been tested against real services, while other integrations can return an explicit not-configured response when the required credentials are unavailable.

# Human-in-the-Loop Safety

AgentOS is designed so that autonomous execution does not mean uncontrolled execution.

Sensitive operations can require explicit human approval before they are executed.

When an approval is required, the workflow is interrupted and its state is persisted. The user can review the pending approval and approve or reject the operation. Once approved, the workflow resumes from the exact point where it was interrupted.

This mechanism provides a controlled boundary between autonomous reasoning and high-risk actions.

# Multi-Tenant Architecture

The backend includes multi-tenant organization management, authentication, authorization, and role-based access control.

Tenant isolation is enforced at the repository layer rather than relying exclusively on API-level checks.

The system includes organization management, user management, RBAC, authentication, JWT access tokens, refresh token rotation, and tenant isolation tests.

Passwords are hashed using Argon2 and refresh tokens are stored in hashed form.

# Audit Logging

AgentOS maintains audit records for platform activity and agent operations.

The audit system is designed to provide traceability across workflows, tools, users, organizations, and execution events.

This allows organizations to understand what happened during an autonomous workflow and provides an operational foundation for enterprise governance and security.

# Memory

AgentOS includes an agent memory subsystem implementing a retrieve, rank, filter, and inject workflow.

The current implementation uses keyword-based memory retrieval. The architecture is designed so that the retrieval implementation can later be extended with vector-based retrieval such as pgvector and embeddings.

# Distributed Execution

AgentOS uses Celery and Redis for asynchronous workflow execution.

Submitting a workflow does not require the API process to execute the complete workflow synchronously. The API can enqueue the execution while a separate Celery worker consumes the task and executes the workflow.

The complete asynchronous execution loop has been tested with a real Redis server, a real Celery worker, a real FastAPI process, and PostgreSQL running as separate services.

# Database

PostgreSQL is used as the primary relational database.

SQLAlchemy 2 with asynchronous database access is used for the application data layer, while Alembic manages database migrations.

The database contains the platform foundation for organizations, users, roles, agents, tools, workflows, workflow executions, approvals, audit records, memory, evaluations, analytics, and related platform data.

# Evaluation

AgentOS includes an evaluation framework for testing agent behavior and workflow results.

The project contains evaluation models, evaluators, regression checks, and tests designed to prevent changes from silently degrading existing behavior.

The architecture also includes a foundation for automated regression gating in CI.

# Monitoring and Observability

The platform includes execution monitoring and cost-related execution records.

The architecture provides a foundation for tracking workflow execution, task activity, model usage, and LLM costs.

The planned observability layer includes OpenTelemetry, Prometheus, Grafana, and LangSmith integration for production monitoring and deeper agent observability.

# Frontend

The AgentOS frontend is built with Next.js and TypeScript with Tailwind CSS.

The dashboard provides interfaces for managing and observing the platform, including agents, workflows, executions, approvals, audit logs, evaluations, monitoring, and tools.

The platform also contains data visualization components for presenting structured analytical results.

# Technology Stack

Backend:

Python
FastAPI
SQLAlchemy 2
Alembic
PostgreSQL
Redis
Celery
LangGraph
LangChain

Frontend:

Next.js
TypeScript
Tailwind CSS

Infrastructure:

Docker
Docker Compose
GitHub Actions

AI and Integration Layer:

Multi-provider LLM architecture
LangGraph orchestration
LangChain integrations
MCP
Tool Registry
Agent Memory

# Project Structure

```text
agentos/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   ├── analytics/
│   │   ├── approvals/
│   │   ├── core/
│   │   ├── evaluation/
│   │   ├── execution/
│   │   ├── iam/
│   │   ├── llm/
│   │   ├── memory/
│   │   ├── orchestration/
│   │   ├── rag/
│   │   ├── security/
│   │   ├── tools/
│   │   └── workers/
│   ├── migrations/
│   ├── scripts/
│   ├── tests/
│   └── pyproject.toml
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
│
├── mcp-servers/
│   ├── filesystem/
│   ├── github/
│   ├── notifications/
│   ├── postgres/
│   └── web/
│
├── docs/
│   └── architecture/
│
├── docker-compose.yml
├── LICENSE
├── README.md
└── .env.example
