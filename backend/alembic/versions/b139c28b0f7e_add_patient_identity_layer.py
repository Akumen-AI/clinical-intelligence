"""Add patient identity layer

Revision ID: b139c28b0f7e
Revises: 004_add_correction_logs
Create Date: 2026-08-12 12:53:01.441742

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b139c28b0f7e'
down_revision = '004_add_correction_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('patients',
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('mrn', sa.String(length=50), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('dob', sa.String(length=50), nullable=True),
        sa.Column('sex', sa.String(length=50), nullable=True),
        sa.Column('duplicate_of', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['duplicate_of'], ['patients.patient_id'], ),
        sa.PrimaryKeyConstraint('patient_id')
    )
    op.create_index(op.f('ix_patients_mrn'), 'patients', ['mrn'], unique=False)
    op.create_index(op.f('ix_patients_patient_id'), 'patients', ['patient_id'], unique=False)

    op.create_table('visits',
        sa.Column('visit_id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('visit_date', sa.DateTime(), nullable=True),
        sa.Column('department', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.patient_id'], ),
        sa.PrimaryKeyConstraint('visit_id')
    )
    op.create_index(op.f('ix_visits_patient_id'), 'visits', ['patient_id'], unique=False)
    op.create_index(op.f('ix_visits_visit_id'), 'visits', ['visit_id'], unique=False)

    for table_name, extra_cols in [
        ('medications', [sa.Column('rxnorm_code', sa.String(length=100), nullable=True)]),
        ('diagnoses', [sa.Column('icd10_code', sa.String(length=100), nullable=True)]),
        ('lab_results', [sa.Column('loinc_code', sa.String(length=100), nullable=True)]),
        ('vitals', [
            sa.Column('type', sa.String(length=100), nullable=True),
            sa.Column('value', sa.String(length=255), nullable=True),
            sa.Column('recorded_at', sa.String(length=100), nullable=True)
        ]),
        ('procedures', [
            sa.Column('code', sa.String(length=100), nullable=True),
            sa.Column('description', sa.String(length=500), nullable=True),
            sa.Column('date', sa.String(length=100), nullable=True)
        ])
    ]:
        op.create_table(table_name,
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('patient_id', sa.String(length=36), nullable=False),
            sa.Column('source_field_id', sa.String(length=36), nullable=False),
            sa.Column('raw_text', sa.String(length=500), nullable=False),
            *extra_cols,
            sa.ForeignKeyConstraint(['patient_id'], ['patients.patient_id'], ),
            sa.ForeignKeyConstraint(['source_field_id'], ['extracted_fields.field_id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f(f'ix_{table_name}_id'), table_name, ['id'], unique=False)
        op.create_index(op.f(f'ix_{table_name}_patient_id'), table_name, ['patient_id'], unique=False)
        op.create_index(op.f(f'ix_{table_name}_source_field_id'), table_name, ['source_field_id'], unique=False)

    # Note: SQLite doesn't easily support adding a column and foreign key via ALTER TABLE. 
    # Since documents table exists, we use batch alter table to add patient_id column.
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('patient_id', sa.String(length=36), nullable=True))
        batch_op.create_index(batch_op.f('ix_documents_patient_id'), ['patient_id'], unique=False)
        # Note: SQLite doesn't support adding foreign key constraints to existing tables well. 
        # Skipping create_foreign_key for SQLite compatibility.


def downgrade() -> None:
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_documents_patient_id'))
        batch_op.drop_column('patient_id')

    for table in ['procedures', 'vitals', 'lab_results', 'diagnoses', 'medications', 'visits', 'patients']:
        op.drop_table(table)
