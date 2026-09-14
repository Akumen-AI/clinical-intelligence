from app.config.complaint_checklists import COMPLAINT_CHECKLISTS, BANNED_PHRASES
from app.services.completeness_service import CompletenessService


def test_no_banned_phrases_in_checklists():
    """AC-3 guard: every checklist label must be free of banned phrases."""
    svc = CompletenessService(db=None)  # no DB needed for _validate_label
    for complaint_type, labels in COMPLAINT_CHECKLISTS.items():
        for label in labels:
            svc._validate_label(label)  # raises if banned phrase found
