"""add_performance_indexes

Revision ID: a5d55edd55f5
Revises: c310214221a4
Create Date: 2026-09-23 10:14:51.269195

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a5d55edd55f5'
down_revision = 'c310214221a4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Patient indexes
    op.execute('CREATE INDEX IF NOT EXISTS ix_patients_mrn ON patients (mrn)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_patients_name ON patients (name)')

    # Document indexes
    op.execute('CREATE INDEX IF NOT EXISTS ix_documents_patient_id ON documents (patient_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_documents_status ON documents (status)')

    # CanonicalPatientRecord indexes
    op.execute('CREATE INDEX IF NOT EXISTS ix_canonical_patient_records_document_id ON canonical_patient_records (document_id)')

    # UploadLog indexes
    op.execute('CREATE INDEX IF NOT EXISTS ix_upload_logs_timestamp ON upload_logs (timestamp)')

def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_upload_logs_timestamp')
    op.execute('DROP INDEX IF EXISTS ix_canonical_patient_records_document_id')
    op.execute('DROP INDEX IF EXISTS ix_documents_status')
    op.execute('DROP INDEX IF EXISTS ix_documents_patient_id')
    op.execute('DROP INDEX IF EXISTS ix_patients_name')
    op.execute('DROP INDEX IF EXISTS ix_patients_mrn')
