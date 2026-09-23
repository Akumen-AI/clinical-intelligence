"""Merge heads before refresh_tokens

Revision ID: 2d864cfc900a
Revises: d783c381b960
Create Date: 2026-09-21 22:41:07.122253

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2d864cfc900a'
down_revision = 'd783c381b960'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
