import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.audit_log import GUID
from app.db.base import Base


class ReportRequest(Base):
    __tablename__ = "report_requests"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    nl_query: Mapped[str] = mapped_column(String(1000), nullable=False)
    resolved_filters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    chart_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
