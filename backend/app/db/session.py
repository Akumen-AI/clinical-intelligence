import os
from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from app.database import Base, DATABASE_URL as SYNC_DATABASE_URL

DATABASE_URL = os.getenv("DATABASE_URL", SYNC_DATABASE_URL)

def _get_async_url(url: str) -> str:
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///")
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    return url

ASYNC_DATABASE_URL = _get_async_url(DATABASE_URL)

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in ASYNC_DATABASE_URL else {}
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

sync_engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def get_sync_db() -> Generator[Session, None, None]:
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

get_db = get_sync_db
