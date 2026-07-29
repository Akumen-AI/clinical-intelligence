from pydantic import BaseModel
from abc import ABC, abstractmethod

class ClassificationResult(BaseModel):
    document_type: str
    # Note: This confidence score is the LLM's self-reported number. It is not derived 
    # from logprobs/embedding similarity, and self-reported LLM confidence is known to 
    # be poorly calibrated. Tune DOCUMENT_CLASSIFICATION_THRESHOLD with this caveat in mind.
    confidence: float

class DocumentClassifier(ABC):
    
    @abstractmethod
    def classify(self, text: str) -> ClassificationResult:
        """Classify the provided document text into one of the supported types."""
        pass

    def _get_prompt(self, text: str) -> str:
        return f"""You are a medical document classifier.

Classify this document into exactly one of:

- Prescription
- Lab Report
- Discharge Summary
- Referral
- Admission Form
- Unknown

Return ONLY JSON.

Schema:

{{
    "document_type": "",
    "confidence": 0.0
}}

Do not include markdown.

Do not explain your reasoning.

Document Text:
{text}"""
