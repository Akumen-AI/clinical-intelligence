"""Add pending_review and system_config tables

Revision ID: 003_add_pending_review_table
Revises: 002_add_confidence_check_and_index
Create Date: 2026-08-07 23:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_pending_review_table'
down_revision = '002_add_confidence_check_and_index'
branch_labels = None
depends_on = None


def upgrade():
    # Create pending_review table
    op.create_table(
        'pending_review',
        sa.Column('id', sa.String(length=36), nullable=False, primary_key=True),
        sa.Column('document_id', sa.String(length=36), sa.ForeignKey('documents.document_id', ondelete='CASCADE'), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('extracted_value', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='reviewstatus_enum'), nullable=False, server_default='PENDING'),
        sa.Column('reviewer_id', sa.String(length=36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_pending_review_id', 'pending_review', ['id'], unique=False)
    op.create_index('ix_pending_review_document_id', 'pending_review', ['document_id'], unique=False)
    op.create_index('ix_pending_review_field_name', 'pending_review', ['field_name'], unique=False)
    op.create_index('ix_pending_review_status', 'pending_review', ['status'], unique=False)

    # Create system_config table
    op.create_table(
        'system_config',
        sa.Column('key', sa.String(length=50), nullable=False, primary_key=True),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_system_config_key', 'system_config', ['key'], unique=False)


def downgrade():
    op.drop_index('ix_system_config_key', table_name='system_config')
    op.drop_table('system_config')
    op.drop_index('ix_pending_review_status', table_name='pending_review')
    op.drop_index('ix_pending_review_field_name', table_name='pending_review')
    op.drop_index('ix_pending_review_document_id', table_name='pending_review')
    op.drop_index('ix_pending_review_id', table_name='pending_review')
    op.drop_table('pending_review')
