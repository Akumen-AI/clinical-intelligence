import os
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from alembic.config import Config
from alembic import command
from sqlalchemy import text as from_sqlalchemy_text
from app.database import Base
import app.models

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_clinical_platform_temp.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False, "timeout": 15},
    poolclass=StaticPool
)

if os.path.exists("./test_clinical_platform_temp.db"):
    os.remove("./test_clinical_platform_temp.db")
    
# Simulating test_confidence_router.py
Base.metadata.create_all(bind=engine)

alembic_cfg = Config("alembic.ini")
alembic_cfg.attributes["connection"] = engine

print("Running upgrade...")
command.upgrade(alembic_cfg, "head")
print("Upgrade finished!")
