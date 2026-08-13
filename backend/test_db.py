import pytest
from app.database import SessionLocal
from tests.conftest import TestingSessionLocal
print(SessionLocal().bind.url)
print(TestingSessionLocal().bind.url)
