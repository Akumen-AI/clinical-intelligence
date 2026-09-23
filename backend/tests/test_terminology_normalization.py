import pytest
from app.services.terminology_service import normalize_clinical_term

def test_exact_mapping():
    result = normalize_clinical_term("medications", "Metformin 500mg")
    assert result["mapped_code"] == "860975"
    assert result["mapping_status"] == "exact"
    assert result["mapping_version"] == "RxNorm 2024-05"
    assert result["mapping_confidence"] == 1.0
    assert result["mapping_provenance"] == "synthetic_demo_curation"

def test_synonym_mapping():
    result = normalize_clinical_term("medications", "Tylenol")
    assert result["mapped_code"] == "161" # Matches Acetaminophen in mock
    assert result["mapping_status"] == "mapped" # Because raw text 'tylenol' != canonical 'Acetaminophen'
    assert result["mapping_version"] == "RxNorm 2024-05"
    assert result["mapping_confidence"] == 1.0

def test_ambiguous_mapping():
    result = normalize_clinical_term("diagnoses", "diabet")
    assert result["mapped_code"] is None
    assert result["mapping_status"] == "ambiguous"
    assert result["mapping_confidence"] == 0.5
    assert result["mapping_provenance"] == "synthetic_demo_curation"

def test_unmapped_term():
    result = normalize_clinical_term("medications", "Unknown Drug XYZ")
    assert result["mapped_code"] is None
    assert result["mapping_status"] == "unmapped"
    assert result["mapping_confidence"] == 0.0

def test_unmapped_with_llm_code():
    # If the LLM guessed a code but we can't verify it in the dictionary
    result = normalize_clinical_term("diagnoses", "Rare Condition", extracted_code="Z99.9")
    assert result["mapped_code"] == "Z99.9"
    assert result["mapping_status"] == "rejected"
    assert result["mapping_confidence"] == 0.0
    assert result["mapping_provenance"] == "llm_extraction_only"

def test_case_insensitivity():
    result = normalize_clinical_term("diagnoses", "TYPE 2 DIABETES MELLITUS")
    assert result["mapped_code"] == "E11.9"
    assert result["mapping_status"] == "exact"

def test_deterministic_repeatability():
    # Ensures the function is pure and returns the same output for the same input
    r1 = normalize_clinical_term("lab_results", "HbA1c")
    r2 = normalize_clinical_term("lab_results", "HbA1c")
    assert r1 == r2
