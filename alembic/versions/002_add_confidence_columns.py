"""Add confidence and status columns to extraction_fields table

Revision ID: 002_add_confidence_columns
Revises: 001_create_layout_regions
Create Date: 2026-08-03
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_confidence_columns'
down_revision = '001_create_layout_regions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'extraction_fields',
        sa.Column('confidence', sa.Float(), nullable=True)
    )
    op.add_column(
        'extraction_fields',
        sa.Column('status', sa.String(length=50), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('extraction_fields', 'status')
    op.drop_column('extraction_fields', 'confidence')
