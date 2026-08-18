"""Acceptance tests for the isolated policy RAG boundary."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.policy_rag_chunk import PolicyRAGChunk


def test_a_policy_index_has_no_patient_columns_or_foreign_keys():
    assert "patient_id" not in PolicyRAGChunk.__table__.columns
    assert not list(PolicyRAGChunk.__table__.foreign_keys)
    assert not any("patient" in str(fk.target_fullname).lower() for fk in PolicyRAGChunk.__table__.foreign_keys)


def test_b_answer_is_derived_from_policy_document(tmp_path, monkeypatch):
    from app.services import policy_ingestion_service as ingestion
    from app.services.policy_rag_service import generate_policy_answer

    policy_dir = tmp_path / "policy_documents"
    policy_dir.mkdir()
    (policy_dir / "medication.md").write_text(
        "# Medication Policy\n\n## Section 1\nHigh-alert medications require an independent double check before administration.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ingestion, "engine", create_engine("sqlite:///:memory:"))
    local_engine = ingestion.engine
    local_session = sessionmaker(bind=local_engine)
    monkeypatch.setattr(ingestion, "SessionLocal", local_session)
    Base.metadata.create_all(local_engine, tables=[PolicyRAGChunk.__table__])
    ingestion.ingest_policy_documents(policy_dir)

    import app.services.policy_rag_service as policy_service
    monkeypatch.setattr(policy_service, "SessionLocal", local_session)
    answer = generate_policy_answer("What is required for high-alert medications?")
    assert "independent double check" in answer.lower()
    assert "patient" not in answer.lower()


def test_c_policy_modules_have_no_patient_related_imports():
    root = Path(__file__).parents[1] / "backend" / "app"
    forbidden = (
        "app.models.patient",
        "app.models.rag_chunk",
        "app.services.rag_service",
        "app.routers.patient",
        "app.api.patients",
    )
    for relative in (
        "services/policy_rag_service.py",
        "routers/policy_chatbot.py",
        "services/policy_ingestion_service.py",
    ):
        source = (root / relative).read_text(encoding="utf-8").lower()
        import_lines = [line for line in source.splitlines() if line.lstrip().startswith(("import ", "from "))]
        assert not any(any(term in line for term in forbidden) for line in import_lines), relative
