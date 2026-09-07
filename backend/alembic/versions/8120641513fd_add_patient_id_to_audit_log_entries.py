"""add patient_id to audit_log_entries

Revision ID: 8120641513fd
Revises: 8a9b0c1d2e3f
Create Date: 2026-09-04 12:16:31.807453

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8120641513fd'
down_revision = '8a9b0c1d2e3f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('audit_log_entries', schema=None) as batch_op:
        batch_op.add_column(sa.Column('patient_id', sa.String(), nullable=True))
        batch_op.create_index(batch_op.f('ix_audit_log_entries_patient_id'), ['patient_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('audit_log_entries', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_log_entries_patient_id'))
        batch_op.drop_column('patient_id')
