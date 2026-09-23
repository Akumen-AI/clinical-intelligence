import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import synonym
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    run_id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    id = synonym("run_id")
    
    document_id = Column(
        String(36),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    extractor_name = Column(String(100), nullable=False)
    extractor_version = Column(String(100), nullable=False)
    config_version = Column(String(100), nullable=True)
    
    status = Column(String(50), nullable=False, default="processing")
    
    supersedes_run_id = Column(
        String(36),
        ForeignKey("extraction_runs.run_id", ondelete="SET NULL"),
        nullable=True,
    )
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
