"""
AC-3 Compliance — Level-1 guardrail.
No output from Epic 5 or Epic 10 may contain diagnostic, condition,
or treatment language. This list is the permanent regression gate
referenced in FR-34.
"""

import re

BANNED_PHRASES: list[str] = [
    # Diagnostic language
    "diagnosis", "diagnosed", "diagnoses",
    "condition is", "presents with", "consistent with",
    "differential", "ddx", "rule out",
    "icd-", "icd10", "icd 10",
    # Treatment / prescription language
    "prescribe", "prescription", "recommend treatment",
    "treatment plan", "administer", "dosage",
    "medication recommendation", "suggest medication",
    "initiate therapy", "start therapy",
    # Causal / inferential language
    "cause of", "caused by", "etiology",
    "likely due to", "probably due to",
    "suggestive of", "indicative of",
    # Clinical conclusion language
    "patient has", "patient is suffering",
    "patient suffers from",
    "impression:", "assessment:",
    "plan:",  # only when followed by treatment nouns — checked via regex below
]

_PLAN_TREATMENT_RE = re.compile(
    r"plan\s*:\s*(prescri|medic|treat|therap|administer|dosage)",
    re.IGNORECASE,
)

def contains_banned_content(text: str) -> tuple[bool, str | None]:
    """
    Returns (True, matched_phrase) if any banned phrase found,
    (False, None) otherwise.
    Performs case-insensitive full-string scan.
    """
    lower = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lower:
            return True, phrase
    if _PLAN_TREATMENT_RE.search(text):
        return True, "plan: <treatment>"
    return False, None


class ComplianceViolationError(ValueError):
    """Raised when AC-3 banned content is detected in output."""
    def __init__(self, phrase: str):
        self.phrase = phrase
        super().__init__(f"AC-3 violation: banned phrase detected — '{phrase}'")


def enforce_ac3(text: str) -> str:
    """
    Call this on every string that will be returned to the frontend
    from Epic 5 or Epic 10. Raises ComplianceViolationError on match.
    Returns the text unchanged if compliant.
    """
    flagged, phrase = contains_banned_content(text)
    if flagged:
        raise ComplianceViolationError(phrase)
    return text
