"""
Factory for obtaining a handwriting extraction engine.

Currently only Gemini multimodal is supported.  The factory pattern
allows future engines (e.g. a dedicated handwriting-OCR API) to be
added without touching the rest of the pipeline.
"""

from app.config import settings
from app.services.handwriting.base import HandwritingExtractor


def get_handwriting_extractor() -> HandwritingExtractor:
    """
    Returns the best available handwriting extraction engine.

    Currently supports:
      - Gemini multimodal (requires GEMINI_API_KEY)

    Raises:
        ValueError: If no suitable engine is available (no API key).
    """
    if settings.GEMINI_API_KEY:
        from app.services.handwriting.gemini_handwriting_extractor import (
            GeminiHandwritingExtractor,
        )
        print("[Handwriting Extraction] Using Gemini multimodal extractor.")
        return GeminiHandwritingExtractor()

    raise ValueError(
        "[Handwriting Extraction] No handwriting extractor available. "
        "GEMINI_API_KEY is required for handwriting extraction."
    )
