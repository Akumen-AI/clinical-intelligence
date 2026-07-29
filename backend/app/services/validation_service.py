import logging
from typing import Tuple, Optional, List
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.upload_log import UploadLog, UploadLogStatus
from app.utils.validators import detect_corruption, FileValidationError

logger = logging.getLogger("validation_service")

class ValidationService:
    """
    Unified File Validation & Logging Service.
    Serves as middleware/service layer for manual uploads, background watchers,
    and API ingestion components.
    """
    
    @staticmethod
    async def validate_file(file: UploadFile) -> Tuple[bytes, str]:
        """
        Reads file content asynchronously and performs extension, MIME, size,
        and corruption detection checks.
        """
        filename = file.filename or ""
        content_type = file.content_type
        
        # Read file bytes into memory for validation
        file.file.seek(0)
        file_bytes = await file.read()
        file.file.seek(0)
        
        ext = detect_corruption(file_bytes, filename, content_type)
        return file_bytes, ext

    @staticmethod
    def log_rejection(
        db: Session,
        filename: str,
        reason: str,
        client_ip: Optional[str] = None,
        http_status: int = 400
    ) -> UploadLog:
        """
        Records every rejected upload attempt in the UploadLog database table.
        """
        log_entry = UploadLog(
            filename=filename or "unknown",
            reason=reason,
            status=UploadLogStatus.REJECTED.value,
            client_ip=client_ip,
            http_status=http_status
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        
        logger.warning(
            f"[Upload Rejected] File: '{filename}' | Reason: '{reason}' | IP: {client_ip} | Status: {http_status}"
        )
        return log_entry

    @staticmethod
    def log_acceptance(
        db: Session,
        filename: str,
        client_ip: Optional[str] = None
    ) -> UploadLog:
        """
        Records accepted upload attempt in the UploadLog database table.
        """
        log_entry = UploadLog(
            filename=filename,
            reason=None,
            status=UploadLogStatus.ACCEPTED.value,
            client_ip=client_ip,
            http_status=201
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        
        logger.info(f"[Upload Accepted] File: '{filename}' | IP: {client_ip}")
        return log_entry

    @staticmethod
    def get_upload_logs(db: Session, limit: int = 100) -> List[UploadLog]:
        """
        Retrieves recent validation log entries for audit trail.
        """
        return db.query(UploadLog).order_by(UploadLog.timestamp.desc()).limit(limit).all()
