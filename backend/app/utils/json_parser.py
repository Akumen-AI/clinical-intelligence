import ast
import json
import re
from typing import Any, Dict, List, Optional, Union


def clean_and_parse_json(text: str, default: Optional[Union[Dict, List]] = None) -> Union[Dict, List, Any]:
    """
    Robustly extract and parse JSON from LLM outputs.
    
    Handles:
    - Markdown code fences (```json ... ```)
    - Preamble / conversational text before/after JSON
    - Python literals (dict syntax with single quotes, None, True, False)
    - Trailing commas in arrays and objects
    - Unescaped raw newlines and tabs inside string literals
    - Missing commas between adjacent keys / array items on newlines
    - Truncated JSON responses (unclosed strings, brackets, and braces)
    - Key-by-key block extraction fallback for clinical schemas
    """
    if not text or not isinstance(text, str):
        if default is not None:
            return default
        return {}

    cleaned = text.strip()

    # 1. Strip markdown fences
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    # Fast path: try standard json.loads
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 2. Extract outermost JSON structure
    extracted = _extract_outermost_json(cleaned)
    if extracted:
        try:
            return json.loads(extracted)
        except Exception:
            cleaned = extracted

    # 3. Try ast.literal_eval (handles Python single-quoted dicts with None, True, False)
    try:
        val = ast.literal_eval(cleaned)
        if isinstance(val, (dict, list)):
            return val
    except Exception:
        pass

    # 4. Apply layered repairs
    repaired = _repair_json_string(cleaned)
    try:
        return json.loads(repaired)
    except Exception:
        pass

    # 5. Truncation repair (close unclosed brackets/braces)
    closed = _close_truncated_json(repaired)
    try:
        return json.loads(closed)
    except Exception:
        pass

    # 6. Key-by-key recovery for clinical document dictionaries
    key_extracted = _fallback_extract_clinical_keys(cleaned)
    if key_extracted:
        return key_extracted

    if default is not None:
        return default

    raise ValueError(f"Unable to parse JSON from response: {text[:200]}...")


def _extract_outermost_json(text: str) -> Optional[str]:
    """Find outermost {...} or [...] substring."""
    first_brace = text.find("{")
    first_bracket = text.find("[")

    if first_brace == -1 and first_bracket == -1:
        return None

    if first_bracket == -1 or (first_brace != -1 and first_brace < first_bracket):
        start_idx = first_brace
        end_idx = text.rfind("}")
    else:
        start_idx = first_bracket
        end_idx = text.rfind("]")

    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return text[start_idx : end_idx + 1]
    return None


def _repair_json_string(text: str) -> str:
    """Apply regex and string transformations to fix common LLM JSON syntax errors."""
    s = text

    # Remove trailing commas before } or ]
    s = re.sub(r",\s*([\]}])", r"\1", s)

    # Normalize Python literals
    s = re.sub(r"\bNone\b", "null", s)
    s = re.sub(r"\bTrue\b", "true", s)
    s = re.sub(r"\bFalse\b", "false", s)

    # Escape literal unescaped control characters inside quotes
    s = _escape_control_chars_in_strings(s)

    # Insert missing commas between lines where a property/item ends and another begins
    # e.g. "key1": "val1"\n"key2": "val2" -> "key1": "val1",\n"key2": "val2"
    s = re.sub(
        r'("(?:\\[\s\S]|[^"\\])*"|\b\d+(?:\.\d+)?\b|\btrue\b|\bfalse\b|\bnull\b|[}\]])\s*\n\s*("(?:\\[\s\S]|[^"\\])*"\s*:)',
        r"\1,\n\2",
        s,
    )

    # Insert missing commas between array items across lines
    # e.g. "item1"\n"item2" -> "item1",\n"item2"
    s = re.sub(
        r'("(?:\\[\s\S]|[^"\\])*"|\b\d+(?:\.\d+)?\b|\btrue\b|\bfalse\b|\bnull\b|[}\]])\s*\n\s*("(?:\\[\s\S]|[^"\\])*"|\[|\{)',
        r"\1,\n\2",
        s,
    )

    # Remove trailing commas again after regex substitutions
    s = re.sub(r",\s*([\]}])", r"\1", s)

    return s


def _escape_control_chars_in_strings(text: str) -> str:
    """Escape raw newlines and tabs inside quoted string literals."""
    result = []
    in_string = False
    escape = False

    for char in text:
        if char == '"' and not escape:
            in_string = not in_string
            result.append(char)
            escape = False
            continue

        if in_string:
            if escape:
                result.append(char)
                escape = False
            elif char == "\\":
                escape = True
                result.append(char)
            elif char == "\n":
                result.append("\\n")
            elif char == "\r":
                result.append("\\r")
            elif char == "\t":
                result.append("\\t")
            else:
                result.append(char)
        else:
            result.append(char)

    return "".join(result)


def _close_truncated_json(text: str) -> str:
    """Attempt to balance unclosed quotes, brackets, and braces in truncated JSON."""
    s = text.rstrip()
    open_stack = []
    in_string = False
    escape = False

    for char in s:
        if char == '"' and not escape:
            in_string = not in_string
            continue

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            continue

        if char in ("{", "["):
            open_stack.append(char)
        elif char == "}" and open_stack and open_stack[-1] == "{":
            open_stack.pop()
        elif char == "]" and open_stack and open_stack[-1] == "[":
            open_stack.pop()

    # If inside an open string, close it
    if in_string:
        s += '"'

    # Strip any trailing comma
    s = re.sub(r",\s*$", "", s.rstrip())

    # Close remaining brackets and braces in reverse order
    while open_stack:
        opener = open_stack.pop()
        if opener == "{":
            s += "}"
        elif opener == "[":
            s += "]"

    return s


def _fallback_extract_clinical_keys(text: str) -> Dict[str, Any]:
    """
    Fallback block extractor: independently extract known top-level clinical keys
    if the global JSON document has an unrecoverable syntax issue.
    """
    recovered: Dict[str, Any] = {}
    known_keys = [
        "transcribed_text",
        "fields",
        "patient_identifier",
        "document_date",
        "ordering_physician",
        "vitals",
        "diagnosis",
        "medications",
        "lab_results",
        "symptoms",
        "procedures",
    ]

    for key in known_keys:
        pattern = rf'"{key}"\s*:\s*([\{{\[][\s\S]*?[\}}\]]|"(?:\\.|[^"\\])*"|null|\d+|true|false)'
        match = re.search(pattern, text)
        if match:
            raw_val = match.group(1).strip()
            try:
                cleaned_val = _repair_json_string(raw_val)
                parsed_val = json.loads(cleaned_val)
                recovered[key] = parsed_val
            except Exception:
                if raw_val.startswith('"') and raw_val.endswith('"'):
                    recovered[key] = raw_val[1:-1]
                elif raw_val == "null":
                    recovered[key] = None

    return recovered
