import re
from copy import deepcopy
from typing import Any

from rapidfuzz import fuzz

from app.languages import is_validated_language
from app.schemas import NOT_STATED_SENTINEL

QUOTATION_LABELS: dict[str, str] = {
    "exact_quotation_found": "Exact quotation found",
    "possible_match": "Possible match: review required",
    "not_found": "Could not verify",
    "needs_user_verification": "Verify against your original document.",
}

QUOTATION_DISPLAY_LABELS = QUOTATION_LABELS

EXPERIMENTAL_CLAIM_NOTE = (
    "Automated deadline and mandatory-wording checks are not yet calibrated for this language. "
    "Please verify against the original quote."
)


class VerificationResult(dict):
    """Dictionary supporting both dot-attribute access (res.quotation_status) and dict unpacking."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


# Calibrated lexical cue dictionaries for Validated Tier languages ("en", "ta", "hi")
DEADLINE_CUES_BY_LANG: dict[str, tuple[str, ...]] = {
    "en": (
        "by",
        "before",
        "until",
        "due",
        "deadline",
        "no later than",
        "not later than",
        "within",
        "expires",
        "expiry",
        "expiration",
        "closing date",
        "last date",
        "on or before",
        "must be received",
        "must be submitted",
    ),
    "ta": (
        "முன்",
        "முன்பாக",
        "இறுதி நாள்",
        "இறுதித் தேதி",
        "கடைசி தேதி",
        "கடைசி நாள்",
        "காலக்கெடு",
        "உள்",
        "வரை",
        "காலாவதி",
    ),
    "hi": (
        "पहले",
        "पूर्व",
        "अंतिम तिथि",
        "आखिरी तारीख",
        "समय सीमा",
        "नियत तिथि",
        "तक",
        "भीतर",
        "अंदर",
        "समाप्ति",
    ),
}

MANDATORY_CUES_BY_LANG: dict[str, tuple[str, ...]] = {
    "en": (
        "must",
        "shall",
        "required",
        "mandatory",
        "obligatory",
        "need to",
        "needs to",
        "have to",
        "has to",
        "is to be",
        "are to be",
        "compulsory",
    ),
    "ta": (
        "வேண்டும்",
        "கட்டாயம்",
        "கட்டாயமாக",
        "அவசியம்",
        "சமர்ப்பிக்க வேண்டும்",
        "இணைக்க வேண்டும்",
        "வழங்க வேண்டும்",
    ),
    "hi": (
        "अनिवार्य",
        "आवश्यक",
        "बाध्यकारी",
        "जरूरी",
        "करना होगा",
        "करना अनिवार्य है",
        "जमा करना होगा",
    ),
}

OPTIONAL_OR_NEGATION_CUES_BY_LANG: dict[str, tuple[str, ...]] = {
    "en": (
        "may",
        "might",
        "could",
        "optional",
        "voluntary",
        "if applicable",
        "where applicable",
        "not required",
        "need not",
        "do not need",
        "does not need",
        "encouraged",
        "recommended",
        "at your discretion",
    ),
    "ta": (
        "விரும்பினால்",
        "விருப்பத்திற்குரிய",
        "தேவையில்லை",
        "அவசியமில்லை",
        "பொருந்தினால்",
        "பரிந்துரைக்கப்படுகிறது",
    ),
    "hi": (
        "वैकल्पिक",
        "यदि लागू हो",
        "आवश्यक नहीं",
        "जरूरी नहीं",
        "स्वेच्छा से",
        "सुझाव दिया जाता है",
    ),
}

_SMART_CHAR_MAP = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u00a0": " ",
    }
)

_CURRENCY_PREFIX_RE = re.compile(
    r"(?:rs\.?|inr|usd|eur|gbp|cad|aud|₹|\$|€|£)\s*",
    re.IGNORECASE,
)


def normalize_for_matching(text: str) -> str:
    if not text:
        return ""
    cleaned = text.translate(_SMART_CHAR_MAP)
    cleaned = re.sub(r"-\s*\r?\n\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


normalize_text = normalize_for_matching


def _normalize_lang_key(lang_code: str) -> str:
    return (lang_code or "").strip().lower().split("-")[0]


def _contains_cue(text_lower: str, cues: tuple[str, ...]) -> bool:
    for cue in cues:
        if cue.isascii():
            if re.search(rf"\b{re.escape(cue)}\b", text_lower):
                return True
        elif cue in text_lower:
            return True
    return False


def _coerce_pages_map(
    pages_input: dict[int, str] | list[dict[str, Any]] | None,
) -> tuple[dict[int, str], bool]:
    if not pages_input:
        return ({}, False)
    if isinstance(pages_input, dict):
        return ({int(k): str(v or "") for k, v in pages_input.items()}, False)
    pages_map: dict[int, str] = {}
    has_image = False
    for p in pages_input:
        p_num = int(p["page_number"])
        pages_map[p_num] = str(p.get("redacted_text", ""))
        if p.get("kind") == "image_based":
            has_image = True
    return (pages_map, has_image)


def verify_quotation_part_a(
    quote: str = "",
    pages_by_num: dict[int, str] | list[dict[str, Any]] | None = None,
    claimed_page: int | None = None,
    has_image_content: bool = False,
    *,
    evidence: str | None = None,
    pages: dict[int, str] | list[dict[str, Any]] | None = None,
    stated_page: int | None = None,
    is_scan_or_image: bool | None = None,
) -> VerificationResult:
    resolved_quote = evidence if evidence is not None else quote
    resolved_page = stated_page if stated_page is not None else claimed_page
    raw_pages_source = pages if pages is not None else pages_by_num
    pages_map, inferred_image = _coerce_pages_map(raw_pages_source)
    resolved_image = (
        is_scan_or_image if is_scan_or_image is not None else (has_image_content or inferred_image)
    )

    raw_quote = (resolved_quote or "").strip()
    non_empty_pages = {p: txt for p, txt in pages_map.items() if txt.strip()}

    if not non_empty_pages and resolved_image:
        return VerificationResult(
            quotation_status="needs_user_verification",
            quotation_label=QUOTATION_LABELS["needs_user_verification"],
            actual_page=None,
            page_corrected=False,
            page_note="Image or scanned input: verify directly against the document.",
            similarity_score=0.0,
        )

    if not raw_quote:
        return VerificationResult(
            quotation_status="not_found",
            quotation_label=QUOTATION_LABELS["not_found"],
            actual_page=None,
            page_corrected=False,
            page_note=None,
            similarity_score=0.0,
        )

    norm_quote = normalize_for_matching(raw_quote)
    if not norm_quote:
        return VerificationResult(
            quotation_status="not_found",
            quotation_label=QUOTATION_LABELS["not_found"],
            actual_page=None,
            page_corrected=False,
            page_note=None,
            similarity_score=0.0,
        )

    norm_pages = {p: normalize_for_matching(txt) for p, txt in non_empty_pages.items()}
    exact_pages = [p for p, norm_txt in norm_pages.items() if norm_quote in norm_txt]

    if exact_pages:
        if resolved_page is not None and resolved_page in exact_pages:
            actual_page = resolved_page
            page_corrected = False
            page_note = None
        else:
            actual_page = exact_pages[0]
            page_corrected = resolved_page is not None
            page_note = (
                f"Located on page {actual_page} (claimed page {resolved_page})."
                if page_corrected
                else None
            )

        return VerificationResult(
            quotation_status="exact_quotation_found",
            quotation_label=QUOTATION_LABELS["exact_quotation_found"],
            actual_page=actual_page,
            page_corrected=page_corrected,
            page_note=page_note,
            similarity_score=100.0,
        )

    best_score = 0.0
    best_page: int | None = None
    for p, norm_txt in norm_pages.items():
        if not norm_txt:
            continue
        score = float(fuzz.partial_ratio(norm_quote, norm_txt))
        if score > best_score:
            best_score = score
            best_page = p

    if best_score >= 85.0 and best_page is not None:
        page_corrected = resolved_page is not None and resolved_page != best_page
        page_note = (
            f"Possible match located on page {best_page} (claimed page {resolved_page})."
            if page_corrected
            else None
        )
        return VerificationResult(
            quotation_status="possible_match",
            quotation_label=QUOTATION_LABELS["possible_match"],
            actual_page=best_page,
            page_corrected=page_corrected,
            page_note=page_note,
            similarity_score=round(best_score, 2),
        )

    return VerificationResult(
        quotation_status="not_found",
        quotation_label=QUOTATION_LABELS["not_found"],
        actual_page=None,
        page_corrected=False,
        page_note=None,
        similarity_score=round(best_score, 2),
    )


verify_quotation = verify_quotation_part_a


def _resolve_part_a_status(
    part_a_status: str,
    part_a: dict[str, Any] | None,
) -> str:
    if part_a is not None:
        return str(part_a.get("quotation_status", part_a_status))
    return part_a_status


def verify_deadline_claim_part_b(
    date_text: str,
    evidence: str,
    part_a_status: str = "exact_quotation_found",
    lang: str = "en",
    *,
    ambiguous: bool = False,
    part_a: dict[str, Any] | None = None,
) -> VerificationResult:
    resolved_status = _resolve_part_a_status(part_a_status, part_a)

    if date_text.strip() in ("NO_DEADLINE", NOT_STATED_SENTINEL):
        return VerificationResult(
            quotation_status=resolved_status,
            quotation_label=QUOTATION_LABELS[resolved_status],
            claim_check="not_applicable",
            claim_note=None,
        )

    if resolved_status in ("not_found", "needs_user_verification"):
        return VerificationResult(
            quotation_status="needs_user_verification",
            quotation_label=QUOTATION_LABELS["needs_user_verification"],
            claim_check="not_applicable",
            claim_note=None,
        )

    norm_lang = _normalize_lang_key(lang)
    if not is_validated_language(norm_lang):
        return VerificationResult(
            quotation_status="needs_user_verification",
            quotation_label=QUOTATION_LABELS["needs_user_verification"],
            claim_check="not_applicable",
            claim_note=EXPERIMENTAL_CLAIM_NOTE,
        )

    norm_date = normalize_for_matching(date_text).lower()
    norm_ev = normalize_for_matching(evidence).lower()

    if not norm_date or norm_date not in norm_ev:
        note = "Quoted passage does not contain the exact stated date text."
        return VerificationResult(
            quotation_status="needs_user_verification",
            quotation_label=QUOTATION_LABELS["needs_user_verification"],
            claim_check="failed",
            claim_note=note,
        )

    cues = DEADLINE_CUES_BY_LANG.get(norm_lang, DEADLINE_CUES_BY_LANG["en"])
    if not _contains_cue(norm_ev, cues):
        note = "Date appears in the quote without clear deadline wording; verify whether this is a true deadline."
        return VerificationResult(
            quotation_status="needs_user_verification",
            quotation_label=QUOTATION_LABELS["needs_user_verification"],
            claim_check="failed",
            claim_note=note,
        )

    return VerificationResult(
        quotation_status=resolved_status,
        quotation_label=QUOTATION_LABELS[resolved_status],
        claim_check="passed",
        claim_note=None,
    )


verify_deadline_claim = verify_deadline_claim_part_b


def _normalize_amount_forms(amount: str) -> set[str]:
    norm = normalize_for_matching(amount).lower()
    forms = {norm}
    stripped = _CURRENCY_PREFIX_RE.sub("", norm).strip()
    if stripped:
        forms.add(stripped)
        forms.add(stripped.replace(",", ""))
        if stripped.endswith(".00"):
            forms.add(stripped[:-3])
            forms.add(stripped[:-3].replace(",", ""))
    return {f for f in forms if f}


def verify_fee_claim_part_b(
    amount: str,
    evidence: str,
    part_a_status: str = "exact_quotation_found",
    *,
    part_a: dict[str, Any] | None = None,
) -> VerificationResult:
    resolved_status = _resolve_part_a_status(part_a_status, part_a)

    if amount.strip() in ("NO_FEE", NOT_STATED_SENTINEL):
        return VerificationResult(
            quotation_status=resolved_status,
            quotation_label=QUOTATION_LABELS[resolved_status],
            claim_check="not_applicable",
            claim_note=None,
        )

    if resolved_status in ("not_found", "needs_user_verification"):
        return VerificationResult(
            quotation_status="needs_user_verification",
            quotation_label=QUOTATION_LABELS["needs_user_verification"],
            claim_check="not_applicable",
            claim_note=None,
        )

    norm_ev = normalize_for_matching(evidence).lower()
    norm_ev_no_commas = norm_ev.replace(",", "")
    candidate_forms = _normalize_amount_forms(amount)

    matched = any(
        (form in norm_ev or form in norm_ev_no_commas) for form in candidate_forms
    )
    if not matched:
        note = "Stated fee amount could not be confirmed verbatim inside the quoted passage."
        return VerificationResult(
            quotation_status="needs_user_verification",
            quotation_label=QUOTATION_LABELS["needs_user_verification"],
            claim_check="failed",
            claim_note=note,
        )

    return VerificationResult(
        quotation_status=resolved_status,
        quotation_label=QUOTATION_LABELS[resolved_status],
        claim_check="passed",
        claim_note=None,
    )


verify_fee_claim = verify_fee_claim_part_b


def _select_relevant_clause(evidence: str, requirement_item: str) -> str:
    sentences = [s.strip() for s in re.split(r"[.!?।]+", evidence) if s.strip()]
    if len(sentences) <= 1 or not requirement_item.strip():
        return evidence
    item_words = {
        w
        for w in re.findall(r"[a-zA-Z\u0900-\u097F\u0B80-\u0BFF]{3,}", requirement_item.lower())
        if w not in {"the", "and", "for", "with", "pay", "submit"}
    }
    if not item_words:
        return evidence
    best_sent = evidence
    best_overlap = 0
    for sent in sentences:
        sent_low = sent.lower()
        overlap = sum(1 for w in item_words if w in sent_low)
        if overlap > best_overlap:
            best_overlap = overlap
            best_sent = sent
    return best_sent if best_overlap > 0 else evidence


def verify_requirement_claim_part_b(
    status: str = "mandatory",
    evidence: str = "",
    part_a_status: str = "exact_quotation_found",
    lang: str = "en",
    *,
    requirement_item: str = "",
    declared_status: str | None = None,
    part_a: dict[str, Any] | None = None,
) -> VerificationResult:
    effective_status = declared_status if declared_status is not None else status
    resolved_status = _resolve_part_a_status(part_a_status, part_a)

    if resolved_status == "not_found":
        downgraded = "unclear" if effective_status == "mandatory" else effective_status
        return VerificationResult(
            status=downgraded,
            effective_status=downgraded,
            effective_requirement_status=downgraded,
            quotation_status="needs_user_verification",
            quotation_label=QUOTATION_LABELS["needs_user_verification"],
            claim_check="failed",
            claim_note="Quoted passage was not found in the document.",
        )

    if resolved_status == "needs_user_verification":
        return VerificationResult(
            status=effective_status,
            effective_status=effective_status,
            effective_requirement_status=effective_status,
            quotation_status="needs_user_verification",
            quotation_label=QUOTATION_LABELS["needs_user_verification"],
            claim_check="not_applicable",
            claim_note=None,
        )

    if effective_status != "mandatory":
        return VerificationResult(
            status=effective_status,
            effective_status=effective_status,
            effective_requirement_status=effective_status,
            quotation_status=resolved_status,
            quotation_label=QUOTATION_LABELS[resolved_status],
            claim_check="passed",
            claim_note=None,
        )

    norm_lang = _normalize_lang_key(lang)
    if not is_validated_language(norm_lang):
        return VerificationResult(
            status=effective_status,
            effective_status=effective_status,
            effective_requirement_status=effective_status,
            quotation_status="needs_user_verification",
            quotation_label=QUOTATION_LABELS["needs_user_verification"],
            claim_check="not_applicable",
            claim_note=EXPERIMENTAL_CLAIM_NOTE,
        )

    target_clause = _select_relevant_clause(evidence, requirement_item)
    norm_ev = normalize_for_matching(target_clause).lower()
    mandatory_cues = MANDATORY_CUES_BY_LANG.get(norm_lang, MANDATORY_CUES_BY_LANG["en"])
    optional_cues = OPTIONAL_OR_NEGATION_CUES_BY_LANG.get(
        norm_lang, OPTIONAL_OR_NEGATION_CUES_BY_LANG["en"]
    )

    has_mandatory = _contains_cue(norm_ev, mandatory_cues)
    has_optional_or_neg = _contains_cue(norm_ev, optional_cues)

    if has_optional_or_neg or not has_mandatory:
        note = "Quoted passage lacks unambiguous mandatory wording or contains conditional/optional terms."
        return VerificationResult(
            status="unclear",
            effective_status="unclear",
            effective_requirement_status="unclear",
            quotation_status="needs_user_verification",
            quotation_label=QUOTATION_LABELS["needs_user_verification"],
            claim_check="failed",
            claim_note=note,
        )

    return VerificationResult(
        status="mandatory",
        effective_status="mandatory",
        effective_requirement_status="mandatory",
        quotation_status=resolved_status,
        quotation_label=QUOTATION_LABELS[resolved_status],
        claim_check="passed",
        claim_note=None,
    )


verify_requirement_claim = verify_requirement_claim_part_b
verify_mandatory_requirement_claim_part_b = verify_requirement_claim_part_b


def _apply_part_a_only(
    item: dict[str, Any],
    quote_field: str,
    pages_by_num: dict[int, str],
    has_image_content: bool,
) -> dict[str, Any]:
    out = dict(item)
    for field in (
        "quotation_status",
        "quotation_label",
        "claim_check",
        "claim_note",
        "actual_page",
        "page_corrected",
        "page_note",
        "similarity_score",
    ):
        out.pop(field, None)

    quote_val = (out.get(quote_field) or "").strip()
    if not quote_val and out.get("value") == NOT_STATED_SENTINEL:
        non_empty_pages = {p: txt for p, txt in pages_by_num.items() if txt.strip()}
        status = (
            "needs_user_verification"
            if (not non_empty_pages and has_image_content)
            else "not_found"
        )
        out["quotation_status"] = status
        out["quotation_label"] = QUOTATION_LABELS[status]
        out["claim_check"] = "not_applicable"
        out["claim_note"] = None
        out["actual_page"] = None
        out["page_corrected"] = False
        out["page_note"] = None
        out["similarity_score"] = 0.0
        return out

    part_a = verify_quotation_part_a(
        quote=quote_val,
        pages_by_num=pages_by_num,
        claimed_page=out.get("page"),
        has_image_content=has_image_content,
    )
    out.update(part_a)
    out["claim_check"] = "not_applicable"
    out["claim_note"] = None
    return out


def verify_analysis_items(
    raw_analysis: dict[str, Any],
    redacted_pages: list[dict[str, Any]],
    has_image_content: bool = False,
    lang: str = "en",
) -> dict[str, Any]:
    """Run deterministic Part A and Part B verification across all extracted items."""
    verified = deepcopy(raw_analysis)
    pages_by_num: dict[int, str] = {
        int(p["page_number"]): str(p.get("redacted_text", ""))
        for p in redacted_pages
    }

    for meta_key in ("document_title", "issuing_authority", "document_type"):
        if meta_key in verified and isinstance(verified[meta_key], dict):
            verified[meta_key] = _apply_part_a_only(
                verified[meta_key], "evidence", pages_by_num, has_image_content
            )

    verified["simplified_passages"] = [
        _apply_part_a_only(item, "original", pages_by_num, has_image_content)
        for item in verified.get("simplified_passages", [])
    ]

    verified["action_steps"] = [
        _apply_part_a_only(item, "evidence", pages_by_num, has_image_content)
        for item in verified.get("action_steps", [])
    ]

    verified_deadlines: list[dict[str, Any]] = []
    for d in verified.get("deadlines", []):
        item = dict(d)
        part_a = verify_quotation_part_a(
            quote=item.get("evidence", ""),
            pages_by_num=pages_by_num,
            claimed_page=item.get("page"),
            has_image_content=has_image_content,
        )
        item.update(part_a)
        part_b = verify_deadline_claim_part_b(
            date_text=item.get("date_text", ""),
            evidence=item.get("evidence", ""),
            part_a_status=part_a["quotation_status"],
            lang=lang,
        )
        item["quotation_status"] = part_b["quotation_status"]
        item["quotation_label"] = part_b["quotation_label"]
        item["claim_check"] = part_b["claim_check"]
        item["claim_note"] = part_b["claim_note"]
        verified_deadlines.append(item)
    verified["deadlines"] = verified_deadlines

    verified_fees: list[dict[str, Any]] = []
    for f in verified.get("fees", []):
        item = dict(f)
        part_a = verify_quotation_part_a(
            quote=item.get("evidence", ""),
            pages_by_num=pages_by_num,
            claimed_page=item.get("page"),
            has_image_content=has_image_content,
        )
        item.update(part_a)
        part_b = verify_fee_claim_part_b(
            amount=item.get("amount", ""),
            evidence=item.get("evidence", ""),
            part_a_status=part_a["quotation_status"],
        )
        item["quotation_status"] = part_b["quotation_status"]
        item["quotation_label"] = part_b["quotation_label"]
        item["claim_check"] = part_b["claim_check"]
        item["claim_note"] = part_b["claim_note"]
        verified_fees.append(item)
    verified["fees"] = verified_fees

    verified_reqs: list[dict[str, Any]] = []
    for r in verified.get("requirements", []):
        item = dict(r)
        part_a = verify_quotation_part_a(
            quote=item.get("evidence", ""),
            pages_by_num=pages_by_num,
            claimed_page=item.get("page"),
            has_image_content=has_image_content,
        )
        item.update(part_a)
        part_b = verify_requirement_claim_part_b(
            status=item.get("status", "unclear"),
            evidence=item.get("evidence", ""),
            part_a_status=part_a["quotation_status"],
            lang=lang,
            requirement_item=item.get("item", ""),
        )
        item["status"] = part_b["status"]
        item["quotation_status"] = part_b["quotation_status"]
        item["quotation_label"] = part_b["quotation_label"]
        item["claim_check"] = part_b["claim_check"]
        item["claim_note"] = part_b["claim_note"]
        verified_reqs.append(item)
    verified["requirements"] = verified_reqs

    if has_image_content:
        verified["verification_limitation_note"] = (
            "Image or scanned input: automated quote verification was limited and requires direct user review."
        )
    elif not is_validated_language(lang):
        verified["verification_limitation_note"] = (
            "Civisterial can generate explanations in any language supported by Gemini. "
            "Full automated claim-checking is currently calibrated for English, Tamil, and Hindi; "
            "other languages show exact quote verification and require manual review of deadlines and mandatory terms."
        )
    else:
        verified["verification_limitation_note"] = (
            "Quotation checks verify whether the quoted text appears in your document. "
            "Always confirm meaning and official deadlines against your original document."
        )

    return verified


verify_document_analysis = verify_analysis_items