from sqlalchemy import Boolean, Column, DateTime, String, text
from sqlalchemy.dialects.sqlite import JSON

from app.database import Base


class ScheduledReport(Base):
    __tablename__ = "scheduled_reports"

    id = Column(String, primary_key=True, server_default=text("(lower(hex(randomblob(16))))"))
    user_id = Column(String, index=True)
    report_definition = Column(JSON, nullable=False)
    schedule = Column(String, nullable=False)
    output_format = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    failure_state = Column(String, nullable=True)
