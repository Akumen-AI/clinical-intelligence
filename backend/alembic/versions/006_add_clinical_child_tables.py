"""Migration 006 — Add clinical child record tables

Revision ID: 006_add_clinical_child_tables
Revises: 005_add_patients_table
Create Date: 2026-08-10

Creates six normalized child tables for the canonical patient record:
  - visits
  - medications
  - diagnoses
  - vitals
  - labs
  - procedures

All tables:
  - Use String(36) UUID primary keys (matching the documents / patients pattern)
  - Have patient_id FK → patients.id (ondelete CASCADE)
  - Have visit_id FK → visits.id (ondelete SET NULL, nullable)
  - Have source_document_id FK → documents.document_id (ondelete SET NULL,
    nullable) — populated when a record was extracted from a document via the
    extraction pipeline.  Manually-entered records leave this NULL.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006_add_clinical_child_tables"
down_revision = "005_add_patients_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── visits ────────────────────────────────────────────────────────────────
    op.create_table(
        "visits",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "patient_id",
            sa.String(36),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("visit_date", sa.Date(), nullable=True),
        sa.Column("visit_type", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_visits_id", "visits", ["id"], unique=False)
    op.create_index("ix_visits_patient_id", "visits", ["patient_id"], unique=False)

    # ── medications ───────────────────────────────────────────────────────────
    op.create_table(
        "medications",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "patient_id",
            sa.String(36),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "visit_id",
            sa.String(36),
            sa.ForeignKey("visits.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("dosage", sa.String(100), nullable=True),
        sa.Column("frequency", sa.String(100), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column(
            "source_document_id",
            sa.String(36),
            sa.ForeignKey("documents.document_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_medications_id", "medications", ["id"], unique=False)
    op.create_index("ix_medications_patient_id", "medications", ["patient_id"], unique=False)
    op.create_index("ix_medications_visit_id", "medications", ["visit_id"], unique=False)
    op.create_index("ix_medications_source_document_id", "medications", ["source_document_id"], unique=False)

    # ── diagnoses ─────────────────────────────────────────────────────────────
    op.create_table(
        "diagnoses",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "patient_id",
            sa.String(36),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "visit_id",
            sa.String(36),
            sa.ForeignKey("visits.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("diagnosis_date", sa.Date(), nullable=True),
        sa.Column(
            "source_document_id",
            sa.String(36),
            sa.ForeignKey("documents.document_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_diagnoses_id", "diagnoses", ["id"], unique=False)
    op.create_index("ix_diagnoses_patient_id", "diagnoses", ["patient_id"], unique=False)
    op.create_index("ix_diagnoses_visit_id", "diagnoses", ["visit_id"], unique=False)
    op.create_index("ix_diagnoses_source_document_id", "diagnoses", ["source_document_id"], unique=False)

    # ── vitals ────────────────────────────────────────────────────────────────
    op.create_table(
        "vitals",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "patient_id",
            sa.String(36),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "visit_id",
            sa.String(36),
            sa.ForeignKey("visits.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("vital_type", sa.String(100), nullable=False),
        sa.Column("value", sa.String(100), nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "source_document_id",
            sa.String(36),
            sa.ForeignKey("documents.document_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_vitals_id", "vitals", ["id"], unique=False)
    op.create_index("ix_vitals_patient_id", "vitals", ["patient_id"], unique=False)
    op.create_index("ix_vitals_visit_id", "vitals", ["visit_id"], unique=False)
    op.create_index("ix_vitals_source_document_id", "vitals", ["source_document_id"], unique=False)

    # ── labs ──────────────────────────────────────────────────────────────────
    op.create_table(
        "labs",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "patient_id",
            sa.String(36),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "visit_id",
            sa.String(36),
            sa.ForeignKey("visits.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("test_name", sa.String(255), nullable=False),
        sa.Column("result_value", sa.String(100), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("reference_range", sa.String(100), nullable=True),
        sa.Column("test_date", sa.Date(), nullable=True),
        sa.Column(
            "source_document_id",
            sa.String(36),
            sa.ForeignKey("documents.document_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_labs_id", "labs", ["id"], unique=False)
    op.create_index("ix_labs_patient_id", "labs", ["patient_id"], unique=False)
    op.create_index("ix_labs_visit_id", "labs", ["visit_id"], unique=False)
    op.create_index("ix_labs_source_document_id", "labs", ["source_document_id"], unique=False)

    # ── procedures ────────────────────────────────────────────────────────────
    op.create_table(
        "procedures",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "patient_id",
            sa.String(36),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "visit_id",
            sa.String(36),
            sa.ForeignKey("visits.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("procedure_name", sa.String(255), nullable=False),
        sa.Column("procedure_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "source_document_id",
            sa.String(36),
            sa.ForeignKey("documents.document_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_procedures_id", "procedures", ["id"], unique=False)
    op.create_index("ix_procedures_patient_id", "procedures", ["patient_id"], unique=False)
    op.create_index("ix_procedures_visit_id", "procedures", ["visit_id"], unique=False)
    op.create_index("ix_procedures_source_document_id", "procedures", ["source_document_id"], unique=False)


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index("ix_procedures_source_document_id", table_name="procedures")
    op.drop_index("ix_procedures_visit_id", table_name="procedures")
    op.drop_index("ix_procedures_patient_id", table_name="procedures")
    op.drop_index("ix_procedures_id", table_name="procedures")
    op.drop_table("procedures")

    op.drop_index("ix_labs_source_document_id", table_name="labs")
    op.drop_index("ix_labs_visit_id", table_name="labs")
    op.drop_index("ix_labs_patient_id", table_name="labs")
    op.drop_index("ix_labs_id", table_name="labs")
    op.drop_table("labs")

    op.drop_index("ix_vitals_source_document_id", table_name="vitals")
    op.drop_index("ix_vitals_visit_id", table_name="vitals")
    op.drop_index("ix_vitals_patient_id", table_name="vitals")
    op.drop_index("ix_vitals_id", table_name="vitals")
    op.drop_table("vitals")

    op.drop_index("ix_diagnoses_source_document_id", table_name="diagnoses")
    op.drop_index("ix_diagnoses_visit_id", table_name="diagnoses")
    op.drop_index("ix_diagnoses_patient_id", table_name="diagnoses")
    op.drop_index("ix_diagnoses_id", table_name="diagnoses")
    op.drop_table("diagnoses")

    op.drop_index("ix_medications_source_document_id", table_name="medications")
    op.drop_index("ix_medications_visit_id", table_name="medications")
    op.drop_index("ix_medications_patient_id", table_name="medications")
    op.drop_index("ix_medications_id", table_name="medications")
    op.drop_table("medications")

    op.drop_index("ix_visits_patient_id", table_name="visits")
    op.drop_index("ix_visits_id", table_name="visits")
    op.drop_table("visits")
