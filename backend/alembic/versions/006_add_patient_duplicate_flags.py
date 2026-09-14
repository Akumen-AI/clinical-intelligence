"""add_patient_duplicate_flags

Revision ID: 006_add_patient_duplicate_flags
Revises: 005_add_notes_table
Create Date: 2026-09-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_patient_duplicate_flags'
down_revision = '005_add_notes_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add status column to patients if not present
    with op.batch_alter_table('patients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=20), server_default='active', nullable=True))

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        match_reasons_col = sa.Column('match_reasons', postgresql.ARRAY(sa.Text()), nullable=False)
        id_col = sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'))
        patient_a_id_col = sa.Column('patient_a_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False)
        patient_b_id_col = sa.Column('patient_b_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False)
        resolved_by_col = sa.Column('resolved_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True)
        merged_into_id_col = sa.Column('merged_into_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.patient_id'), nullable=True)
    else:
        match_reasons_col = sa.Column('match_reasons', sa.JSON(), nullable=False)
        id_col = sa.Column('id', sa.String(length=36), primary_key=True)
        patient_a_id_col = sa.Column('patient_a_id', sa.String(length=36), sa.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False)
        patient_b_id_col = sa.Column('patient_b_id', sa.String(length=36), sa.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False)
        resolved_by_col = sa.Column('resolved_by', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True)
        merged_into_id_col = sa.Column('merged_into_id', sa.String(length=36), sa.ForeignKey('patients.patient_id'), nullable=True)

    op.create_table(
        'patient_duplicate_flags',
        id_col,
        patient_a_id_col,
        patient_b_id_col,
        sa.Column('similarity_score', sa.Float(), nullable=False),
        match_reasons_col,
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('flagged_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        resolved_by_col,
        merged_into_id_col,
    )
    op.create_index('ix_patient_duplicate_flags_status', 'patient_duplicate_flags', ['status'], unique=False)

    if bind.dialect.name == 'postgresql':
        op.execute(
            "CREATE UNIQUE INDEX uq_patient_duplicate_pair ON patient_duplicate_flags "
            "(LEAST(patient_a_id::text, patient_b_id::text), GREATEST(patient_a_id::text, patient_b_id::text));"
        )
    else:
        op.create_index('uq_patient_duplicate_pair', 'patient_duplicate_flags', ['patient_a_id', 'patient_b_id'], unique=False)


def downgrade() -> None:
    op.drop_index('uq_patient_duplicate_pair', table_name='patient_duplicate_flags')
    op.drop_index('ix_patient_duplicate_flags_status', table_name='patient_duplicate_flags')
    op.drop_table('patient_duplicate_flags')
    with op.batch_alter_table('patients', schema=None) as batch_op:
        batch_op.drop_column('status')
