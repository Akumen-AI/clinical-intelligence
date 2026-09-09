"""Deterministic, offline normalization for the demo terminology subset."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


MAPPING_SOURCE = "demo-subset"
MAPPING_VERSION = "v1"
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class MappingResult:
    code: str
    display_name: str
    vocabulary: str
    mapping_source: str = MAPPING_SOURCE
    mapping_version: str = MAPPING_VERSION
    matched_at: str = MAPPING_VERSION


def _normalize_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _load_lookup(filename: str) -> dict[str, tuple[str, str]]:
    with (_DATA_DIR / filename).open(encoding="utf-8") as handle:
        entries = json.load(handle)
    lookup = {}
    for entry in entries:
        for term in entry["terms"]:
            lookup[_normalize_text(term)] = (entry["code"], entry["display_name"])
    return lookup


# Loaded once when the service module is imported, rather than per request.
_RXNORM_LOOKUP = _load_lookup("rxnorm_subset_v1.json")
_ICD10_LOOKUP = _load_lookup("icd10_subset_v1.json")


def _normalize(raw_text: Any, lookup: dict[str, tuple[str, str]], vocabulary: str) -> Optional[MappingResult]:
    if raw_text is None:
        return None
    match = lookup.get(_normalize_text(raw_text))
    if match is None:
        return None
    code, display_name = match
    return MappingResult(code=code, display_name=display_name, vocabulary=vocabulary)


def normalize_medication(raw_text: Any) -> Optional[MappingResult]:
    return _normalize(raw_text, _RXNORM_LOOKUP, "RXNORM")


def normalize_diagnosis(raw_text: Any) -> Optional[MappingResult]:
    return _normalize(raw_text, _ICD10_LOOKUP, "ICD10")


def normalize_lab_result(raw_text: Any) -> Optional[MappingResult]:
    """LOINC hook reserved for a future versioned lab-result subset."""
    return None
