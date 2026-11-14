from __future__ import annotations

import re
from dataclasses import dataclass

_PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3,4}\)?[\s.-]?)\d{3,4}[\s.-]?\d{3,4}"
)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9.\s]{2,30}\b(?:street|st\.?|road|rd\.?|avenue|ave\.?|lane|ln\.?|close|crescent|way|drive|dr\.?|boulevard|blvd\.?)\b",
    re.IGNORECASE,
)
_SELF_NAME_RE = re.compile(
    r"\b(?:my name is|i am called|i'm called|call me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})",
    re.IGNORECASE,
)


@dataclass
class ScrubResult:
    redacted_text: str
    redaction_count: int
    redacted_types: list[str]


def scrub_pii(text: str) -> ScrubResult:
    """Deterministically mask contact and identity PII while preserving community/school context."""
    redacted = text or ""
    count = 0
    types: list[str] = []

    def _sub(pattern: re.Pattern[str], label: str, current: str) -> str:
        nonlocal count
        matches = pattern.findall(current)
        if matches:
            count += len(matches)
            types.append(label)
            return pattern.sub(f"[REDACTED_{label}]", current)
        return current

    redacted = _sub(_EMAIL_RE, "EMAIL", redacted)
    redacted = _sub(_PHONE_RE, "PHONE", redacted)
    redacted = _sub(_ADDRESS_RE, "ADDRESS", redacted)

    def _name_repl(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        if "NAME" not in types:
            types.append("NAME")
        prefix = match.group(0)[: match.start(1) - match.start(0)]
        return f"{prefix}[REDACTED_NAME]"

    redacted = _SELF_NAME_RE.sub(_name_repl, redacted)
    return ScrubResult(redacted_text=redacted, redaction_count=count, redacted_types=types)


def contains_raw_pii(text: str) -> bool:
    """Verification check used by the eval harness to confirm 0 leaked PII."""
    if not text:
        return False
    return bool(_EMAIL_RE.search(text) or _PHONE_RE.search(text) or _ADDRESS_RE.search(text))

