"""Add terminology mapping audit columns.

Revision ID: c4f1a2b3d4e5
Revises: 8a9b0c1d2e3f
"""
from alembic import op
import sqlalchemy as sa


revision = "c4f1a2b3d4e5"
down_revision = "8a9b0c1d2e3f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("medications") as batch_op:
        batch_op.add_column(sa.Column("mapping_source", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("mapping_version", sa.String(length=50), nullable=True))
    with op.batch_alter_table("diagnoses") as batch_op:
        batch_op.add_column(sa.Column("mapping_source", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("mapping_version", sa.String(length=50), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("diagnoses") as batch_op:
        batch_op.drop_column("mapping_version")
        batch_op.drop_column("mapping_source")
    with op.batch_alter_table("medications") as batch_op:
        batch_op.drop_column("mapping_version")
        batch_op.drop_column("mapping_source")
