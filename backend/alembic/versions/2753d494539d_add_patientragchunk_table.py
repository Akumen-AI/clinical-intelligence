"""Add PatientRAGChunk table

Revision ID: 2753d494539d
Revises: b139c28b0f7e
Create Date: 2026-08-12 17:47:01.431654

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2753d494539d'
down_revision = 'b139c28b0f7e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('patient_rag_chunks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('patient_id', sa.String(), nullable=False),
        sa.Column('source_document_id', sa.String(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', sa.JSON(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['source_document_id'], ['documents.document_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_patient_rag_chunks_id'), 'patient_rag_chunks', ['id'], unique=False)
    op.create_index(op.f('ix_patient_rag_chunks_patient_id'), 'patient_rag_chunks', ['patient_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_patient_rag_chunks_patient_id'), table_name='patient_rag_chunks')
    op.drop_index(op.f('ix_patient_rag_chunks_id'), table_name='patient_rag_chunks')
    op.drop_table('patient_rag_chunks')
