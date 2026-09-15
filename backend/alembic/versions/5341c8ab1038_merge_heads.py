"""Merge heads

Revision ID: 5341c8ab1038
Revises: 007_add_dept_completeness, c1a2b3c4d5e6
Create Date: 2026-09-15 13:10:40.004112

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5341c8ab1038'
down_revision = ('007_add_dept_completeness', 'c1a2b3c4d5e6')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
