import os
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.pending_review import SystemConfig

logger = logging.getLogger("app.services.watched_folder_config_service")


def get_watched_folder_path_info(db: Optional[Session] = None) -> Tuple[str, str]:
    """
    Returns (path_value, source) where source is 'db' or 'env'.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        config_rec = (
            db.query(SystemConfig)
            .filter(SystemConfig.key == "WATCHED_FOLDER_PATH")
            .first()
        )
        if config_rec and config_rec.value:
            return config_rec.value.strip(), "db"
        return settings.WATCHED_FOLDER_PATH, "env"
    finally:
        if close_db:
            db.close()


def set_watched_folder_path(path: str, db: Optional[Session] = None) -> Tuple[str, str]:
    """
    Validates and sets the watched folder path.
    Rejects empty/whitespace paths.
    Creates the directory and raises a clear ValueError if creation fails.
    Persists setting in SystemConfig table.
    """
    if not path or not path.strip():
        raise ValueError("Watched folder path cannot be empty or whitespace.")

    clean_path = path.strip()

    try:
        os.makedirs(clean_path, exist_ok=True)
    except Exception as e:
        logger.error(f"[WatchedFolderConfig] Failed to create directory '{clean_path}': {e}")
        raise ValueError(f"Failed to create directory '{clean_path}'. Please check permissions: {e}") from e

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        config_rec = (
            db.query(SystemConfig)
            .filter(SystemConfig.key == "WATCHED_FOLDER_PATH")
            .first()
        )
        if config_rec:
            config_rec.value = clean_path
            config_rec.updated_at = datetime.now(timezone.utc)
        else:
            config_rec = SystemConfig(
                key="WATCHED_FOLDER_PATH",
                value=clean_path,
                updated_at=datetime.now(timezone.utc),
            )
            db.add(config_rec)

        db.commit()
        logger.info(f"[WatchedFolderConfig] Watched folder path updated to '{clean_path}'")
        return clean_path, "db"
    except Exception as e:
        db.rollback()
        logger.error(f"[WatchedFolderConfig] Failed to persist watched folder path: {e}")
        raise e
    finally:
        if close_db:
            db.close()


def get_watched_folder_interval(db: Optional[Session] = None) -> int:
    """
    Returns the current WATCHED_FOLDER_POLL_INTERVAL_SECONDS from DB or settings.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        config_rec = (
            db.query(SystemConfig)
            .filter(SystemConfig.key == "WATCHED_FOLDER_POLL_INTERVAL_SECONDS")
            .first()
        )
        if config_rec and config_rec.value:
            try:
                return int(config_rec.value.strip())
            except ValueError:
                pass
        return settings.WATCHED_FOLDER_POLL_INTERVAL_SECONDS
    finally:
        if close_db:
            db.close()

