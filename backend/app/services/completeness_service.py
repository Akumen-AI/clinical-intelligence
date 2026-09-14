import structlog
from uuid import UUID
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config.complaint_checklists import COMPLAINT_CHECKLISTS, BANNED_PHRASES
from app.models.department_completeness_setting import DepartmentCompletenessSetting
from app.models.patient import Patient
from app.models.clinical_entities import Allergy, Medication, Vital, Procedure, LabResult
from app.models.canonical_patient_record import CanonicalPatientRecord
from app.models.document import Document
from app.schemas.completeness import CompletenessCheckResponse, MissingFieldItem

log = structlog.get_logger()


LABEL_TO_FIELD: dict[str, str] = {
    "Onset date": "onset_date",
    "Duration": "duration",
    "Known allergies": "allergies",
    "Current medications": "current_medications",
    "Travel history (last 30 days)": "travel_history",
    "Smoking history": "smoking_history",
    "Occupational exposure": "occupational_exposure",
    "Vaccination history": "vaccination_history",
    "Last normal bowel movement": "last_normal_bowel_movement",
    "Dietary history (last 48 h)": "dietary_history",
    "Nausea / vomiting present": "nausea_vomiting",
    "Cough character": "cough_character",
    "Radiation pattern": "radiation_pattern",
    "Associated symptoms": "associated_symptoms",
    "Family history of cardiac events": "family_history_cardiac",
    "Exercise tolerance baseline": "exercise_tolerance",
    "Laterality": "laterality",
    "Loss of consciousness (Y/N)": "loss_of_consciousness",
    "Seizure history": "seizure_history",
    "Recent head trauma": "recent_head_trauma",
}


class CompletenessService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Banned-phrase guard — MUST be called before any label is returned
    # ------------------------------------------------------------------
    def _validate_label(self, label: str) -> None:
        lower = label.lower()
        for phrase in BANNED_PHRASES:
            if phrase in lower:
                raise ValueError(
                    f"Completeness label contains banned phrase '{phrase}': {label!r}"
                )

    # ------------------------------------------------------------------
    # Toggle check
    # ------------------------------------------------------------------
    async def is_enabled_for_department(self, department_id: UUID | str) -> bool:
        dept_str = str(department_id)
        result = await self.db.execute(
            select(DepartmentCompletenessSetting).where(
                DepartmentCompletenessSetting.department_id == dept_str
            )
        )
        setting = result.scalar_one_or_none()
        if setting is None:
            return True   # default: enabled
        return setting.enabled

    # ------------------------------------------------------------------
    # Core check
    # ------------------------------------------------------------------
    async def check(
        self,
        patient_id: UUID | str,
        complaint_type: str,
        department_id: UUID | str,
    ) -> CompletenessCheckResponse:
        """
        1. Check department toggle — if disabled, return feature_enabled=False
           with empty missing_fields.
        2. Look up checklist for complaint_type (fall back to "general").
        3. Load patient record fields; determine which checklist items are
           undocumented (null / empty string in the canonical record).
        4. Validate every field label against BANNED_PHRASES before including.
        5. Return CompletenessCheckResponse.
        Never surface diagnostic content — only field-slot labels.
        """
        patient_str = str(patient_id)
        p_uuid = UUID(patient_str) if isinstance(patient_id, str) else patient_id

        enabled = await self.is_enabled_for_department(department_id)
        if not enabled:
            log.info("completeness_check_skipped", patient_id=patient_str, reason="department_disabled")
            return CompletenessCheckResponse(
                patient_id=p_uuid,
                complaint_type=complaint_type,
                missing_fields=[],
                total_required=0,
                total_documented=0,
                feature_enabled=False,
            )

        checklist = COMPLAINT_CHECKLISTS.get(complaint_type, COMPLAINT_CHECKLISTS["general"])

        # Load patient
        result = await self.db.execute(select(Patient).where(Patient.patient_id == patient_str))
        patient = result.scalar_one_or_none()
        if patient is None:
            raise ValueError(f"Patient {patient_id} not found")

        # Pre-query related normalized tables for patient to enhance detection
        has_allergies = False
        has_meds = False
        try:
            alg_res = await self.db.execute(select(Allergy).where(Allergy.patient_id == patient_str))
            has_allergies = len(alg_res.scalars().all()) > 0
            med_res = await self.db.execute(select(Medication).where(Medication.patient_id == patient_str))
            has_meds = len(med_res.scalars().all()) > 0
        except Exception:
            pass

        # Query generic canonical records for patient if documents exist
        canonical_fields: set[str] = set()
        try:
            doc_res = await self.db.execute(select(Document.document_id).where(Document.patient_id == patient_str))
            doc_ids = list(doc_res.scalars().all())
            if doc_ids:
                can_res = await self.db.execute(select(CanonicalPatientRecord.field_name).where(CanonicalPatientRecord.document_id.in_(doc_ids)))
                canonical_fields = set(can_res.scalars().all())
        except Exception:
            pass

        missing: list[MissingFieldItem] = []
        documented_count = 0

        for label in checklist:
            self._validate_label(label)  # AC-3 guard
            field_attr = LABEL_TO_FIELD.get(label)

            value = getattr(patient, field_attr, None) if field_attr else None

            # Special checks for allergies & medications normalized entities or canonical records
            if label == "Known allergies" and has_allergies:
                value = True
            elif label == "Current medications" and has_meds:
                value = True
            elif field_attr and field_attr in canonical_fields:
                value = True

            is_missing = value is None or (isinstance(value, str) and not value.strip())

            if is_missing:
                missing.append(MissingFieldItem(field_label=label))
            else:
                documented_count += 1

        log.info(
            "completeness_check_complete",
            patient_id=patient_str,
            complaint_type=complaint_type,
            missing=len(missing),
        )

        return CompletenessCheckResponse(
            patient_id=p_uuid,
            complaint_type=complaint_type,
            missing_fields=missing,
            total_required=len(checklist),
            total_documented=documented_count,
            feature_enabled=True,
        )
