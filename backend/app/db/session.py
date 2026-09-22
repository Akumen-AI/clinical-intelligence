import os
from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from app.database import Base, DATABASE_URL as SYNC_DATABASE_URL

DATABASE_URL = os.getenv("DATABASE_URL", SYNC_DATABASE_URL)


sync_engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


def get_sync_db() -> Generator[Session, None, None]:
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

get_db = get_sync_db
