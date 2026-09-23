"""Baseline tables

Revision ID: 001_baseline
Revises:
Create Date: 2026-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = '001_baseline'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()

    if 'users' not in tables:
        op.create_table(
            'users',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('email', sa.String(length=255), unique=True, nullable=False),
            sa.Column('role', sa.String(length=50), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )

    if 'documents' not in tables:
        op.create_table(
            'documents',
            sa.Column('document_id', sa.String(length=36), primary_key=True),
            sa.Column('filename', sa.String(length=255), nullable=False),
            sa.Column('raw_uri', sa.String(length=500), nullable=False),
            sa.Column('filetype', sa.String(length=50), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False),
            sa.Column('uploaded_at', sa.DateTime(), nullable=False),
            sa.Column('processed_uri', sa.String(length=500), nullable=True),
        )

    if 'extracted_fields' not in tables:
        op.create_table(
            'extracted_fields',
            sa.Column('field_id', sa.String(length=36), primary_key=True),
            sa.Column('document_id', sa.String(length=36), sa.ForeignKey('documents.document_id', ondelete="CASCADE"), nullable=False),
            sa.Column('field_name', sa.String(length=100), nullable=False),
            sa.Column('raw_value', sa.JSON(), nullable=True),
            sa.Column('confidence_score', sa.Float(), nullable=False),
            sa.Column('bounding_box', sa.JSON(), nullable=True),
            sa.Column('verification_status', sa.String(length=50), nullable=False),
            sa.Column('verified_value', sa.JSON(), nullable=True),
            sa.Column('reviewer_id', sa.String(length=36), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )

def downgrade():
    pass
