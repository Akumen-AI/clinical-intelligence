"""Add department_access to users

Revision ID: b3b5b6b7b8b9
Revises: c70d8c54004c
Create Date: 2026-09-21 23:04:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import json

# revision identifiers, used by Alembic.
revision: str = 'b3b5b6b7b8b9'
down_revision: Union[str, None] = 'c70d8c54004c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add column with default empty list JSON
    op.add_column('users', sa.Column('department_access', sa.JSON(), nullable=False, server_default='[]'))


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('department_access')
