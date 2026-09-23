import os
from sqlalchemy import create_engine
from alembic.config import Config
from alembic import command
import app.database

SQLALCHEMY_DATABASE_URL = "sqlite:///./temp_test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

alembic_cfg = Config("alembic.ini")
alembic_cfg.attributes["connection"] = engine
command.upgrade(alembic_cfg, "head")
