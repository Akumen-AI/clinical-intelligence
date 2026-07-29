import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app.services.text_extraction_service import _get_paddle_ocr

image_path_raw = "uploads/8972eee4-863a-4467-88fa-92bc19354be7_sample_3.png"

try:
    ocr = _get_paddle_ocr()
    result = ocr.ocr(image_path_raw)
    
    print("--- RAW RESULT ---")
    import pprint
    pprint.pprint(result)
except Exception as e:
    print(f"Error: {e}")
