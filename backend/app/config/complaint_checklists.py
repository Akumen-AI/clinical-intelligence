# Each value is a list of human-readable field labels that should be
# documented for that complaint type. Labels are shown verbatim to clinicians.
# NEVER include diagnostic language — field labels must be documentation slots only.

COMPLAINT_CHECKLISTS: dict[str, list[str]] = {
    "respiratory": [
        "Onset date",
        "Duration",
        "Cough character",
        "Smoking history",
        "Occupational exposure",
        "Travel history (last 30 days)",
        "Known allergies",
        "Current medications",
        "Vaccination history",
    ],
    "gastrointestinal": [
        "Onset date",
        "Duration",
        "Last normal bowel movement",
        "Dietary history (last 48 h)",
        "Travel history (last 30 days)",
        "Known allergies",
        "Current medications",
        "Nausea / vomiting present",
    ],
    "cardiac": [
        "Onset date",
        "Duration",
        "Radiation pattern",
        "Associated symptoms",
        "Family history of cardiac events",
        "Current medications",
        "Known allergies",
        "Smoking history",
        "Exercise tolerance baseline",
    ],
    "neurological": [
        "Onset date",
        "Duration",
        "Laterality",
        "Loss of consciousness (Y/N)",
        "Seizure history",
        "Current medications",
        "Known allergies",
        "Recent head trauma",
        "Travel history (last 30 days)",
    ],
    "general": [
        "Onset date",
        "Duration",
        "Known allergies",
        "Current medications",
        "Travel history (last 30 days)",
    ],
}

# Banned phrases — any generated label or message containing these strings
# must be rejected before it leaves the service layer.
BANNED_PHRASES: list[str] = [
    "diagnosis", "diagnosed", "condition", "cause", "etiology",
    "pathology", "disease", "disorder", "syndrome", "infection",
    "treatment", "therapy", "prescribe", "recommend", "suggest",
    "likely", "probably", "possibly", "may indicate", "consistent with",
    "rule out", "differential", "icd", "snomed",
]
