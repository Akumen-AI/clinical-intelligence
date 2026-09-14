import os
import uuid
import time
import shutil
import logging
import mimetypes
from sqlalchemy.orm import Session

from app.services.watched_folder_config_service import get_watched_folder_path_info
from app.utils.validators import detect_corruption, FileValidationError
from app.services.validation_service import ValidationService
from app.services import upload_service
from app.services import audit_service

logger = logging.getLogger("app.services.folder_watcher_service")

def scan_watched_folder(db: Session, actor_user_id: uuid.UUID) -> dict:
    """
    Scans the watched folder root for new files, ignoring dotfiles, _ingested/, _failed/,
    and files currently being written (mtime < 2 seconds old).
    
    Validates, ingests, and processes each valid file.
    Moves successfully ingested files to _ingested/.
    Moves validation-failed files to _failed/.
    Leaves files that encounter unexpected errors in place for the next scan cycle.
    """
    watched_path, _ = get_watched_folder_path_info(db)
    
    if not os.path.exists(watched_path):
        logger.warning(f"[FolderWatcher] Watched folder path does not exist: {watched_path}")
        return {"queued": [], "failed": []}
        
    ingested_dir = os.path.join(watched_path, "_ingested")
    failed_dir = os.path.join(watched_path, "_failed")
    
    os.makedirs(ingested_dir, exist_ok=True)
    os.makedirs(failed_dir, exist_ok=True)
    
    result = {"queued": [], "failed": []}
    current_time = time.time()
    
    try:
        entries = os.listdir(watched_path)
    except Exception as e:
        logger.error(f"[FolderWatcher] Failed to list directory {watched_path}: {e}")
        return result
        
    for entry in entries:
        if entry.startswith("."):
            continue
        if entry in ("_ingested", "_failed"):
            continue
            
        file_path = os.path.join(watched_path, entry)
        
        if not os.path.isfile(file_path):
            continue
            
        try:
            mtime = os.path.getmtime(file_path)
            if current_time - mtime < 2.0:
                # File is still potentially growing
                continue
        except Exception as e:
            logger.error(f"[FolderWatcher] Error getting mtime for {file_path}: {e}")
            continue

        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            
            guessed_type, _ = mimetypes.guess_type(entry)
            
            # Detect corruption / validate file
            ext = detect_corruption(file_bytes, entry, guessed_type)
            
            # Ingest
            document_id = upload_service.generate_uuid()
            safe_filename = upload_service.get_safe_filename(document_id, entry)
            
            upload_service.ensure_upload_directory_exists(upload_service.UPLOAD_DIR)
            target_filepath = os.path.join(upload_service.UPLOAD_DIR, safe_filename)
            
            with open(target_filepath, "wb") as f:
                f.write(file_bytes)
                
            relative_path = "uploads/" + safe_filename
            
            doc = upload_service.create_document(
                db=db,
                document_id=document_id,
                filename=entry,
                filepath=relative_path,
                filetype=ext
            )
            
            # Process synchronously as requested by folder watcher pattern
            upload_service.process_document(db, doc.document_id, actor_user_id)
            
            # Write audit trail
            audit_service.write_entry(
                db=db,
                actor_user_id=actor_user_id,
                action_type="document_uploaded",
                target_entity=f"document:{doc.document_id}",
                patient_id=None,
                rationale=f"Uploaded document {entry} via folder watcher"
            )
            
            # Move to _ingested
            shutil.move(file_path, os.path.join(ingested_dir, entry))
            result["queued"].append(doc.document_id)
            logger.info(f"[FolderWatcher] Successfully processed and ingested {entry} as {doc.document_id}")
            
        except FileValidationError as e:
            ValidationService.log_rejection(
                db=db,
                filename=entry,
                reason=e.message,
                client_ip="watcher",
                http_status=e.status_code
            )
            shutil.move(file_path, os.path.join(failed_dir, entry))
            result["failed"].append(entry)
            logger.warning(f"[FolderWatcher] Validation failed for {entry}, moved to _failed: {e.message}")
            
        except Exception as e:
            logger.error(f"[FolderWatcher] Unexpected error processing {entry}: {e}")
            # Leave file in place for next scan cycle
            continue

    return result
