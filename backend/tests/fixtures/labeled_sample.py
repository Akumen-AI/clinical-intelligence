"""
Labeled sample fixture for Story 2.3 spot-check tests (AC-3).

Each entry simulates a known extraction result with ground-truth correctness.
The ConfidenceEngine must produce:
  - mean(correct scores) > 0.70
  - mean(wrong scores)   < 0.50

15 labeled examples covering all field types, with a mix of correct and
incorrect/null extractions to exercise all four scoring signals.
"""

LABELED_SAMPLE = [
    # ----------------------------------------------------------------
    # CORRECT extractions — should score HIGH (> 0.70 mean)
    # ----------------------------------------------------------------
    {
        "field_name": "patient_identifier",
        "raw_value": "MRN-123456",
        "ocr_word_confidences": [0.97, 0.95],
        "layout_region": "header",
        "document_type": "lab_report",
        "field_map": {"patient_identifier": "MRN-123456", "ordering_physician": "Dr. Smith"},
        "ground_truth_correct": True,
    },
    {
        "field_name": "document_date",
        "raw_value": "15/07/2026",
        "ocr_word_confidences": [0.99],
        "layout_region": "header",
        "document_type": "prescription",
        "field_map": {"patient_identifier": "P001", "ordering_physician": "Dr. Jones"},
        "ground_truth_correct": True,
    },
    {
        "field_name": "vitals",
        "raw_value": "120 mmHg",
        "ocr_word_confidences": [0.93, 0.96],
        "layout_region": "table",
        "document_type": "discharge_summary",
        "field_map": {"patient_identifier": "P002", "ordering_physician": "Dr. White"},
        "ground_truth_correct": True,
    },
    {
        "field_name": "medications",
        "raw_value": "Metformin 500mg twice daily",
        "ocr_word_confidences": [0.91, 0.94, 0.92, 0.89],
        "layout_region": "body",
        "document_type": "prescription",
        "field_map": {"patient_identifier": "P003", "ordering_physician": "Dr. Brown"},
        "ground_truth_correct": True,
    },
    {
        "field_name": "diagnosis",
        "raw_value": "Essential Hypertension (I10)",
        "ocr_word_confidences": [0.88, 0.92, 0.90],
        "layout_region": "body",
        "document_type": "discharge_summary",
        "field_map": {"patient_identifier": "P004", "ordering_physician": "Dr. Lee"},
        "ground_truth_correct": True,
    },
    {
        "field_name": "ordering_physician",
        "raw_value": "Dr. Robert Adams, MD",
        "ocr_word_confidences": [0.96, 0.98, 0.97, 0.95],
        "layout_region": "header",
        "document_type": "prescription",
        "field_map": {"patient_identifier": "P005", "ordering_physician": "Dr. Robert Adams, MD"},
        "ground_truth_correct": True,
    },
    {
        "field_name": "lab_results",
        "raw_value": "Hemoglobin 14.5 g/dL",
        "ocr_word_confidences": [0.95, 0.93, 0.97],
        "layout_region": "table",
        "document_type": "lab_report",
        "field_map": {"patient_identifier": "P006", "ordering_physician": "Dr. Clark"},
        "ground_truth_correct": True,
    },
    {
        "field_name": "symptoms",
        "raw_value": "Severe chest pain, shortness of breath",
        "ocr_word_confidences": [0.89, 0.91, 0.87, 0.93, 0.90, 0.88],
        "layout_region": "body",
        "document_type": "discharge_summary",
        "field_map": {"patient_identifier": "P007", "ordering_physician": "Dr. Welby"},
        "ground_truth_correct": True,
    },
    {
        "field_name": "procedures",
        "raw_value": "Coronary Angiography",
        "ocr_word_confidences": [0.92, 0.94],
        "layout_region": "body",
        "document_type": "discharge_summary",
        "field_map": {"patient_identifier": "P008", "ordering_physician": "Dr. Shah"},
        "ground_truth_correct": True,
    },
    # ----------------------------------------------------------------
    # WRONG / NULL extractions — should score LOW (< 0.50 mean)
    # ----------------------------------------------------------------
    {
        "field_name": "document_date",
        "raw_value": "13/O5/2O24",   # OCR confused 0 with O
        "ocr_word_confidences": [0.41],
        "layout_region": "header",
        "document_type": "prescription",
        "field_map": {"patient_identifier": None, "ordering_physician": None},
        "ground_truth_correct": False,
    },
    {
        "field_name": "patient_identifier",
        "raw_value": None,            # Missing entirely
        "ocr_word_confidences": [],
        "layout_region": "body",
        "document_type": "lab_report",
        "field_map": {"patient_identifier": None, "ordering_physician": None},
        "ground_truth_correct": False,
    },
    {
        "field_name": "vitals",
        "raw_value": "abc xyz",       # Garbage text, no valid vital format
        "ocr_word_confidences": [0.32, 0.28],
        "layout_region": "body",       # Wrong region (expected: table)
        "document_type": "lab_report",
        "field_map": {"patient_identifier": None, "ordering_physician": None},
        "ground_truth_correct": False,
    },
    {
        "field_name": "medications",
        "raw_value": None,            # Not extracted
        "ocr_word_confidences": [],
        "layout_region": "header",     # Wrong region
        "document_type": "prescription",
        "field_map": {"patient_identifier": None, "ordering_physician": None},
        "ground_truth_correct": False,
    },
    {
        "field_name": "ordering_physician",
        "raw_value": None,            # Missing
        "ocr_word_confidences": [],
        "layout_region": "body",       # Wrong region
        "document_type": "lab_report",
        "field_map": {"patient_identifier": None, "ordering_physician": None},
        "ground_truth_correct": False,
    },
    {
        "field_name": "diagnosis",
        "raw_value": "X",             # Too short (len <= 3)
        "ocr_word_confidences": [0.35],
        "layout_region": "header",     # Wrong region (expected: body)
        "document_type": "prescription",
        "field_map": {"patient_identifier": None, "ordering_physician": None},
        "ground_truth_correct": False,
    },
]
