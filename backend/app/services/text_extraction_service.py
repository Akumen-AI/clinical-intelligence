"""
Text extraction service for document classification pipeline.

Extracts text from PDFs (embedded text) and images (via PaddleOCR).
Used by the classification step to get actual document content instead of mock text.
"""

import os
import fitz  # PyMuPDF


# Resolve backend root directory once
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Lazy-loaded PaddleOCR instance (heavy to initialize, so we cache it)
_paddle_ocr_instance = None


def _get_paddle_ocr():
    """Lazily initialize and return the PaddleOCR instance."""
    global _paddle_ocr_instance
    if _paddle_ocr_instance is None:
        from paddleocr import PaddleOCR
        # use_angle_cls=True enables text direction detection (useful for rotated docs)
        # lang='en' for English medical documents
        _paddle_ocr_instance = PaddleOCR(use_angle_cls=True, lang='en')
    return _paddle_ocr_instance


def _extract_text_with_paddle(image_path: str) -> str:
    """
    Extract text from an image file using PaddleOCR.
    Returns the concatenated text from all detected regions.
    """
    try:
        ocr = _get_paddle_ocr()
        # In PaddleOCR 3.7.0 (PaddleX based), the API uses predict() and returns a dict list
        # We need to extract the 'rec_text' list from the first result dictionary
        result = ocr.predict(image_path)
        
        if not result:
            return ""

        # result is a generator or list of dict-like objects. We take the first one.
        res_dict = next(iter(result))
        
        # In PaddleOCR 3.7.0 / PaddleX, the key is 'rec_texts' (plural)
        if hasattr(res_dict, 'keys') and 'rec_texts' in res_dict and res_dict['rec_texts']:
            # It's a list of strings
            return "\n".join(res_dict['rec_texts']).strip()
            
        return ""
    except Exception as e:
        print(f"[Text Extraction] PaddleOCR failed: {e}")
        return ""


def extract_text_from_pdf(filepath: str) -> str:
    """
    Extract embedded text from all pages of a PDF using PyMuPDF.
    Falls back to OCR-based extraction if no embedded text is found.
    """
    abs_path = os.path.abspath(os.path.join(_BACKEND_DIR, filepath))
    doc = fitz.open(abs_path)
    text_parts = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        page_text = page.get_text("text").strip()
        if page_text:
            text_parts.append(page_text)

    doc.close()

    full_text = "\n\n".join(text_parts).strip()

    # If PDF has no embedded text (scanned PDF), try OCR via image extraction
    if not full_text:
        full_text = _ocr_pdf_pages(abs_path)

    return full_text


def extract_text_from_image(filepath: str) -> str:
    """
    Extract text from an image file using PaddleOCR.
    """
    abs_path = os.path.abspath(os.path.join(_BACKEND_DIR, filepath))
    return _extract_text_with_paddle(abs_path)


def _ocr_pdf_pages(abs_path: str) -> str:
    """
    For scanned PDFs with no embedded text, render pages to images
    and run PaddleOCR on each page.
    """
    try:
        import io
        import tempfile

        doc = fitz.open(abs_path)
        text_parts = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Render page at 300 DPI for better OCR accuracy
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")

            # PaddleOCR can accept a file path, so write to a temp file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(img_bytes)
                tmp_path = tmp.name

            try:
                page_text = _extract_text_with_paddle(tmp_path)
                if page_text:
                    text_parts.append(page_text)
            finally:
                os.unlink(tmp_path)

        doc.close()
        return "\n\n".join(text_parts).strip()
    except Exception as e:
        print(f"[Text Extraction] OCR of scanned PDF failed: {e}")
        return ""


def extract_text(filepath: str, filetype: str) -> str:
    """
    Main entry point: extract text from a document based on its file type.

    Args:
        filepath: Relative path to the file (from backend root), e.g. 'uploads/xxx.pdf'
        filetype: File extension, e.g. 'pdf', 'png', 'jpg'

    Returns:
        Extracted text string, or empty string if extraction fails.
    """
    filetype_lower = filetype.lower()

    if filetype_lower == "pdf":
        text = extract_text_from_pdf(filepath)
    elif filetype_lower in ("png", "jpg", "jpeg", "tiff"):
        text = extract_text_from_image(filepath)
    else:
        print(f"[Text Extraction] Unsupported file type: {filetype}")
        text = ""

    if text:
        print(f"[Text Extraction] Extracted {len(text)} characters from {os.path.basename(filepath)}")
    else:
        print(f"[Text Extraction] No text extracted from {os.path.basename(filepath)}")

    return text
