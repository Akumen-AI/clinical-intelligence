import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app.services.text_extraction_service import extract_text_from_image

image_path_raw = "uploads/8972eee4-863a-4467-88fa-92bc19354be7_sample_3.png"
image_path_proc = "uploads/processed_8972eee4-863a-4467-88fa-92bc19354be7_sample_3.png"

for p in [image_path_raw, image_path_proc]:
    try:
        text = extract_text_from_image(p)
        print(f"[{os.path.basename(p)}] Length: {len(text)}")
        print(f"Preview: {text[:100].replace(chr(10), ' ')}")
    except Exception as e:
        print(f"Error on {p}: {e}")
