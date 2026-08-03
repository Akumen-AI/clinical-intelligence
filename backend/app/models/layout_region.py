from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String

from app.database import Base


class LayoutRegion(Base):
    __tablename__ = "layout_regions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(
        String(36),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    region_type = Column(String(50), nullable=False)
    bbox = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
