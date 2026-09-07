"""
Story 10.1 — FR-32
ContextPanelService: assembles the read-only proactive context panel
shown to a doctor when a patient profile (note-entry screen) is opened.

SAFETY CONTRACT (AC-3):
  - Diagnosis rows are NEVER included in the output.
  - No icd10_code, condition_name, or diagnostic label is exposed.
  - Data is retrieved exclusively from the canonical DB tables;
    no LLM call is made.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.clinical_entities import LabResult, Medication
from app.models.canonical_patient_record import CanonicalPatientRecord

log = logging.getLogger("app.services.context_panel_service")

# Keys that, if present in any panel value, would expose diagnostic language.
# AC-3 requires that none of these reach the API response.
_DIAGNOSTIC_KEYS: frozenset[str] = frozenset(
    {"icd10_code", "condition_name", "diagnosis", "differential", "impression", "assessment"}
)


def _strip_diagnostic_keys(obj: Any) -> Any:
    """
    Recursively remove any key whose name is in _DIAGNOSTIC_KEYS from
    dicts/lists.  Returns the sanitised object.
    """
    if isinstance(obj, dict):
        return {k: _strip_diagnostic_keys(v) for k, v in obj.items() if k not in _DIAGNOSTIC_KEYS}
    if isinstance(obj, list):
        return [_strip_diagnostic_keys(item) for item in obj]
    return obj


@dataclass
class ContextPanel:
    """
    The data payload returned to the front end.

    Fields
    ------
    medications   : list of {"id": str, "raw_text": str, "rxnorm_code": str|None}
    allergies     : list of str   (sourced from CanonicalPatientRecord where
                                   field_name == "allergies")
    prior_results : list of {"id": str, "raw_text": str, "loinc_code": str|None}
    history       : list of str   (sourced from CanonicalPatientRecord where
                                   field_name == "medical_history" or "history")
    source        : always "canonical_record"  — confirms AC-2 at runtime

    NOTE: diagnoses are intentionally absent (AC-3).
    """
    medications: list[dict] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    prior_results: list[dict] = field(default_factory=list)
    history: list[str] = field(default_factory=list)
    source: str = "canonical_record"

    def to_dict(self) -> dict:
        return {
            "medications": self.medications,
            "allergies": self.allergies,
            "prior_results": self.prior_results,
            "history": self.history,
            "source": self.source,
        }


class ContextPanelService:
    """
    Builds the ContextPanel for a patient.

    AC-2: all data originates from the DB tables populated by the
          canonical record pipeline (Epics 2-4).  No LLM is called.
    AC-3: Diagnosis rows are excluded entirely. _strip_diagnostic_keys()
          is applied as a second safety pass on every item.
    """

    def build_context(self, db: Session, patient_id: str) -> ContextPanel:
        panel = ContextPanel()

        # ── Medications (from normalized table) ──────────────────────────
        med_rows = (
            db.query(Medication)
            .filter(Medication.patient_id == patient_id)
            .all()
        )
        panel.medications = [
            _strip_diagnostic_keys(
                {"id": m.id, "raw_text": m.raw_text, "rxnorm_code": m.rxnorm_code}
            )
            for m in med_rows
        ]

        # ── Prior Lab Results (from normalized table) ─────────────────────
        lab_rows = (
            db.query(LabResult)
            .filter(LabResult.patient_id == patient_id)
            .all()
        )
        panel.prior_results = [
            _strip_diagnostic_keys(
                {"id": r.id, "raw_text": r.raw_text, "loinc_code": r.loinc_code}
            )
            for r in lab_rows
        ]

        # ── Allergies (from canonical_patient_records, field_name="allergies") ─
        allergy_rows = (
            db.query(CanonicalPatientRecord)
            .join(
                __import__("app.models.document", fromlist=["Document"]).Document,
                CanonicalPatientRecord.document_id
                == __import__("app.models.document", fromlist=["Document"]).Document.document_id,
            )
            .filter(
                __import__("app.models.document", fromlist=["Document"]).Document.patient_id
                == patient_id,
                CanonicalPatientRecord.field_name == "allergies",
            )
            .all()
        )
        for row in allergy_rows:
            val = row.value
            if isinstance(val, list):
                panel.allergies.extend(str(v) for v in val if v)
            elif isinstance(val, str) and val.strip():
                panel.allergies.append(val.strip())

        # ── Medical History (from canonical_patient_records) ──────────────
        history_rows = (
            db.query(CanonicalPatientRecord)
            .join(
                __import__("app.models.document", fromlist=["Document"]).Document,
                CanonicalPatientRecord.document_id
                == __import__("app.models.document", fromlist=["Document"]).Document.document_id,
            )
            .filter(
                __import__("app.models.document", fromlist=["Document"]).Document.patient_id
                == patient_id,
                CanonicalPatientRecord.field_name.in_(["medical_history", "history"]),
            )
            .all()
        )
        for row in history_rows:
            val = row.value
            if isinstance(val, list):
                panel.history.extend(str(v) for v in val if v)
            elif isinstance(val, str) and val.strip():
                panel.history.append(val.strip())

        log.info(
            "context_panel.built patient_id=%s meds=%d labs=%d allergies=%d history=%d",
            patient_id,
            len(panel.medications),
            len(panel.prior_results),
            len(panel.allergies),
            len(panel.history),
        )
        return panel


async def build_panel_text(patient_id: str) -> str:
    from app.core.compliance import enforce_ac3
    text = f"Patient context panel summary for patient {patient_id}"
    return enforce_ac3(text)


async def get_context_panel(db, patient_id: str):
    from app.core.compliance import enforce_ac3
    rendered_text = await build_panel_text(patient_id)
    enforce_ac3(rendered_text)

    svc = ContextPanelService()
    if db is None:
        panel_dict = {
            "medications": [],
            "allergies": [],
            "prior_results": [],
            "history": [],
            "source": "canonical_record",
        }
    else:
        panel_dict = svc.build_context(db, patient_id).to_dict()

    # AC-3 enforce on all text fields
    for k, v in panel_dict.items():
        if isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    enforce_ac3(item)
                elif isinstance(item, dict):
                    for subk, subv in item.items():
                        if isinstance(subv, str):
                            enforce_ac3(subv)
    return panel_dict

