"""Add missing document columns and extracted_fields index

Revision ID: e0b55652796e
Revises: 5341c8ab1038
Create Date: 2026-09-15 13:10:56.256090

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e0b55652796e'
down_revision = '5341c8ab1038'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Safely add columns to 'documents' table
    doc_cols = [c['name'] for c in inspector.get_columns('documents')]
    with op.batch_alter_table('documents', schema=None) as batch_op:
        if 'processing_time_ms' not in doc_cols:
            batch_op.add_column(sa.Column('processing_time_ms', sa.Integer(), nullable=True))
        if 'document_type' not in doc_cols:
            batch_op.add_column(sa.Column('document_type', sa.String(length=100), nullable=True))
        if 'classification_confidence' not in doc_cols:
            batch_op.add_column(sa.Column('classification_confidence', sa.Float(), nullable=True))
        if 'extraction_confidence' not in doc_cols:
            batch_op.add_column(sa.Column('extraction_confidence', sa.Float(), nullable=True))
        if 'needs_manual_review' not in doc_cols:
            batch_op.add_column(sa.Column('needs_manual_review', sa.Boolean(), server_default='0', nullable=False))

    # Safely create index on 'extracted_fields' table
    indexes = [idx['name'] for idx in inspector.get_indexes('extracted_fields')]
    if 'ix_extracted_fields_doc_confidence' not in indexes:
        with op.batch_alter_table('extracted_fields', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_extracted_fields_doc_confidence'), ['document_id', 'confidence_score'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('extracted_fields', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_extracted_fields_doc_confidence'))
        
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_column('needs_manual_review')
        batch_op.drop_column('extraction_confidence')
        batch_op.drop_column('classification_confidence')
        batch_op.drop_column('document_type')
        batch_op.drop_column('processing_time_ms')
