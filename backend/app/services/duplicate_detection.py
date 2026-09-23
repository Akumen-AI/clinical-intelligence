import os
import re
import uuid
from datetime import datetime, timezone
import jellyfish

from sqlalchemy import select, update, or_, and_
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.patient_duplicate_flag import PatientDuplicateFlag
from app.models.document import Document
from app.models.visit import Visit
from app.models.note import Note
from app.models.clinical_entities import Medication, LabResult, Vital, Procedure, Allergy
from app.models.rag_chunk import PatientRAGChunk
from app.models.canonical_patient_record import CanonicalPatientRecord
from app.services import audit_service


def normalize_name(name: str | None) -> str:
    if not name:
        return ""
    cleaned = re.sub(r'[^\w\s]', '', name.lower())
    tokens = sorted(cleaned.split())
    return " ".join(tokens)


class DuplicateDetectionService:
    """
    Heuristic matching: name similarity + exact DOB + partial MRN/ID overlap.
    Never reads from or writes to the Diagnosis table (AC-3).
    """

    @property
    def SIMILARITY_THRESHOLD(self) -> float:
        val = os.getenv("DUPLICATE_THRESHOLD")
        if val:
            try:
                return float(val)
            except ValueError:
                pass
        return 0.80

    def scan_all_patients(self, db: Session) -> list[PatientDuplicateFlag]:
        """
        Efficient duplicate detection using blocking.
        Matching heuristic requires either exact DOB match OR MRN prefix match.
        We group by DOB and MRN prefix to avoid O(N^2) full comparisons.
        """
        patients = db.query(Patient).filter(or_(Patient.status.is_(None), Patient.status != "merged")).all()

        created_flags: list[PatientDuplicateFlag] = []
        threshold = self.SIMILARITY_THRESHOLD
        
        from collections import defaultdict
        
        dob_blocks = defaultdict(list)
        mrn_blocks = defaultdict(list)
        
        for p in patients:
            if p.dob:
                dob_blocks[p.dob.strip()].append(p)
            mrn = (p.mrn or p.patient_number or "").strip()[:6].lower()
            if mrn:
                mrn_blocks[mrn].append(p)
                
        def check_pair(p_a, p_b, checked_pairs):
            pair_id = tuple(sorted([str(p_a.id), str(p_b.id)]))
            if pair_id in checked_pairs:
                return
            checked_pairs.add(pair_id)
            
            norm_a = normalize_name(p_a.name)
            norm_b = normalize_name(p_b.name)
            name_sim = jellyfish.jaro_winkler_similarity(norm_a, norm_b) if norm_a and norm_b else 0.0

            dob_match = 1.0 if (p_a.dob and p_b.dob and p_a.dob.strip() == p_b.dob.strip()) else 0.0
            mrn_a = (p_a.mrn or p_a.patient_number or "").strip()[:6]
            mrn_b = (p_b.mrn or p_b.patient_number or "").strip()[:6]
            mrn_match = 1.0 if (mrn_a and mrn_b and mrn_a.lower() == mrn_b.lower()) else 0.0

            score = (name_sim * 0.5) + (dob_match * 0.3) + (mrn_match * 0.2)
            has_name_match = name_sim > 0.0
            has_other_factor = (dob_match == 1.0) or (mrn_match == 1.0)

            if score >= threshold and has_name_match and has_other_factor:
                id_a = str(p_a.id)
                id_b = str(p_b.id)

                existing = db.query(PatientDuplicateFlag).filter(
                    or_(
                        and_(PatientDuplicateFlag.patient_a_id == id_a, PatientDuplicateFlag.patient_b_id == id_b),
                        and_(PatientDuplicateFlag.patient_a_id == id_b, PatientDuplicateFlag.patient_b_id == id_a)
                    )
                ).first()

                if not existing:
                    reasons = []
                    if name_sim > 0.0: reasons.append("name")
                    if dob_match == 1.0: reasons.append("dob")
                    if mrn_match == 1.0: reasons.append("partial_id")

                    new_flag = PatientDuplicateFlag(
                        id=uuid.uuid4(),
                        patient_a_id=id_a,
                        patient_b_id=id_b,
                        similarity_score=round(score, 4),
                        match_reasons=reasons,
                        status="pending"
                    )
                    db.add(new_flag)
                    created_flags.append(new_flag)
                    
        checked_pairs = set()
        
        # Check DOB blocks
        for block in dob_blocks.values():
            if len(block) > 1:
                for i in range(len(block)):
                    for j in range(i + 1, len(block)):
                        check_pair(block[i], block[j], checked_pairs)
                        
        # Check MRN blocks
        for block in mrn_blocks.values():
            if len(block) > 1:
                for i in range(len(block)):
                    for j in range(i + 1, len(block)):
                        check_pair(block[i], block[j], checked_pairs)

        if created_flags:
            db.commit()
            for f in created_flags:
                db.refresh(f)

        return created_flags

    def merge_patients(
        self,
        db: Session,
        flag_id: uuid.UUID | str,
        keep_patient_id: uuid.UUID | str,
        current_user: any,
    ) -> Patient:
        """
        Merge the 'other' patient into keep_patient_id:
          1. Reassign all documents, timeline events, and visit records from
             the discarded patient to keep_patient_id.
          2. Set PatientDuplicateFlag.status = 'merged', merged_into_id = keep_patient_id,
             resolved_by, resolved_at.
          3. Soft-delete or mark the discarded patient record as 'merged'.
          4. Write an audit log entry (action='patient_merge').
          5. Never touch the Diagnosis table.
        """
        flag_str_id = str(flag_id)
        keep_str_id = str(keep_patient_id)

        flag = db.query(PatientDuplicateFlag).filter(PatientDuplicateFlag.id == flag_str_id).first()
        if not flag:
            raise ValueError(f"Flag {flag_id} not found")

        id_a = str(flag.patient_a_id)
        id_b = str(flag.patient_b_id)

        if keep_str_id not in (id_a, id_b):
            raise ValueError(f"Target patient_id {keep_patient_id} is not part of duplicate flag {flag_id}")

        discarded_str_id = id_b if keep_str_id == id_a else id_a

        keep_patient = db.query(Patient).filter(Patient.patient_id == keep_str_id).first()
        discarded_patient = db.query(Patient).filter(Patient.patient_id == discarded_str_id).first()

        if not keep_patient:
            raise ValueError(f"Keep patient {keep_patient_id} not found")

        # 1. Reassign records (EXCLUDING Diagnosis)
        for model_cls in [Document, Visit, Note, Medication, LabResult, Vital, Procedure, Allergy, PatientRAGChunk, CanonicalPatientRecord]:
            if hasattr(model_cls, "patient_id"):
                db.execute(
                    update(model_cls)
                    .where(model_cls.patient_id == discarded_str_id)
                    .values(patient_id=keep_str_id)
                )

        # 2. Update flag
        flag.status = "merged"
        flag.merged_into_id = keep_str_id
        flag.resolved_by = str(current_user.id) if hasattr(current_user, "id") else None
        flag.resolved_at = datetime.now(timezone.utc)

        # 3. Soft-delete / mark discarded patient
        if discarded_patient:
            discarded_patient.status = "merged"
            discarded_patient.duplicate_of = keep_str_id

        # 4. Audit log
        actor_id = current_user.id if hasattr(current_user, "id") else uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
        audit_service.write_entry(
            db=db,
            actor_user_id=actor_id,
            action_type="patient_merge",
            target_entity=f"patient:{keep_str_id}",
            rationale=f"Merged discarded patient {discarded_str_id} into {keep_str_id}",
            patient_id=keep_str_id
        )

        db.commit()
        db.refresh(keep_patient)
        return keep_patient

    def ignore_flag(
        self,
        db: Session,
        flag_id: uuid.UUID | str,
        current_user: any,
    ) -> PatientDuplicateFlag:
        """Set flag status = 'ignored', resolved_by, resolved_at. Log audit."""
        flag_str_id = str(flag_id)
        flag = db.query(PatientDuplicateFlag).filter(PatientDuplicateFlag.id == flag_str_id).first()
        if not flag:
            raise ValueError(f"Flag {flag_id} not found")

        flag.status = "ignored"
        flag.resolved_by = str(current_user.id) if hasattr(current_user, "id") else None
        flag.resolved_at = datetime.now(timezone.utc)

        actor_id = current_user.id if hasattr(current_user, "id") else uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
        audit_service.write_entry(
            db=db,
            actor_user_id=actor_id,
            action_type="ignore_duplicate_flag",
            target_entity=f"duplicate_flag:{flag_str_id}",
            rationale=f"Flag {flag_str_id} ignored",
            patient_id=str(flag.patient_a_id)
        )

        db.commit()
        db.refresh(flag)
        return flag
