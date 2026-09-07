"""merge branches

Revision ID: 21fadcc6022f
Revises: 005_add_notes_table, 8120641513fd
Create Date: 2026-09-07 21:02:48.002297

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '21fadcc6022f'
down_revision = ('005_add_notes_table', '8120641513fd')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
