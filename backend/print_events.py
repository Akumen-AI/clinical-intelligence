import pytest
from starlette.testclient import TestClient
import io
import time

def test_debug():
    from app.main import app
    client = TestClient(app)
    
    events = []
    
    import app.services.layout_detection_service as lds
    import app.services.text_extraction_service as tes
    import app.services.classification.factory as clf
    from app.services.extraction.rule_based_extractor import RuleBasedFieldExtractor
    import app.services.field_extraction_service as fes
    
    original_detect = lds.detect_layout
    original_extract = tes.extract_text_with_confidence
    original_preprocess = app.services.preprocessing_service.preprocess_document_file
    
    def mock_preprocess(raw_uri, filetype, db=None):
        return (raw_uri.replace("uploads/", "uploads/processed_"), 1)
        
    def mock_detect(*args, **kwargs):
        events.append("layout")
        return [
            {"type": "header", "bbox": [0, 0, 240, 45], "confidence": 0.97},
            {"type": "body", "bbox": [0, 60, 240, 160], "confidence": 0.91},
        ]
        
    def mock_extract(*args, **kwargs):
        events.append("ocr")
        return ("sample clinical text", [0.95])
        
    app.services.preprocessing_service.preprocess_document_file = mock_preprocess
    lds.detect_layout = mock_detect
    tes.extract_text_with_confidence = mock_extract
    tes.extract_text = lambda *args: "sample clinical text"
    
    class MockClassifier:
        def classify(self, *args):
            class R: pass
            r = R()
            r.document_type = "Lab Report"
            r.confidence = 0.95
            return r
            
    clf.get_document_classifier = lambda: MockClassifier()
    fes.get_field_extractor = lambda: RuleBasedFieldExtractor()
    
    response = client.post(
        "/api/v1/documents/upload",
        files=[("files", ("lab_report.png", io.BytesIO(b"fake image data"), "image/png"))],
    )
    
    document_id = response.json()["accepted"][0]["document_id"]
    
    time.sleep(2) # Wait for background tasks
    print("EVENTS:", events)
    
test_debug()
