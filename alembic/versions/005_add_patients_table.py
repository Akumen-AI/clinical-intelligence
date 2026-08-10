"""Migration 005 — Add patients table and FK from documents.patient_id → patients.id

Revision ID: 005_add_patients_table
Revises: 004_add_correction_logs
Create Date: 2026-08-10

Steps performed in upgrade():
  1. Creates the `patients` table.
  2. Reports the count of orphaned patient_id values already in `documents`
     (i.e. rows where patient_id IS NOT NULL).  Because the patients table is
     brand-new, every existing non-null patient_id is an orphan by definition.
     The count is printed to stdout / logged so the operator can decide whether
     to create stub Patient rows before enforcing the constraint.
     *** These rows are NOT silently nulled out. ***
  3. Adds a FK declaration from documents.patient_id → patients.id using
     batch_alter_table (required for SQLite, which does not support
     ADD CONSTRAINT via ALTER TABLE).  The column remains nullable.

Note on SQLite FK enforcement:
  SQLite accepts the FK syntax but does not enforce it unless PRAGMA
  foreign_keys = ON is set per-connection.  The FK is declared here for
  schema correctness and forward-compatibility with PostgreSQL.
"""

from alembic import op
import sqlalchemy as sa
import logging

logger = logging.getLogger("alembic.005_add_patients_table")

# revision identifiers, used by Alembic.
revision = "005_add_patients_table"
down_revision = "004_add_correction_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Create patients table ──────────────────────────────────────────────
    op.create_table(
        "patients",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("dob", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(50), nullable=True),
        sa.Column("mrn", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_patients_id", "patients", ["id"], unique=False)
    op.create_index("ix_patients_mrn", "patients", ["mrn"], unique=False)

    # ── 2. Orphan check ───────────────────────────────────────────────────────
    # Count documents rows with a non-null patient_id that has no matching
    # row in the freshly-created (empty) patients table.
    # Because patients is new, ALL non-null patient_id values are orphans.
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM documents "
            "WHERE patient_id IS NOT NULL "
            "AND patient_id NOT IN (SELECT id FROM patients)"
        )
    )
    orphan_count = result.scalar() or 0

    msg = (
        "\n"
        "  +-----------------------------------------------------------------+\n"
        "  |  MIGRATION 005 - ORPHANED patient_id REPORT                    |\n"
        "  |                                                                 |\n"
        f" |  documents rows with patient_id set but no matching patient    |\n"
        f" |  in the new 'patients' table: {orphan_count:<36}|\n"
        "  |                                                                 |\n"
        "  |  These rows are NOT modified.  If you wish to back-fill stub   |\n"
        "  |  Patient records for these IDs, do so before enabling strict   |\n"
        "  |  FK enforcement (e.g. PRAGMA foreign_keys = ON).               |\n"
        "  +-----------------------------------------------------------------+\n"
    )
    print(msg)
    logger.info("Orphaned documents.patient_id count: %d", orphan_count)

    # ── 3. Add FK constraint (batch mode for SQLite compatibility) ────────────
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_documents_patient_id",          # constraint name
            "patients",                          # referent table
            ["patient_id"],                      # local columns
            ["id"],                              # remote columns
            ondelete="SET NULL",
        )


def downgrade() -> None:
    # Remove FK constraint first (batch mode)
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.drop_constraint("fk_documents_patient_id", type_="foreignkey")

    op.drop_index("ix_patients_mrn", table_name="patients")
    op.drop_index("ix_patients_id", table_name="patients")
    op.drop_table("patients")
