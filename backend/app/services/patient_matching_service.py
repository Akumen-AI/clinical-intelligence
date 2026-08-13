import difflib
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.models.patient import Patient

logger = logging.getLogger("app.services.patient_matching_service")

NAME_SIMILARITY_THRESHOLD = 0.90


def match_patient(
    db: Session,
    name: Optional[str],
    dob: Optional[str],
    gender: Optional[str] = None
) -> Optional[str]:
    """
    Attempts to find a matching patient in the database using exact DOB matching
    and fuzzy name matching.

    Returns the patient_id if a confident match is found, otherwise None.
    """
    if not name:
        return None

    # Normalise name
    search_name = name.strip().lower()

    # Query patients. If DOB is provided, filter by it for efficiency and accuracy.
    query = db.query(Patient)
    if dob:
        # Standardise dob for comparison if possible, but exact match is safest for now
        query = query.filter(Patient.dob == dob.strip())
        
    candidates = query.all()
    
    # If no DOB was provided in extraction, candidates contains ALL patients. 
    # Be very careful matching just on name if it's a common name without DOB.
    # To be safe, if we don't have a DOB, we might require an even higher threshold
    # or reject matching to avoid merging different "John Smiths".
    # For now, we will allow it if similarity is very high.

    best_match_id = None
    highest_ratio = 0.0

    for patient in candidates:
        if not patient.name:
            continue
            
        patient_name = patient.name.strip().lower()
        
        # Calculate similarity
        matcher = difflib.SequenceMatcher(None, search_name, patient_name)
        ratio = matcher.ratio()
        
        if ratio > highest_ratio:
            highest_ratio = ratio
            best_match_id = patient.patient_id

    threshold = NAME_SIMILARITY_THRESHOLD
    # If no DOB was provided, enforce a stricter name match (e.g. 0.95 or exact)
    if not dob:
        threshold = 0.95

    if highest_ratio >= threshold:
        logger.info(f"[PatientMatching] Found fuzzy match: '{search_name}' matched '{best_match_id}' with ratio {highest_ratio:.2f}")
        return best_match_id

    logger.info(f"[PatientMatching] No match found for '{search_name}' (highest ratio: {highest_ratio:.2f})")
    return None
