"""
Abstract base class and result model for handwriting extraction providers.

Follows the same provider-abstraction pattern used in:
  - app/services/classification/base.py  (DocumentClassifier)
  - app/services/extraction/base.py      (ClinicalFieldExtractor)

The interface accepts a raw image path (not pre-extracted text) because
multimodal vision models read handwriting directly from the image — they
don't need an OCR-text intermediary and in fact perform worse with one.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.extracted_field import ClinicalFieldsSchema


class HandwritingExtractionResult(BaseModel):
    """Result of handwriting extraction from a document image."""

    raw_text: str = ""
    """Full transcribed text as the model reads it."""

    fields: ClinicalFieldsSchema = Field(default_factory=ClinicalFieldsSchema)
    """Structured clinical fields parsed from the handwritten content."""

    field_confidences: Dict[str, float] = Field(default_factory=dict)
    """Per-field confidence scores reported by the extraction model."""

    illegible_fields: List[str] = Field(default_factory=list)
    """
    Field names the model flagged as ILLEGIBLE — i.e., it could not read
    the handwritten content with reasonable confidence.  These fields will
    be mapped to:
        ExtractedField.confidence_score = 0.0
        ExtractedField.verification_status = "illegible"
        Document.needs_manual_review = True
    """


class HandwritingExtractor(ABC):
    """
    Abstract interface for handwriting extraction engines.

    Implementations receive a path to the raw document image and return
    structured clinical fields plus illegibility flags.  The underlying
    engine (Gemini multimodal today, a dedicated handwriting-OCR API
    tomorrow) can be swapped without touching the rest of the pipeline.
    """

    @abstractmethod
    def extract_from_image(
        self,
        image_path: str,
        document_type: Optional[str] = None,
    ) -> HandwritingExtractionResult:
        """
        Extract text and structured clinical fields from a handwritten
        document image.

        Args:
            image_path: Absolute path to the document image file.
            document_type: Optional hint (e.g. "Prescription") for the
                extraction prompt.

        Returns:
            HandwritingExtractionResult with transcribed text, structured
            fields, per-field confidences, and illegible-field flags.
        """
        pass
