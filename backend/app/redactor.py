import re
from dataclasses import dataclass, field
from typing import Any, Literal

RedactionStatus = Literal["redacted", "nothing_detected", "not_applicable_image_page"]

IMAGE_REDACTION_WARNING = "Personal details in images are not hidden before analysis."

# Verhoeff algorithm tables for 12-digit Aadhaar checksum validation
_VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)

_VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)

_VERHOEFF_INV = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)


def verhoeff_validate(num_str: str) -> bool:
    """Return True if num_str consists of digits and passes the Verhoeff checksum."""
    if not num_str.isdigit():
        return False
    c = 0
    for i, item in enumerate(reversed(num_str)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(item)]]
    return c == 0


def verhoeff_compute_check_digit(partial_digits: str) -> str:
    """Compute the Verhoeff check digit for a numeric string prefix."""
    c = 0
    for i, item in enumerate(reversed(partial_digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[(i + 1) % 8][int(item)]]
    return str(_VERHOEFF_INV[c])


_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# 12 digits starting 2-9, optionally separated into 4-4-4 groups by spaces or hyphens
_AADHAAR_CANDIDATE_RE = re.compile(
    r"(?<![A-Za-z0-9/-])\b([2-9]\d{3})([\s-]?)(\d{4})\2(\d{4})\b(?![A-Za-z0-9/-])"
)

# Indian PAN-like pattern: 5 uppercase letters + 4 digits + 1 uppercase letter
_PAN_RE = re.compile(
    r"(?<![A-Za-z0-9-])\b([A-Z]{5}\d{4}[A-Z])\b(?![A-Za-z0-9-])"
)

# Indian IFSC: 4 uppercase letters + '0' + 6 alphanumeric characters
_IFSC_RE = re.compile(
    r"(?<![A-Za-z0-9-])\b([A-Z]{4}0[A-Z0-9]{6})\b(?![A-Za-z0-9-])"
)

# Indian mobile/landline & international E.164-like phone numbers
_PHONE_RE = re.compile(
    r"(?<![A-Za-z0-9./-])"
    r"(?:"
    r"(?:\+91[\s.-]?|91[\s.-]?|0)?[6-9]\d{4}[\s.-]?\d{5}"
    r"|"
    r"\+(?!91\b)[1-9]\d{0,2}[\s.-]?\(?\d{1,4}\)?(?:[\s.-]?\d{2,5}){2,4}"
    r")"
    r"(?![A-Za-z0-9./-])"
)

# Bank account numbers: 9 to 18 digits (not preceded by '+') near banking keywords
_BANK_ACCOUNT_CANDIDATE_RE = re.compile(
    r"(?<![A-Za-z0-9./+-])\b(\d(?:[\s-]?\d){8,17})\b(?![A-Za-z0-9./-])"
)
_BANK_CONTEXT_RE = re.compile(
    r"\b(?:account|acct|a/c|a\.c\.|bank|ifsc|iban|savings|current\s+account|beneficiary|neft|rtgs|imps)\b",
    re.IGNORECASE,
)

# Context prefixes that denote administrative reference numbers, fees, or dates (do not redact)
_REF_PREFIX_RE = re.compile(
    r"(?:ref|reference|case\s*id|case|application|app|ticket|file|order\s*id|order|invoice|receipt|challan|notice|no\.|#)"
    r"[\s.:#-]*$",
    re.IGNORECASE,
)
_CURRENCY_PREFIX_RE = re.compile(r"(?:₹|rs\.?|inr|\$|£|€)\s*$", re.IGNORECASE)
_DATE_LIKE_RE = re.compile(
    r"^(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})$"
)


@dataclass
class _RequestRedactionSession:
    """Ephemeral per-request mapping ensuring identical values receive identical placeholders."""

    value_to_placeholder: dict[tuple[str, str], str] = field(default_factory=dict)
    type_counters: dict[str, int] = field(default_factory=dict)

    def placeholder_for(self, entity_type: str, canonical_key: str) -> str:
        lookup = (entity_type, canonical_key)
        existing = self.value_to_placeholder.get(lookup)
        if existing is not None:
            return existing
        next_idx = self.type_counters.get(entity_type, 0) + 1
        self.type_counters[entity_type] = next_idx
        token = f"[{entity_type}_{next_idx}]"
        self.value_to_placeholder[lookup] = token
        return token

    def clear(self) -> None:
        self.value_to_placeholder.clear()
        self.type_counters.clear()


def _is_protected_context(text: str, start: int, matched_str: str) -> bool:
    """Return True if the span looks like an essential date, fee, or reference number."""
    if _DATE_LIKE_RE.match(matched_str.strip()):
        return True
    prefix_window = text[max(0, start - 24) : start]
    if _CURRENCY_PREFIX_RE.search(prefix_window):
        return True
    if _REF_PREFIX_RE.search(prefix_window):
        return True
    return False


def _redact_single_page_text(
    text: str,
    session: _RequestRedactionSession,
) -> tuple[str, dict[str, int]]:
    """Redact supported PII types in one text page and return (redacted_text, counts_by_type)."""
    counts: dict[str, int] = {}

    def record(entity_type: str, canonical_key: str) -> str:
        counts[entity_type] = counts.get(entity_type, 0) + 1
        return session.placeholder_for(entity_type, canonical_key)

    # 1. Email addresses
    def repl_email(m: re.Match[str]) -> str:
        raw = m.group(0)
        return record("EMAIL", raw.lower())

    working = _EMAIL_RE.sub(repl_email, text)

    # 2. Aadhaar-like 12-digit numbers with Verhoeff checksum validation
    def repl_aadhaar(m: re.Match[str]) -> str:
        raw = m.group(0)
        if _is_protected_context(working, m.start(), raw):
            return raw
        digits_only = re.sub(r"\D", "", raw)
        if len(digits_only) != 12 or not verhoeff_validate(digits_only):
            return raw
        return record("AADHAAR", digits_only)

    working = _AADHAAR_CANDIDATE_RE.sub(repl_aadhaar, working)

    # 3. PAN-like identifiers
    def repl_pan(m: re.Match[str]) -> str:
        raw = m.group(1)
        if _is_protected_context(working, m.start(), raw):
            return raw
        return record("PAN", raw.upper())

    working = _PAN_RE.sub(repl_pan, working)

    # 4. IFSC codes
    def repl_ifsc(m: re.Match[str]) -> str:
        raw = m.group(1)
        return record("IFSC", raw.upper())

    working = _IFSC_RE.sub(repl_ifsc, working)

    # 5. Indian and international phone numbers (before bank accounts so +intl phones aren't split)
    def repl_phone(m: re.Match[str]) -> str:
        raw = m.group(0)
        if _is_protected_context(working, m.start(), raw):
            return raw
        digits_only = re.sub(r"\D", "", raw)
        if len(digits_only) < 10 or len(digits_only) > 15:
            return raw
        if len(digits_only) == 12 and digits_only.startswith("91"):
            canonical = digits_only[2:]
        elif len(digits_only) == 11 and digits_only.startswith("0"):
            canonical = digits_only[1:]
        else:
            canonical = digits_only
        return record("PHONE", canonical)

    working = _PHONE_RE.sub(repl_phone, working)

    # 6. Bank account numbers (9-18 digits near banking keywords, excluding ref/fee/date contexts)
    def repl_bank_account(m: re.Match[str]) -> str:
        raw = m.group(1)
        if _is_protected_context(working, m.start(), raw):
            return raw
        digits_only = re.sub(r"\D", "", raw)
        if not (9 <= len(digits_only) <= 18):
            return raw
        window_start = max(0, m.start() - 45)
        window_end = min(len(working), m.end() + 45)
        context_slice = working[window_start:window_end]
        if not _BANK_CONTEXT_RE.search(context_slice):
            return raw
        return record("BANK_ACCOUNT", digits_only)

    working = _BANK_ACCOUNT_CANDIDATE_RE.sub(repl_bank_account, working)

    return working, counts


def redact_extracted_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply conservative PII redaction across extracted pages in a single request session."""
    session = _RequestRedactionSession()
    redacted_pages: list[dict[str, Any]] = []

    try:
        for page in pages:
            kind = page.get("kind", "empty")
            raw_text = page.get("text") or ""

            if kind != "text" or not raw_text.strip():
                existing_notice = page.get("notice")
                combined_notice = (
                    f"{IMAGE_REDACTION_WARNING} {existing_notice}".strip()
                    if existing_notice
                    else IMAGE_REDACTION_WARNING
                )
                redacted_pages.append(
                    {
                        "page_number": page["page_number"],
                        "kind": kind,
                        "char_count": 0,
                        "text": "",
                        "redacted_text": "",
                        "redaction_status": "not_applicable_image_page",
                        "redaction_applied": False,
                        "redaction_counts": {},
                        "notice": combined_notice,
                    }
                )
                continue

            masked_text, counts = _redact_single_page_text(raw_text, session)
            has_redactions = sum(counts.values()) > 0
            status: RedactionStatus = "redacted" if has_redactions else "nothing_detected"

            redacted_pages.append(
                {
                    "page_number": page["page_number"],
                    "kind": "text",
                    "char_count": len(masked_text),
                    "text": masked_text,
                    "redacted_text": masked_text,
                    "redaction_status": status,
                    "redaction_applied": True,
                    "redaction_counts": counts,
                    "notice": page.get("notice"),
                }
            )

        return redacted_pages
    finally:
        session.clear()


def build_gemini_input_payload(redacted_pages: list[dict[str, Any]]) -> str:
    """Assemble strictly redacted text pages for downstream AI analysis."""
    sections: list[str] = []
    for page in redacted_pages:
        if page.get("kind") == "text" and page.get("redaction_applied") is True:
            sections.append(f"--- Page {page['page_number']} ---\n{page['redacted_text']}")
    return "\n\n".join(sections)