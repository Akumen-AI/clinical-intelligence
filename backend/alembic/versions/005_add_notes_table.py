"""Add notes table

Revision ID: 005_add_notes_table
Revises: f77d5b30acdc
Create Date: 2026-09-03 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_add_notes_table'
down_revision = 'f77d5b30acdc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'notes',
        sa.Column('id', sa.String(length=36), nullable=False, primary_key=True),
        sa.Column('patient_id', sa.String(length=36), sa.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False),
        sa.Column('author_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('author_role', sa.String(length=64), nullable=False),
        sa.Column('complaint_type', sa.String(length=128), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_notes_patient_id', 'notes', ['patient_id'])
    op.create_index('idx_notes_author_id', 'notes', ['author_id'])


def downgrade() -> None:
    op.drop_index('idx_notes_author_id', table_name='notes')
    op.drop_index('idx_notes_patient_id', table_name='notes')
    op.drop_table('notes')
