import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.schemas.extracted_field import ClinicalFieldsSchema


class ExtractionResult(BaseModel):
    fields: ClinicalFieldsSchema
    confidence: float = 1.0
    field_confidences: Dict[str, float] = Field(default_factory=dict)


class ClinicalFieldExtractor(ABC):
    @abstractmethod
    def extract(self, text: str, document_type: Optional[str] = None) -> ExtractionResult:
        """Extract structured clinical fields from document text."""
        pass

    def _get_prompt(self, text: str, document_type: Optional[str] = None) -> str:
        doc_type_hint = f" Document type is: '{document_type}'." if document_type else ""
        return f"""You are an expert clinical document field extraction system.{doc_type_hint}

Extract all relevant key clinical fields from the document text into the EXACT JSON schema provided below.

CRITICAL RULES:
1. Every top-level key must be present in the output JSON.
2. If a field or category is not mentioned or cannot be found in the document, you MUST explicitly set its value to null. DO NOT omit keys.
3. For patient identifier, ordering physician, and vitals, provide an object with the specified subkeys or null if completely absent.
4. For diagnosis, medications, and lab_results, provide a list of objects or null if none are mentioned.
5. Return ONLY valid raw JSON. Do not include markdown codeblocks (no ```json).

INPUT FORMAT NOTES:
- The document text may contain TAB-SEPARATED columns representing tabular data (e.g., lab results).
  Tab characters (\\t) indicate column boundaries. For example, a lab result row may look like:
  "Hemoglobin (Hb)\\t13.2\\tg/dL\\t13.0 - 17.0"
  This means: Test=Hemoglobin (Hb), Value=13.2, Unit=g/dL, Range=13.0 - 17.0
- Each line represents a row. Read across columns within a row, not down.

EXCLUSION RULES — DO NOT extract the following as lab results or clinical data:
- Phone numbers, fax numbers (e.g., "Ph: 0484-4012345")
- Addresses, websites, email addresses
- Barcode numbers, lab accession numbers, sample IDs (these go in patient_identifier if relevant)
- Timestamps (e.g., "08:30 AM", "01:15 PM") — these are collection/report times, not lab values
- Document headers/footers (lab name, logo text, disclaimers)

REQUIRED JSON SCHEMA:
{{
  "patient_identifier": {{
    "patient_id": "MRN or patient ID string or null",
    "name": "Patient full name or null",
    "dob": "Date of birth string or null",
    "gender": "Male/Female/Other or null"
  }},
  "document_date": "Date of document/visit (YYYY-MM-DD or as written) or null",
  "ordering_physician": {{
    "name": "Doctor / Provider name or null",
    "npi_or_license": "NPI or license number or null",
    "department": "Specialty or department or null"
  }},
  "vitals": {{
    "blood_pressure": "e.g. 120/80 mmHg or null",
    "heart_rate": "e.g. 72 bpm or null",
    "respiratory_rate": "e.g. 16 /min or null",
    "temperature": "e.g. 98.6 F or 37 C or null",
    "spo2": "e.g. 98% or null",
    "weight": "e.g. 70 kg or 154 lbs or null",
    "height": "e.g. 175 cm or 5'9'' or null",
    "bmi": "e.g. 22.8 or null"
  }},
  "diagnosis": [
    {{
      "condition_name": "Diagnosis/condition name",
      "icd10_code": "ICD-10 code if mentioned or null",
      "notes": "Relevant notes or null"
    }}
  ],
  "medications": [
    {{
      "medication_name": "Name of drug/medication",
      "dosage": "e.g. 500mg or null",
      "frequency": "e.g. Twice daily or BID or null",
      "route": "Oral / IV / Topical / etc. or null",
      "duration": "e.g. 7 days or null",
      "instructions": "Special instructions or null"
    }}
  ],
  "lab_results": [
    {{
      "test_name": "Name of lab test",
      "value": "Measured value or null",
      "unit": "Measurement unit (mg/dL, mmol/L, etc.) or null",
      "reference_range": "Normal range or null",
      "flag": "Normal / High / Low / Abnormal or null"
    }}
  ],
  "symptoms": ["List of reported symptoms or complaints, or null if none"],
  "procedures": ["List of performed/ordered procedures or null if none"]
}}

Document Text:
{text}"""
