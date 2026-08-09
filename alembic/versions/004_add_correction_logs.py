"""Add correction_logs table

Revision ID: 004_add_correction_logs
Revises: 003_add_pending_review_table
Create Date: 2026-08-09 18:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_add_correction_logs'
down_revision = '003_add_pending_review_table'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'correction_logs',
        sa.Column('id', sa.UUID(), nullable=False, primary_key=True),
        sa.Column('extracted_field_id', sa.UUID(), sa.ForeignKey('extracted_fields.field_id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', sa.UUID(), sa.ForeignKey('documents.document_id', ondelete='CASCADE'), nullable=False),
        sa.Column('action', sa.String(length=10), nullable=False),
        sa.Column('before_value', sa.Text(), nullable=True),
        sa.Column('after_value', sa.Text(), nullable=True),
        sa.Column('field_name', sa.String(length=255), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('reviewer_id', sa.UUID(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reviewer_role', sa.String(length=50), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retraining_exported', sa.Boolean(), nullable=False, server_default=sa.text('FALSE')),
        sa.Column('export_batch_id', sa.String(length=64), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("action IN ('accept', 'edit', 'reject')", name='ck_correction_action'),
    )
    op.create_index('idx_correction_logs_field', 'correction_logs', ['extracted_field_id'])
    op.create_index('idx_correction_logs_document', 'correction_logs', ['document_id'])
    op.create_index('idx_correction_logs_reviewer', 'correction_logs', ['reviewer_id'])
    op.create_index('idx_correction_logs_action', 'correction_logs', ['action'])
    op.create_index('idx_correction_logs_exported', 'correction_logs', ['retraining_exported'])
    op.create_index('idx_correction_logs_verified', 'correction_logs', ['verified_at'], postgresql_where=sa.text('verified_at IS NOT NULL'), sqlite_where=sa.text('verified_at IS NOT NULL'))


def downgrade():
    op.drop_index('idx_correction_logs_verified', table_name='correction_logs')
    op.drop_index('idx_correction_logs_exported', table_name='correction_logs')
    op.drop_index('idx_correction_logs_action', table_name='correction_logs')
    op.drop_index('idx_correction_logs_reviewer', table_name='correction_logs')
    op.drop_index('idx_correction_logs_document', table_name='correction_logs')
    op.drop_index('idx_correction_logs_field', table_name='correction_logs')
    op.drop_table('correction_logs')
