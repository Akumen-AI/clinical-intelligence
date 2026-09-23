import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from alembic.config import Config
from alembic import command
import os

engine = create_engine("sqlite:///./test_clinical_platform_debug.db", connect_args={"check_same_thread": False, "timeout": 15}, poolclass=StaticPool)

print("Before upgrade:", engine.connect().execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall())

alembic_cfg = Config(os.path.join(os.path.dirname(os.path.abspath(__file__)), "alembic.ini"))
alembic_cfg.attributes["connection"] = engine
command.upgrade(alembic_cfg, "head")

print("After upgrade:", engine.connect().execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall())
