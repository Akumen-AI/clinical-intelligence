import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.text_extraction_service import extract_text_from_image

image_path = "uploads/8972eee4-863a-4467-88fa-92bc19354be7_sample_3.png"
try:
    print(f"Testing extraction on {image_path}...")
    text = extract_text_from_image(image_path)
    print(f"Extracted length: {len(text)}")
    print(f"Text preview:\n{text[:200]}")
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
