"""Add correlation_id, outcome, and context to audit_log_entries

Revision ID: e732bd510d82
Revises: b3b5b6b7b8b9
Create Date: 2026-09-22 11:52:58.964542

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e732bd510d82'
down_revision = 'b3b5b6b7b8b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('audit_log_entries', sa.Column('correlation_id', sa.String(), nullable=True))
    op.add_column('audit_log_entries', sa.Column('outcome', sa.String(), nullable=True))
    op.add_column('audit_log_entries', sa.Column('context', sa.JSON(), nullable=True))
    op.create_index(op.f('ix_audit_log_entries_correlation_id'), 'audit_log_entries', ['correlation_id'], unique=False)
    op.create_index(op.f('ix_audit_log_entries_outcome'), 'audit_log_entries', ['outcome'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_audit_log_entries_outcome'), table_name='audit_log_entries')
    op.drop_index(op.f('ix_audit_log_entries_correlation_id'), table_name='audit_log_entries')
    op.drop_column('audit_log_entries', 'context')
    op.drop_column('audit_log_entries', 'outcome')
    op.drop_column('audit_log_entries', 'correlation_id')
