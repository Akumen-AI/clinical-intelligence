"""add snomed_code to diagnoses

Revision ID: d783c381b960
Revises: e0b55652796e
Create Date: 2026-09-15 14:25:39.175544

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd783c381b960'
down_revision = 'e0b55652796e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("diagnoses", sa.Column("snomed_code", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("diagnoses", "snomed_code")
