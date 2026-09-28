"""document_chunks for RAG

Revision ID: 0003_document_chunks
Revises: 0002_platform_schema
Create Date: 2026-09-23
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0003_document_chunks"
down_revision = "0002_platform_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", pg.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("chunk_metadata", sa.JSON, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_organization_id", "document_chunks", ["organization_id"])


def downgrade() -> None:
    op.drop_table("document_chunks")
