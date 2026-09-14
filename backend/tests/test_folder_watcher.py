import os
import uuid
import pytest
from unittest.mock import patch

from app.models.document import Document
from app.models.upload_log import UploadLog
from app.services.folder_watcher_service import scan_watched_folder
from app.utils.validators import FileValidationError
from tests.conftest import TestingSessionLocal
from app.services import upload_service

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def mock_detect_corruption():
    with patch("app.services.folder_watcher_service.detect_corruption") as m:
        # By default assume valid
        m.return_value = "pdf"
        yield m

@pytest.fixture
def mock_process_document():
    with patch("app.services.folder_watcher_service.upload_service.process_document") as m:
        yield m

@pytest.fixture
def isolated_upload_dir(tmp_path):
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()
    original = upload_service.UPLOAD_DIR
    upload_service.UPLOAD_DIR = str(uploads_dir)
    yield uploads_dir
    upload_service.UPLOAD_DIR = original

def _create_test_file(folder, filename, content=b"dummy", mtime_offset=10):
    filepath = folder / filename
    filepath.write_bytes(content)
    # Move mtime to the past so it's not skipped by the 2-second rule
    import time
    past_time = time.time() - mtime_offset
    os.utime(filepath, (past_time, past_time))
    return filepath

def test_new_files_are_queued(db_session, tmp_path, mock_detect_corruption, mock_process_document, isolated_upload_dir):
    # Setup
    _create_test_file(tmp_path, "file1.pdf")
    _create_test_file(tmp_path, "file2.pdf")
    
    actor_id = uuid.uuid4()
    
    with patch("app.services.folder_watcher_service.get_watched_folder_path_info", return_value=(str(tmp_path), "env")):
        result = scan_watched_folder(db_session, actor_id)
        
    assert len(result["queued"]) == 2
    assert len(result["failed"]) == 0
    
    # Assert Document rows exist
    docs = db_session.query(Document).filter(Document.filename.in_(["file1.pdf", "file2.pdf"])).all()
    assert len(docs) == 2
    
    # Assert files were moved to _ingested
    assert not (tmp_path / "file1.pdf").exists()
    assert (tmp_path / "_ingested" / "file1.pdf").exists()
    assert (tmp_path / "_ingested" / "file2.pdf").exists()

def test_duplicate_filename_does_not_overwrite(db_session, tmp_path, mock_detect_corruption, mock_process_document, isolated_upload_dir):
    actor_id = uuid.uuid4()
    
    # First scan
    _create_test_file(tmp_path, "scan001.pdf", b"content1")
    with patch("app.services.folder_watcher_service.get_watched_folder_path_info", return_value=(str(tmp_path), "env")):
        result1 = scan_watched_folder(db_session, actor_id)
        
    assert len(result1["queued"]) == 1
    doc1_id = result1["queued"][0]
    
    # Before the second scan, we need to clear out the one in _ingested 
    # so shutil.move on windows/mac doesn't fail or overwrite silently in a way that affects the test folder layout (though it's fine for the test).
    # But for safety, let's just let it overwrite or fail, or we remove it.
    (tmp_path / "_ingested" / "scan001.pdf").unlink()

    # Second scan with SAME filename but DIFFERENT content
    _create_test_file(tmp_path, "scan001.pdf", b"content2")
    with patch("app.services.folder_watcher_service.get_watched_folder_path_info", return_value=(str(tmp_path), "env")):
        result2 = scan_watched_folder(db_session, actor_id)
        
    assert len(result2["queued"]) == 1
    doc2_id = result2["queued"][0]
    
    assert doc1_id != doc2_id
    
    # Assert two distinct Document rows
    docs = db_session.query(Document).filter(Document.filename == "scan001.pdf").all()
    assert len(docs) == 2
    
    doc1 = db_session.query(Document).filter(Document.document_id == doc1_id).first()
    doc2 = db_session.query(Document).filter(Document.document_id == doc2_id).first()
    
    # They should have different stored file paths in UPLOAD_DIR
    assert doc1.raw_uri != doc2.raw_uri
    
    # Verify contents in the uploads dir to ensure neither overwrote the other
    doc1_disk_path = isolated_upload_dir / doc1.raw_uri.split("/")[-1]
    doc2_disk_path = isolated_upload_dir / doc2.raw_uri.split("/")[-1]
    
    assert doc1_disk_path.read_bytes() == b"content1"
    assert doc2_disk_path.read_bytes() == b"content2"

def test_unreadable_file_logs_and_continues(db_session, tmp_path, mock_detect_corruption, mock_process_document, isolated_upload_dir):
    # Setup 1 valid, 1 corrupt
    _create_test_file(tmp_path, "good.pdf")
    _create_test_file(tmp_path, "bad.pdf")
    
    def mock_detect(file_bytes, entry, guessed_type):
        if entry == "bad.pdf":
            raise FileValidationError("Corrupt PDF", status_code=400)
        return "pdf"
        
    mock_detect_corruption.side_effect = mock_detect
    
    actor_id = uuid.uuid4()
    
    with patch("app.services.folder_watcher_service.get_watched_folder_path_info", return_value=(str(tmp_path), "env")):
        result = scan_watched_folder(db_session, actor_id)
        
    assert len(result["queued"]) == 1
    assert len(result["failed"]) == 1
    assert "bad.pdf" in result["failed"]
    
    docs = db_session.query(Document).filter(Document.filename == "good.pdf").all()
    assert len(docs) == 1
    
    # bad.pdf shouldn't be in Documents
    bad_docs = db_session.query(Document).filter(Document.filename == "bad.pdf").all()
    assert len(bad_docs) == 0
    
    # Check that the bad file moved to _failed
    assert (tmp_path / "_failed" / "bad.pdf").exists()
    assert (tmp_path / "_ingested" / "good.pdf").exists()
    
    # Should be logged in UploadLog
    logs = db_session.query(UploadLog).filter(UploadLog.filename == "bad.pdf").all()
    assert len(logs) == 1
    assert logs[0].status == "REJECTED"
    assert logs[0].reason == "Corrupt PDF"

def test_rescan_skips_already_ingested_files(db_session, tmp_path, mock_detect_corruption, mock_process_document, isolated_upload_dir):
    _create_test_file(tmp_path, "scan_once.pdf")
    actor_id = uuid.uuid4()
    
    with patch("app.services.folder_watcher_service.get_watched_folder_path_info", return_value=(str(tmp_path), "env")):
        # First scan
        res1 = scan_watched_folder(db_session, actor_id)
        assert len(res1["queued"]) == 1
        
        # Second scan (nothing new added, file is in _ingested)
        res2 = scan_watched_folder(db_session, actor_id)
        assert len(res2["queued"]) == 0
        assert len(res2["failed"]) == 0
        
    docs = db_session.query(Document).filter(Document.filename == "scan_once.pdf").all()
    assert len(docs) == 1
