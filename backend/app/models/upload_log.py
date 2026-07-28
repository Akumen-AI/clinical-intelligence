from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base

class UploadLogStatus(str, enum.Enum):
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"

class UploadLog(Base):
    __tablename__ = "upload_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    reason = Column(String(500), nullable=True)
    status = Column(String(50), default=UploadLogStatus.REJECTED.value, nullable=False)
    client_ip = Column(String(50), nullable=True)
    http_status = Column(Integer, nullable=True)
