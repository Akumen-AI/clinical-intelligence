import hashlib
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.correction_log import CorrectionLog
from app.schemas.correction_log import CorrectionLogCreate, CorrectionExportRow, ExportBatchResponse

PHI_FIELD_NAMES: set[str] = {
    "patient_name", "date_of_birth", "ssn", "address",
    "phone", "email", "mrn", "insurance_id",
}

def _hash_value(value: str | None) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(value.encode()).hexdigest()

def _phi_safe_value(field_name: str, value: str | None) -> str | None:
    """Return hash if field is PHI-sensitive, else return value as-is."""
    if field_name.lower() in PHI_FIELD_NAMES:
        return _hash_value(value)
    return value  # non-PHI fields (e.g. diagnosis_code) safe to export raw

class CorrectionLogService:

    async def log_correction(
        self,
        db: AsyncSession,
        payload: CorrectionLogCreate,
        reviewer_id: uuid.UUID,
        reviewer_role: str | None,
    ) -> CorrectionLog:
        """
        Persist one correction log entry atomically.
        Sets verified_at = NOW() for accept/edit; leaves NULL for reject.
        Removes the field from pending_review_queue on accept/edit.
        """
        now = datetime.now(timezone.utc)
        verified_at = now if payload.action in ("accept", "edit") else None

        action_str = payload.action.value if hasattr(payload.action, "value") else str(payload.action)

        log = CorrectionLog(
            extracted_field_id=payload.extracted_field_id,
            document_id=payload.document_id,
            action=action_str,
            before_value=payload.before_value,
            after_value=payload.after_value,
            field_name=payload.field_name,
            confidence_score=payload.confidence_score,
            reviewer_id=reviewer_id,
            reviewer_role=reviewer_role,
            reviewed_at=now,
            verified_at=verified_at,
            notes=payload.notes,
        )
        db.add(log)

        # Remove from pending_review_queue on accept/edit
        if payload.action in ("accept", "edit"):
            try:
                from app.models.pending_review import PendingReview
                stmt = (
                    select(PendingReview)
                    .where(
                        (PendingReview.document_id == str(payload.document_id)) &
                        (PendingReview.field_name == payload.field_name)
                    )
                )
                result = await db.execute(stmt)
                queue_entries = result.scalars().all()
                for queue_entry in queue_entries:
                    await db.delete(queue_entry)
            except Exception:
                pass

        await db.flush()   # catch constraint violations before commit
        await db.commit()
        await db.refresh(log)
        return log

    async def get_logs_for_document(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
    ) -> list[CorrectionLog]:
        stmt = (
            select(CorrectionLog)
            .where(CorrectionLog.document_id == document_id)
            .order_by(CorrectionLog.reviewed_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_log_by_id(
        self,
        db: AsyncSession,
        log_id: uuid.UUID,
    ) -> CorrectionLog | None:
        result = await db.execute(
            select(CorrectionLog).where(CorrectionLog.id == log_id)
        )
        return result.scalar_one_or_none()

    async def export_for_retraining(
        self,
        db: AsyncSession,
        limit: int = 1000,
        actor_user_id: uuid.UUID | None = None,
    ) -> ExportBatchResponse:
        """
        Export un-exported correction logs as PHI-safe retraining rows.
        Marks them as exported atomically so they are never double-exported.
        """
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"

        stmt = (
            select(CorrectionLog)
            .where(CorrectionLog.retraining_exported == False)
            .order_by(CorrectionLog.reviewed_at.asc())
            .limit(limit)
        )
        if db.bind and db.bind.dialect.name != "sqlite":
            stmt = stmt.with_for_update(skip_locked=True)

        result = await db.execute(stmt)
        logs = list(result.scalars().all())

        rows: list[CorrectionExportRow] = []
        ids_to_mark: list[uuid.UUID] = []

        for log in logs:
            row = CorrectionExportRow(
                log_id=log.id,
                field_id=log.extracted_field_id,
                document_id=log.document_id,
                field_name=log.field_name,
                action=log.action,
                before_value_hash=_phi_safe_value(log.field_name, log.before_value),
                after_value_hash=_phi_safe_value(log.field_name, log.after_value),
                confidence_score=log.confidence_score,
                reviewer_role=log.reviewer_role,
                reviewed_at=log.reviewed_at,
                verified=log.verified_at is not None,
                export_batch_id=batch_id,
            )
            rows.append(row)
            ids_to_mark.append(log.id)

        if ids_to_mark:
            await db.execute(
                update(CorrectionLog)
                .where(CorrectionLog.id.in_(ids_to_mark))
                .values(retraining_exported=True, export_batch_id=batch_id)
            )
            await db.commit()

            from app.services import audit_service
            await audit_service.write_entry_async(
                db=db,
                actor_user_id=actor_user_id or audit_service.SYSTEM_ACTOR_ID,
                action_type="correction_log_export",
                target_entity=f"export_batch:{batch_id}",
                patient_id=None,
                rationale=f"Exported {len(rows)} corrections in batch {batch_id}"
            )

        return ExportBatchResponse(
            batch_id=batch_id,
            exported_count=len(rows),
            rows=rows,
        )
