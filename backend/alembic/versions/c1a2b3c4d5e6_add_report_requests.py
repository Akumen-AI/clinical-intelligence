"""Add persisted natural-language report requests.

Revision ID: c1a2b3c4d5e6
Revises: 21fadcc6022f
"""

from alembic import op
import sqlalchemy as sa


revision = "c1a2b3c4d5e6"
down_revision = "21fadcc6022f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=False),
        sa.Column("nl_query", sa.String(length=1000), nullable=False),
        sa.Column("resolved_filters", sa.JSON(), nullable=False),
        sa.Column("chart_type", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("report_requests") as batch_op:
        batch_op.create_index("ix_report_requests_actor_user_id", ["actor_user_id"])
        batch_op.create_index("ix_report_requests_created_at", ["created_at"])


def downgrade() -> None:
    op.drop_table("report_requests")
