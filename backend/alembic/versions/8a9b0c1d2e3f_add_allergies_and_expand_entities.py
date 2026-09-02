"""add_allergies_and_expand_entities

Revision ID: 8a9b0c1d2e3f
Revises: f77d5b30acdc
Create Date: 2026-09-02 14:43:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8a9b0c1d2e3f'
down_revision = 'f77d5b30acdc'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create allergies table
    op.create_table(
        'allergies',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('source_field_id', sa.String(length=36), nullable=True),
        sa.Column('raw_text', sa.String(length=500), nullable=False),
        sa.Column('allergen', sa.String(length=255), nullable=False),
        sa.Column('reaction', sa.String(length=500), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.patient_id'], ),
        sa.ForeignKeyConstraint(['source_field_id'], ['extracted_fields.field_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_allergies_id'), 'allergies', ['id'], unique=False)
    op.create_index(op.f('ix_allergies_patient_id'), 'allergies', ['patient_id'], unique=False)
    op.create_index(op.f('ix_allergies_source_field_id'), 'allergies', ['source_field_id'], unique=False)

    # Add columns to lab_results
    with op.batch_alter_table('lab_results', schema=None) as batch_op:
        batch_op.add_column(sa.Column('test_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('value_text', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('value_numeric', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('unit', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('reference_range', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('flag', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('recorded_at', sa.String(length=100), nullable=True))

    # Add columns to medications
    with op.batch_alter_table('medications', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=True, server_default='active'))
        batch_op.add_column(sa.Column('discontinued_reason', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('discontinued_date', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('started_date', sa.String(length=100), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('medications', schema=None) as batch_op:
        batch_op.drop_column('started_date')
        batch_op.drop_column('discontinued_date')
        batch_op.drop_column('discontinued_reason')
        batch_op.drop_column('status')

    with op.batch_alter_table('lab_results', schema=None) as batch_op:
        batch_op.drop_column('recorded_at')
        batch_op.drop_column('flag')
        batch_op.drop_column('reference_range')
        batch_op.drop_column('unit')
        batch_op.drop_column('value_numeric')
        batch_op.drop_column('value_text')
        batch_op.drop_column('test_name')

    op.drop_index(op.f('ix_allergies_source_field_id'), table_name='allergies')
    op.drop_index(op.f('ix_allergies_patient_id'), table_name='allergies')
    op.drop_index(op.f('ix_allergies_id'), table_name='allergies')
    op.drop_table('allergies')
