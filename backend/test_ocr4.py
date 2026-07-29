import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app.services.text_extraction_service import _get_paddle_ocr

image_path_raw = "uploads/8972eee4-863a-4467-88fa-92bc19354be7_sample_3.png"

try:
    ocr = _get_paddle_ocr()
    result = ocr.predict(image_path_raw)
    
    # Let's inspect the type and fields
    print(f"Type of result: {type(result)}")
    
    first_item = next(iter(result))
    print(f"Type of first_item: {type(first_item)}")
    
    # If it's a dict
    if isinstance(first_item, dict):
        print(f"Keys: {first_item.keys()}")
        print(f"rec_text present: {'rec_text' in first_item}")
        
    # Maybe it's a custom Paddlex object that acts like a dict but we need to access it differently?
    if hasattr(first_item, 'keys'):
        print(f"Keys (hasattr): {first_item.keys()}")
    
    # Try getting the rec_text
    try:
        text_list = first_item['rec_text']
        print(f"Length of text_list: {len(text_list)}")
        print(f"First element: {text_list[0]}")
    except Exception as inner_e:
        print(f"Failed to access 'rec_text': {inner_e}")
        
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
