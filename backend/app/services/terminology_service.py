import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("app.services.terminology_service")

# Curated Synthetic Terminology Dictionary for Demo
# Keys are lowercase raw terms or synonyms.
# Values are dictionaries with the canonical 'mapped_code' and 'canonical_name'
SYNTHETIC_DICTIONARY = {
    "medications": {
        "metformin": {"mapped_code": "860975", "canonical_name": "Metformin", "version": "RxNorm 2024-05"},
        "metformin 500mg": {"mapped_code": "860975", "canonical_name": "Metformin 500mg", "version": "RxNorm 2024-05"},
        "glimepiride": {"mapped_code": "310340", "canonical_name": "Glimepiride", "version": "RxNorm 2024-05"},
        "glimepiride 2mg": {"mapped_code": "310340", "canonical_name": "Glimepiride 2mg", "version": "RxNorm 2024-05"},
        "lisinopril": {"mapped_code": "314076", "canonical_name": "Lisinopril", "version": "RxNorm 2024-05"},
        "lisinopril 10mg": {"mapped_code": "314076", "canonical_name": "Lisinopril 10mg", "version": "RxNorm 2024-05"},
        "amlodipine": {"mapped_code": "197361", "canonical_name": "Amlodipine", "version": "RxNorm 2024-05"},
        "amlodipine 5mg": {"mapped_code": "197361", "canonical_name": "Amlodipine 5mg", "version": "RxNorm 2024-05"},
        "albuterol": {"mapped_code": "745679", "canonical_name": "Albuterol", "version": "RxNorm 2024-05"},
        "albuterol inhaler": {"mapped_code": "745679", "canonical_name": "Albuterol inhaler", "version": "RxNorm 2024-05"},
        "fluticasone": {"mapped_code": "352362", "canonical_name": "Fluticasone", "version": "RxNorm 2024-05"},
        "fluticasone inhaler": {"mapped_code": "352362", "canonical_name": "Fluticasone inhaler", "version": "RxNorm 2024-05"},
        "oxycodone": {"mapped_code": "161", "canonical_name": "Oxycodone", "version": "RxNorm 2024-05"},
        "oxycodone 5mg": {"mapped_code": "161", "canonical_name": "Oxycodone 5mg", "version": "RxNorm 2024-05"},
        "naproxen": {"mapped_code": "748797", "canonical_name": "Naproxen", "version": "RxNorm 2024-05"},
        "naproxen 250mg": {"mapped_code": "748797", "canonical_name": "Naproxen 250mg", "version": "RxNorm 2024-05"},
        "furosemide": {"mapped_code": "315966", "canonical_name": "Furosemide", "version": "RxNorm 2024-05"},
        "furosemide 40mg": {"mapped_code": "315966", "canonical_name": "Furosemide 40mg", "version": "RxNorm 2024-05"},
        "lantus": {"mapped_code": "274783", "canonical_name": "Lantus", "version": "RxNorm 2024-05"},
        "tylenol": {"mapped_code": "161", "canonical_name": "Acetaminophen", "version": "RxNorm 2024-05"}, # Synonym test
    },
    "diagnoses": {
        "type 2 diabetes mellitus": {"mapped_code": "E11.9", "canonical_name": "Type 2 diabetes mellitus", "version": "ICD-10-CM 2024"},
        "type 2 diabetes": {"mapped_code": "E11.9", "canonical_name": "Type 2 diabetes mellitus", "version": "ICD-10-CM 2024"},
        "essential hypertension": {"mapped_code": "I10", "canonical_name": "Essential (primary) hypertension", "version": "ICD-10-CM 2024"},
        "asthma": {"mapped_code": "J45.909", "canonical_name": "Unspecified asthma, uncomplicated", "version": "ICD-10-CM 2024"},
        "chf": {"mapped_code": "I50.9", "canonical_name": "Heart failure, unspecified", "version": "ICD-10-CM 2024"},
        "ckd stage 3": {"mapped_code": "N18.3", "canonical_name": "Chronic kidney disease, stage 3 (moderate)", "version": "ICD-10-CM 2024"},
        "vitamin d deficiency": {"mapped_code": "E55.9", "canonical_name": "Vitamin D deficiency, unspecified", "version": "ICD-10-CM 2024"},
        "low back pain": {"mapped_code": "M54.5", "canonical_name": "Low back pain", "version": "ICD-10-CM 2024"},
        "pregnancy, unspecified": {"mapped_code": "Z33.1", "canonical_name": "Pregnant state, incidental", "version": "ICD-10-CM 2024"},
        "gerd": {"mapped_code": "K21.9", "canonical_name": "Gastro-esophageal reflux disease without esophagitis", "version": "ICD-10-CM 2024"},
        "peptic ulcer": {"mapped_code": "K27.9", "canonical_name": "Peptic ulcer, site unspecified, unspecified as acute or chronic, without hemorrhage or perforation", "version": "ICD-10-CM 2024"},
        "hypothyroidism": {"mapped_code": "E03.9", "canonical_name": "Hypothyroidism, unspecified", "version": "ICD-10-CM 2024"},
        "hypertension": {"mapped_code": "I10", "canonical_name": "Essential (primary) hypertension", "version": "ICD-10-CM 2024"},
        "pneumonia": {"mapped_code": "J18.9", "canonical_name": "Pneumonia, unspecified organism", "version": "ICD-10-CM 2024"},
        "covid-19": {"mapped_code": "U07.1", "canonical_name": "COVID-19", "version": "ICD-10-CM 2024"},
        "migraine": {"mapped_code": "G43.9", "canonical_name": "Migraine, unspecified", "version": "ICD-10-CM 2024"},
        "bone fracture": {"mapped_code": "S82.8", "canonical_name": "Fracture of other parts of lower leg", "version": "ICD-10-CM 2024"},
        "diabet": {"ambiguous": True}, # Test for ambiguous mappings
    },
    "lab_results": {
        "hba1c": {"mapped_code": "4548-4", "canonical_name": "Hemoglobin A1c/Hemoglobin.total in Blood", "version": "LOINC 2.77"},
        "creatinine": {"mapped_code": "2160-0", "canonical_name": "Creatinine [Mass/volume] in Serum or Plasma", "version": "LOINC 2.77"},
        "peak flow": {"mapped_code": "19935-6", "canonical_name": "Maximum expiratory gas flow Respiratory system airway by Peak flow meter", "version": "LOINC 2.77"},
        "egfr": {"mapped_code": "62238-1", "canonical_name": "Glomerular filtration rate/1.73 sq M.predicted", "version": "LOINC 2.77"},
        "heart rate": {"mapped_code": "8867-4", "canonical_name": "Heart rate", "version": "LOINC 2.77"},
    },
    "procedures": {
        "total knee arthroplasty, right": {"mapped_code": "0SRD0JZ", "canonical_name": "Replacement of Right Knee Joint with Synthetic Substitute", "version": "ICD-10-PCS 2024"},
    }
}

def normalize_clinical_term(entity_type: str, raw_text: str, extracted_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Normalizes a clinical term against the synthetic terminology dictionary.
    
    Args:
        entity_type: "medications", "diagnoses", "lab_results", or "procedures"
        raw_text: The raw text extracted from the document
        extracted_code: Any code the LLM originally suggested (used as fallback/validation)
        
    Returns:
        dict: A structured dictionary containing mapping metadata.
    """
    if not raw_text:
        return {
            "mapped_code": extracted_code,
            "mapping_status": "unmapped",
            "mapping_version": None,
            "mapping_confidence": 0.0,
            "mapping_provenance": "none"
        }
        
    domain_dict = SYNTHETIC_DICTIONARY.get(entity_type, {})
    term = raw_text.strip().lower()
    
    if term in domain_dict:
        entry = domain_dict[term]
        
        # Check for ambiguity
        if entry.get("ambiguous"):
            logger.warning(f"Ambiguous term detected: {raw_text}")
            return {
                "mapped_code": None, # Never invent a code for ambiguous terms
                "mapping_status": "ambiguous",
                "mapping_version": None,
                "mapping_confidence": 0.5,
                "mapping_provenance": "synthetic_demo_curation"
            }
            
        is_exact = (term == entry["canonical_name"].lower())
        return {
            "mapped_code": entry["mapped_code"],
            "mapping_status": "exact" if is_exact else "mapped",
            "mapping_version": entry.get("version"),
            "mapping_confidence": 1.0,
            "mapping_provenance": "synthetic_demo_curation"
        }
        
    # If not mapped in our dictionary, preserve the LLM extracted code if present but mark as unmapped/rejected
    # In a real system, we would ping an external API (UMLS, SNOMED, etc.)
    logger.info(f"Term not found in terminology dictionary: {raw_text}")
    return {
        "mapped_code": extracted_code, # Use the LLM's code if provided, but mark it unverified
        "mapping_status": "unmapped" if not extracted_code else "rejected", # If LLM gave a code but we can't verify it, we can call it rejected or unmapped
        "mapping_version": None,
        "mapping_confidence": 0.0,
        "mapping_provenance": "llm_extraction_only" if extracted_code else "none"
    }
