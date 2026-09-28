"""agent platform + analytics schema

Revision ID: 0002_platform_schema
Revises: 0001_initial_iam
Create Date: 2026-09-23
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0002_platform_schema"
down_revision = "0001_initial_iam"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Prompts (global, versioned) ---
    op.create_table(
        "prompts",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("description", sa.String(255), server_default=""),
        sa.Column("template", sa.Text, nullable=False),
        sa.Column("variables", sa.JSON, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Agents ---
    op.create_table(
        "agents",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), server_default=""),
        sa.Column("system_prompt_ref", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("temperature", sa.Float, server_default="0.2"),
        sa.Column("max_iterations", sa.Integer, server_default="10"),
        sa.Column("allowed_tools", sa.JSON, server_default="[]"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agents_organization_id", "agents", ["organization_id"])

    # --- Tools catalog ---
    op.create_table(
        "tools",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), server_default=""),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("timeout_seconds", sa.Integer, server_default="30"),
        sa.Column("is_enabled", sa.Boolean, server_default=sa.true()),
    )
    op.create_index("ix_tools_organization_id", "tools", ["organization_id"])

    # --- Workflows & Executions ---
    op.create_table(
        "workflows",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("definition", sa.JSON, server_default="{}"),
        sa.Column("created_by", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_workflows_organization_id", "workflows", ["organization_id"])

    op.create_table(
        "workflow_executions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("workflow_id", pg.UUID(as_uuid=True), sa.ForeignKey("workflows.id"), nullable=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("goal", sa.Text, nullable=False),
        sa.Column("status", sa.String(30), server_default="queued"),
        sa.Column("plan", sa.JSON, server_default="{}"),
        sa.Column("checkpoint", sa.JSON, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_workflow_executions_organization_id", "workflow_executions", ["organization_id"])
    op.create_index("ix_workflow_executions_status", "workflow_executions", ["status"])
    op.create_index("ix_workflow_executions_created_at", "workflow_executions", ["created_at"])

    op.create_table(
        "tasks",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("workflow_execution_id", pg.UUID(as_uuid=True), sa.ForeignKey("workflow_executions.id"), nullable=False),
        sa.Column("external_id", sa.String(50), nullable=False),
        sa.Column("agent", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("dependencies", sa.JSON, server_default="[]"),
        sa.Column("required_tools", sa.JSON, server_default="[]"),
        sa.Column("priority", sa.Integer, server_default="1"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("retry_count", sa.Integer, server_default="0"),
    )
    op.create_index("ix_tasks_workflow_execution_id", "tasks", ["workflow_execution_id"])

    op.create_table(
        "task_executions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", pg.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("agent_run_id", sa.String(64), nullable=False),
        sa.Column("tool_calls", sa.JSON, server_default="[]"),
        sa.Column("output", sa.JSON, server_default="{}"),
        sa.Column("status", sa.String(20), server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
    )
    op.create_index("ix_task_executions_task_id", "task_executions", ["task_id"])

    # --- Memory ---
    op.create_table(
        "memories",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("scope", sa.String(30), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("memory_metadata", sa.JSON, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_memories_organization_id", "memories", ["organization_id"])
    op.create_index("ix_memories_scope", "memories", ["scope"])
    op.create_index("ix_memories_created_at", "memories", ["created_at"])

    # --- Approvals ---
    op.create_table(
        "approvals",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("workflow_execution_id", sa.String(64), nullable=False),
        sa.Column("task_id", sa.String(64), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON, server_default="{}"),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("requested_by_agent", sa.String(100), nullable=False),
        sa.Column("decided_by_user_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_approvals_organization_id", "approvals", ["organization_id"])
    op.create_index("ix_approvals_workflow_execution_id", "approvals", ["workflow_execution_id"])
    op.create_index("ix_approvals_status", "approvals", ["status"])

    # --- Documents (RAG) ---
    op.create_table(
        "documents",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("source", sa.String(300), server_default="upload"),
        sa.Column("owner_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(300), nullable=False),
        sa.Column("content_preview", sa.Text, server_default=""),
        sa.Column("permissions", sa.JSON, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_documents_organization_id", "documents", ["organization_id"])

    # --- LLM usage / cost tracking ---
    op.create_table(
        "llm_usage",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_execution_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("input_tokens", sa.Integer, server_default="0"),
        sa.Column("output_tokens", sa.Integer, server_default="0"),
        sa.Column("total_tokens", sa.Integer, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float, server_default="0"),
        sa.Column("latency_ms", sa.Float, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_llm_usage_organization_id", "llm_usage", ["organization_id"])
    op.create_index("ix_llm_usage_created_at", "llm_usage", ["created_at"])

    # --- Evaluations ---
    op.create_table(
        "evaluations",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("agent_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("dataset_name", sa.String(200), nullable=False),
        sa.Column("results", sa.JSON, server_default="{}"),
        sa.Column("score", sa.Float, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_evaluations_organization_id", "evaluations", ["organization_id"])

    # --- Analytics / sales data (the org's own business data) ---
    op.create_table(
        "regions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
    )
    op.create_index("ix_regions_organization_id", "regions", ["organization_id"])

    op.create_table(
        "product_categories",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
    )
    op.create_index("ix_product_categories_organization_id", "product_categories", ["organization_id"])

    op.create_table(
        "products",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("category_id", pg.UUID(as_uuid=True), sa.ForeignKey("product_categories.id"), nullable=False),
        sa.Column("sku", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("unit_price", sa.Float, nullable=False),
        sa.Column("unit_cost", sa.Float, nullable=False),
    )
    op.create_index("ix_products_organization_id", "products", ["organization_id"])

    op.create_table(
        "customers",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("region_id", pg.UUID(as_uuid=True), sa.ForeignKey("regions.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("segment", sa.String(30), nullable=False),
    )
    op.create_index("ix_customers_organization_id", "customers", ["organization_id"])

    op.create_table(
        "sales_orders",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("order_date", sa.Date, nullable=False),
        sa.Column("customer_id", pg.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("region_id", pg.UUID(as_uuid=True), sa.ForeignKey("regions.id"), nullable=False),
        sa.Column("product_id", pg.UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("unit_price", sa.Float, nullable=False),
        sa.Column("total_amount", sa.Float, nullable=False),
        sa.Column("quarter", sa.String(10), nullable=False),
    )
    op.create_index("ix_sales_orders_organization_id", "sales_orders", ["organization_id"])
    op.create_index("ix_sales_orders_order_date", "sales_orders", ["order_date"])
    op.create_index("ix_sales_orders_quarter", "sales_orders", ["quarter"])


def downgrade() -> None:
    for table in [
        "sales_orders", "customers", "products", "product_categories", "regions",
        "evaluations", "llm_usage", "documents", "approvals",
        "task_executions", "tasks", "workflow_executions", "workflows",
        "tools", "agents", "prompts", "memories",
    ]:
        op.drop_table(table)
