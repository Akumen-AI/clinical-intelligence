import pytest
from app.utils.json_parser import clean_and_parse_json


def test_parse_valid_json():
    text = '{"name": "John Doe", "age": 30}'
    result = clean_and_parse_json(text)
    assert result == {"name": "John Doe", "age": 30}


def test_parse_markdown_wrapped_json():
    text = """```json
    {
        "document_type": "Prescription",
        "confidence": 0.95
    }
    ```"""
    result = clean_and_parse_json(text)
    assert result == {"document_type": "Prescription", "confidence": 0.95}


def test_parse_trailing_commas():
    text = """{
        "patient_identifier": {
            "name": "SRINIVAS",
            "gender": "Male",
        },
        "symptoms": [
            "Fever",
            "Cough",
        ],
    }"""
    result = clean_and_parse_json(text)
    assert result["patient_identifier"]["name"] == "SRINIVAS"
    assert len(result["symptoms"]) == 2


def test_parse_unescaped_newlines_in_strings():
    # Literal newline inside a string value (common in OCR/transcriptions)
    text = '{\n  "transcribed_text": "Line 1\nLine 2\nLine 3",\n  "count": 3\n}'
    result = clean_and_parse_json(text)
    assert "Line 1" in result["transcribed_text"]
    assert "Line 2" in result["transcribed_text"]
    assert result["count"] == 3


def test_parse_missing_commas_between_properties():
    text = """{
        "name": "SRINIVAS"
        "dob": "1990-01-01"
        "gender": "Male"
    }"""
    result = clean_and_parse_json(text)
    assert result["name"] == "SRINIVAS"
    assert result["dob"] == "1990-01-01"
    assert result["gender"] == "Male"


def test_parse_python_literals():
    text = "{'name': 'SRINIVAS', 'dob': None, 'active': True, 'flag': False}"
    result = clean_and_parse_json(text)
    assert result["name"] == "SRINIVAS"
    assert result["dob"] is None
    assert result["active"] is True
    assert result["flag"] is False


def test_parse_truncated_json():
    text = '{"patient_identifier": {"name": "SRINIVAS", "gender": "Male"}, "medications": [{"medication_name": "Sizodon Plus"'
    result = clean_and_parse_json(text)
    assert "patient_identifier" in result
    assert result["patient_identifier"]["name"] == "SRINIVAS"


def test_parse_with_conversational_preamble_and_epilogue():
    text = """Here is the extracted clinical data from the document image:
    {
        "document_type": "Prescription",
        "confidence": 0.92
    }
    Hope this helps with your clinical record!"""
    result = clean_and_parse_json(text)
    assert result == {"document_type": "Prescription", "confidence": 0.92}
