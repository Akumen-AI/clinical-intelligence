import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.document import Document
from app.models.upload_log import UploadLog
from app.models.layout_region import LayoutRegion
from app.models.extracted_field import ExtractedField
from app.database import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_clinical_platform.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False, "timeout": 15},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

import os
import asyncio
from sqlalchemy.pool import StaticPool

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    
    # Patch the global SessionLocal so Celery tasks in the same process use the test DB
    import app.database
    original_session_local = app.database.SessionLocal
    app.database.SessionLocal = TestingSessionLocal
    
    yield
    
    # Clear all data without dropping tables to avoid 'database is locked' errors
    # and to provide a clean state for each test.
    # Note: We must disable foreign keys temporarily to clear all tables in any order.
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = OFF;"))
        for table_name in Base.metadata.tables.keys():
            conn.execute(text(f"DELETE FROM {table_name}"))
        conn.execute(text("PRAGMA foreign_keys = ON;"))
        conn.commit()

    from app.services.upload_service import UPLOAD_DIR
    if os.path.exists(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            if f != ".gitkeep":
                try:
                    os.remove(os.path.join(UPLOAD_DIR, f))
                except Exception:
                    pass

@pytest.fixture
def client():
    return TestClient(app)

