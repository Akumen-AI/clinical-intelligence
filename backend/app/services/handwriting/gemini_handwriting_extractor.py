"""
Gemini multimodal handwriting extraction engine.

Sends the raw document image directly to Gemini's vision API for
handwriting transcription and structured field extraction.  Multimodal
models read handwriting far better than classical OCR because they use
contextual/vocabulary reasoning rather than pure character-shape matching.

Uses the same genai client pattern as:
  - app/services/classification/gemini_classifier.py
  - app/services/extraction/gemini_extractor.py
"""

import json
import os
import re
from typing import Optional

from google import genai
from google.genai import types as genai_types

from app.config import settings
from app.schemas.extracted_field import ClinicalFieldsSchema
from app.services.handwriting.base import (
    HandwritingExtractionResult,
    HandwritingExtractor,
)
from app.utils.json_parser import clean_and_parse_json


# Sentinel value the model is instructed to use for unreadable fields
_ILLEGIBLE_SENTINEL = "ILLEGIBLE"


class GeminiHandwritingExtractor(HandwritingExtractor):
    """
    Extracts handwritten clinical fields by sending the document image
    to Gemini's multimodal vision API.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY must be set to use GeminiHandwritingExtractor"
            )
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-3.5-flash"

    def extract_from_image(
        self,
        image_path: str,
        document_type: Optional[str] = None,
    ) -> HandwritingExtractionResult:
        """Send the image to Gemini and parse the structured response."""
        prompt = self._build_prompt(document_type)

        try:
            # Read the image file
            with open(image_path, "rb") as f:
                image_bytes = f.read()

            # Determine MIME type from extension
            ext = os.path.splitext(image_path)[1].lower()
            mime_map = {
                ".pdf": "application/pdf",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".tiff": "image/tiff",
                ".tif": "image/tiff",
                ".webp": "image/webp",
            }
            mime_type = mime_map.get(ext, "image/png")

            # Build multimodal content: image + text prompt
            image_part = genai_types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type,
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[image_part, prompt],
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )

            raw_text = response.text or ""
            data = clean_and_parse_json(raw_text, default={})

            return self._parse_response(data)

        except Exception as e:
            print(f"[Handwriting Extraction] Gemini extractor failed: {e}")
            return HandwritingExtractionResult()

    @staticmethod
    def _clean_and_parse_json(text: str) -> dict:
        """Robustly parse JSON from LLM output using the shared parser."""
        return clean_and_parse_json(text, default={})

    def _parse_response(self, data: dict) -> HandwritingExtractionResult:
        """Parse the JSON response into a HandwritingExtractionResult."""
        # Extract the transcribed text (if the model provided it)
        raw_text = data.pop("transcribed_text", "")

        # Separate the fields data from metadata
        fields_data = data.get("fields", data)

        # Identify illegible fields before validation
        illegible_fields = []
        field_confidences = {}
        cleaned_fields = {}

        for key, value in fields_data.items():
            if isinstance(value, str) and value.upper() == _ILLEGIBLE_SENTINEL:
                illegible_fields.append(key)
                cleaned_fields[key] = None
                field_confidences[key] = 0.0
            elif isinstance(value, dict):
                # Check nested dict fields for ILLEGIBLE sentinels
                has_illegible = False
                cleaned_sub = {}
                for sub_key, sub_val in value.items():
                    if isinstance(sub_val, str) and sub_val.upper() == _ILLEGIBLE_SENTINEL:
                        has_illegible = True
                        cleaned_sub[sub_key] = None
                    else:
                        cleaned_sub[sub_key] = sub_val
                if has_illegible:
                    illegible_fields.append(key)
                    field_confidences[key] = 0.0
                else:
                    field_confidences[key] = 0.85
                cleaned_fields[key] = cleaned_sub
            elif isinstance(value, list):
                # Check list items for ILLEGIBLE sentinels
                has_illegible = False
                cleaned_list = []
                for item in value:
                    if isinstance(item, str) and item.upper() == _ILLEGIBLE_SENTINEL:
                        has_illegible = True
                        continue
                    elif isinstance(item, dict):
                        cleaned_item = {}
                        for sub_key, sub_val in item.items():
                            if isinstance(sub_val, str) and sub_val.upper() == _ILLEGIBLE_SENTINEL:
                                has_illegible = True
                                cleaned_item[sub_key] = None
                            else:
                                cleaned_item[sub_key] = sub_val
                        cleaned_list.append(cleaned_item)
                    else:
                        cleaned_list.append(item)
                if has_illegible:
                    illegible_fields.append(key)
                    field_confidences[key] = 0.0
                else:
                    field_confidences[key] = 0.85
                cleaned_fields[key] = cleaned_list if cleaned_list else None
            else:
                cleaned_fields[key] = value
                field_confidences[key] = 0.85 if value is not None else 0.0

        # Validate into the standard schema
        try:
            fields = ClinicalFieldsSchema.model_validate(cleaned_fields)
        except Exception as e:
            print(f"[Handwriting Extraction] Schema validation failed: {e}")
            fields = ClinicalFieldsSchema()

        return HandwritingExtractionResult(
            raw_text=raw_text if isinstance(raw_text, str) else "",
            fields=fields,
            field_confidences=field_confidences,
            illegible_fields=illegible_fields,
        )

    def _build_prompt(self, document_type: Optional[str] = None) -> str:
        """Build the multimodal prompt for handwriting extraction."""
        doc_hint = (
            f" The document is a {document_type}." if document_type else ""
        )
        return f"""You are an expert medical document reader specializing in handwritten and mixed printed/handwritten clinical documents (e.g. prescriptions, clinical notes, lab requisitions).{doc_hint}

Examine this document image carefully. It contains handwritten text mixed with printed letterheads and form fields.

CLINICAL PRESCRIPTION & HANDWRITING GUIDELINES:
1. Patient Demographics & Vitals:
   - Patient gender is often written as 'M' (Male) or 'F' (Female). Do not confuse handwritten 'M'/'F' with adjacent digits or slashes.
   - Vitals (e.g. Blood Pressure '90/60 mmHg', Pulse, Temp) are often handwritten next to printed labels on the right or top margin.
   - Date format may be written as DD/MM/YY or DD/MM/YYYY (e.g. '11/5/24' -> '2024-05-11' or '11/5/24').

2. Medications & Medical Shorthand:
   - Recognize common brand names, generics, and dosage forms (Tab, Cap, Syr/Sys, Pouch/Sachet, Oint, Inj).
   - Interpret doctor dosage frequency shorthand:
     * '1 - 0 - 0' or '1-0' -> Once daily in morning
     * '0 - 0 - 1' or '0-1' -> Once daily at night
     * '1 - 0 - 1' or '= =' or '1-1' -> Twice daily (BID)
     * '1 - 1 - 1' -> Three times daily (TID)
     * Instructions like 'E water' / 'c water' -> 'in water' / 'with water'
     * Numbers like '10' or 'tab 10' -> Quantity 10 / Duration

3. Symptoms vs. Doctor's Instructions/Advice:
   - Patient chief complaints (prefixed by 'c/o', 'c/c', 'complaints of', e.g. 'Burning micturition', 'Fever', 'Cough') belong in 'symptoms'.
   - Doctor's general lifestyle advice/instructions (e.g. 'Rest for 5 days', 'Review after 5 days', 'Drink plenty of water') are instructions, NOT patient symptoms. If they relate to medications, put them in medication instructions; do NOT place post-treatment advice into symptoms.

4. Unreadable Text & JSON Formatting:
   - For any field you CANNOT read with reasonable confidence due to severe illegibility, return the string "ILLEGIBLE" as the value. Do NOT guess.
   - Do NOT use unescaped double quotes inside string values (use single quotes like 'tablet' instead).
   - Ensure all string values are properly JSON escaped without raw unescaped newlines.

Return ONLY valid raw JSON (no markdown codeblocks, no explanations).

REQUIRED JSON SCHEMA:
{{
  "transcribed_text": "Full transcription of all visible text in the image",
  "fields": {{
    "patient_identifier": {{
      "patient_id": "MRN or patient ID string, or null, or ILLEGIBLE",
      "name": "Patient full name, or null, or ILLEGIBLE",
      "dob": "Date of birth, or null, or ILLEGIBLE",
      "gender": "Male/Female/Other, or null, or ILLEGIBLE"
    }},
    "document_date": "Date of document (YYYY-MM-DD or as written), or null, or ILLEGIBLE",
    "ordering_physician": {{
      "name": "Doctor name, or null, or ILLEGIBLE",
      "npi_or_license": "NPI or license number, or null, or ILLEGIBLE",
      "department": "Specialty or department, or null, or ILLEGIBLE"
    }},
    "vitals": {{
      "blood_pressure": "e.g. 120/80 mmHg, or null, or ILLEGIBLE",
      "heart_rate": "e.g. 72 bpm, or null, or ILLEGIBLE",
      "respiratory_rate": "e.g. 16 /min, or null, or ILLEGIBLE",
      "temperature": "e.g. 98.6 F, or null, or ILLEGIBLE",
      "spo2": "e.g. 98%, or null, or ILLEGIBLE",
      "weight": "e.g. 70 kg, or null, or ILLEGIBLE",
      "height": "e.g. 175 cm, or null, or ILLEGIBLE",
      "bmi": "e.g. 22.8, or null, or ILLEGIBLE"
    }},
    "diagnosis": [
      {{
        "condition_name": "Diagnosis name, or ILLEGIBLE",
        "icd10_code": "ICD-10 code or null or ILLEGIBLE",
        "notes": "Notes or null or ILLEGIBLE"
      }}
    ],
    "medications": [
      {{
        "medication_name": "Drug name, or ILLEGIBLE",
        "dosage": "e.g. 500mg, or null, or ILLEGIBLE",
        "frequency": "e.g. Twice daily / BID, or null, or ILLEGIBLE",
        "route": "Oral/IV/etc., or null, or ILLEGIBLE",
        "duration": "e.g. 7 days / 10 tabs, or null, or ILLEGIBLE",
        "instructions": "Special instructions, or null, or ILLEGIBLE"
      }}
    ],
    "lab_results": [
      {{
        "test_name": "Lab test name, or ILLEGIBLE",
        "value": "Value or null or ILLEGIBLE",
        "unit": "Unit or null or ILLEGIBLE",
        "reference_range": "Range or null or ILLEGIBLE",
        "flag": "Normal/High/Low/Abnormal or null or ILLEGIBLE"
      }}
    ],
    "symptoms": ["Patient reported symptom or complaint, or ILLEGIBLE"],
    "procedures": ["Procedure or ILLEGIBLE"]
  }}
}}"""
