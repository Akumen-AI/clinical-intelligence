import sys
from app.services.extraction.gemini_extractor import GeminiFieldExtractor
try:
    extractor = GeminiFieldExtractor()
    print("Extractor initialized.")
    res = extractor.extract("Patient Name: John Doe\nDOB: 1980-01-01", document_type="clinical_note")
    print(res)
except Exception as e:
    import traceback
    traceback.print_exc()
