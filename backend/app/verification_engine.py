"""Deterministic two-part verification engine for Civisterial.

Honest Limitation Notice:
- Part A checks only whether a normalized quotation exists in the redacted text of the uploaded
  document. It never verifies external truth or official authenticity.
- Part B catches only simple lexical and structural mismatches (missing deadline cues, mismatched
  currency amounts, or clause-level optional/negated wording on mandatory requirements). Passing
  Part B is NOT proof that an interpretation is legally or administratively correct.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Literal

from rapidfuzz import fuzz

QuotationStatus = Literal[
    "exact_quotation_found",
    "possible_match",
    "not_found",
    "needs_user_verification",
]

ClaimCheckStatus = Literal[
    "passed",
    "failed",
    "needs_user_verification",
    "not_applicable",
]

QUOTATION_DISPLAY_LABELS: dict[QuotationStatus, str] = {
    "exact_quotation_found": "Exact quotation found",
    "possible_match": "Possible match: review required",
    "not_found": "Could not verify",
    "needs_user_verification": "Verify against your original document.",
}

PART_B_LIMITATION_NOTE = (
    "Automated checks catch only simple text mismatches and cannot prove an interpretation is "
    "correct. Review all details against your original document."
)

# Configurable per-language lexical cues for Part B
DEADLINE_CUES_BY_LANG: dict[str, tuple[str, ...]] = {
    "en": (
        "by",
        "before",
        "no later than",
        "not later than",
        "on or before",
        "last date",
        "due date",
        "deadline",
        "within",
        "expires on",
        "valid until",
        "submit by",
    ),
}

MANDATORY_CUES_BY_LANG: dict[str, tuple[str, ...]] = {
    "en": (
        "must",
        "shall",
        "required",
        "mandatory",
        "compulsory",
        "obligatory",
        "is required to",
        "are required to",
    ),
}

OPTIONAL_OR_NEGATION_CUES_BY_LANG: dict[str, tuple[str, ...]] = {
    "en": (
        "may",
        "optional",
        "optionally",
        "voluntary",
        "not required",
        "need not",
        "no need to",
        "exempt",
        "exemption",
        "unless",
        "except",
        "at your discretion",
        "if applicable",
    ),
}

_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "of",
        "to",
        "for",
        "in",
        "on",
        "at",
        "and",
        "or",
        "is",
        "are",
        "be",
        "with",
        "by",
        "that",
        "this",
        "their",
        "your",
        "applicant",
        "applicants",
    }
)


@dataclass
class VerificationResult:
    quotation_status: QuotationStatus
    quotation_label: str
    claim_check: ClaimCheckStatus
    claim_note: str | None = None
    actual_page: int | None = None
    page_corrected: bool = False
    page_note: str | None = None
    similarity_score: float = 0.0
    effective_requirement_status: Literal["mandatory", "optional", "unclear"] | None = None


def normalize_text(text: str) -> str:
    """Normalize text for deterministic comparison:
    - Unicode NFKC normalization
    - Smart quotes/apostrophes & dashes normalized to ASCII equivalents
    - Hyphenation line breaks joined (e.g., 'appli-\\ncation' -> 'application')
    - Lowercased and whitespace collapsed to single spaces
    """
    if not text:
        return ""

    # 1. Unicode NFKC
    norm = unicodedata.normalize("NFKC", text)

    # 2. Smart quotes and typographic dashes
    quote_map = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u201f": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u00a0": " ",
    }
    for src, dst in quote_map.items():
        norm = norm.replace(src, dst)

    # 3. Remove hyphenation across line breaks: word-\nword -> wordword
    norm = re.sub(r"([A-Za-z0-9])-\s*[\r\n]+\s*([A-Za-z0-9])", r"\1\2", norm)

    # 4. Lowercase and collapse all whitespace
    norm = norm.lower()
    norm = re.sub(r"\s+", " ", norm).strip()
    return norm


def normalize_currency_tokens(text: str) -> str:
    """Normalize common currency representations for fee matching only (never for display).

    Examples: '₹500', 'Rs. 500', 'Rs 500/-', 'INR 500.00' -> 'inr 500'
    """
    norm = normalize_text(text)
    # Remove trailing '/-' common in Indian fee notices
    norm = re.sub(r"/-", "", norm)
    # Remove thousand separators inside numbers: 1,500 -> 1500
    norm = re.sub(r"(?<=\d),(?=\d{3}\b)", "", norm)
    # Strip trailing .00 on whole numbers: 500.00 -> 500
    norm = re.sub(r"\b(\d+)\.00\b", r"\1", norm)
    # Normalize Indian Rupee variants (₹, rs., rs, inr) -> 'inr '
    norm = re.sub(r"(?:₹|rs\.?|inr)\s*(?=\d)", "inr ", norm)
    # Normalize USD/GBP/EUR symbols adjacent to numbers
    norm = re.sub(r"\$\s*(?=\d)", "usd ", norm)
    norm = re.sub(r"£\s*(?=\d)", "gbp ", norm)
    norm = re.sub(r"€\s*(?=\d)", "eur ", norm)
    norm = re.sub(r"\s+", " ", norm).strip()
    return norm


def _best_window_similarity(norm_quote: str, norm_haystack: str) -> float:
    """Compute rapidfuzz similarity against the best-matching window of norm_haystack."""
    if not norm_quote or not norm_haystack:
        return 0.0
    if norm_quote in norm_haystack:
        return 100.0
    # partial_ratio finds the highest-scoring aligned window; ratio compares overall length
    # Using partial_ratio with length guard prevents tiny fragments from scoring high artificially
    if len(norm_haystack) < max(1, int(len(norm_quote) * 0.5)):
        return float(fuzz.ratio(norm_quote, norm_haystack))
    return float(fuzz.partial_ratio(norm_quote, norm_haystack))


def verify_quotation_part_a(
    evidence: str,
    stated_page: int | None,
    pages: list[dict[str, Any]],
    *,
    is_scan_or_image: bool = False,
    ambiguous_or_unclear: bool = False,
    uncertain_page: bool = False,
) -> VerificationResult:
    """PART A: Deterministic quotation check against redacted per-page text in memory."""
    norm_quote = normalize_text(evidence)

    # Empty or whitespace-only quote cannot match
    if not norm_quote:
        status: QuotationStatus = (
            "needs_user_verification"
            if (is_scan_or_image or ambiguous_or_unclear or uncertain_page)
            else "not_found"
        )
        return VerificationResult(
            quotation_status=status,
            quotation_label=QUOTATION_DISPLAY_LABELS[status],
            claim_check="not_applicable",
            similarity_score=0.0,
        )

    text_pages: dict[int, str] = {}
    for p in pages:
        if p.get("kind") == "text" and p.get("redaction_applied") is True:
            text_pages[int(p["page_number"])] = normalize_text(p.get("redacted_text") or "")

    whole_doc_norm = "\n".join(text_pages.values())

    # If the input is a scan/image or no text layer exists at all, always require user verification
    if is_scan_or_image or not text_pages:
        return VerificationResult(
            quotation_status="needs_user_verification",
            quotation_label=QUOTATION_DISPLAY_LABELS["needs_user_verification"],
            claim_check="not_applicable",
            actual_page=stated_page,
            page_note="Source is an image or scan; verify directly against your original document.",
            similarity_score=0.0,
        )

    # 1. Exact substring check on stated page (or whole document when page is null)
    if stated_page is not None:
        stated_haystack = text_pages.get(stated_page, "")
        if stated_haystack and norm_quote in stated_haystack:
            final_status: QuotationStatus = (
                "needs_user_verification"
                if (ambiguous_or_unclear or uncertain_page)
                else "exact_quotation_found"
            )
            return VerificationResult(
                quotation_status=final_status,
                quotation_label=QUOTATION_DISPLAY_LABELS[final_status],
                claim_check="not_applicable",
                actual_page=stated_page,
                page_corrected=False,
                similarity_score=100.0,
            )

        # Wrong-page search: check if the exact quote exists on another text page
        for p_num, p_text in sorted(text_pages.items()):
            if p_num != stated_page and p_text and norm_quote in p_text:
                final_status = (
                    "needs_user_verification"
                    if (ambiguous_or_unclear or uncertain_page)
                    else "exact_quotation_found"
                )
                return VerificationResult(
                    quotation_status=final_status,
                    quotation_label=QUOTATION_DISPLAY_LABELS[final_status],
                    claim_check="not_applicable",
                    actual_page=p_num,
                    page_corrected=True,
                    page_note=(
                        f"Quote found on page {p_num} instead of page {stated_page}; "
                        "page reference was not validated."
                    ),
                    similarity_score=100.0,
                )
    else:
        # stated_page is None -> check whole document
        if whole_doc_norm and norm_quote in whole_doc_norm:
            matched_pages = [p_num for p_num, p_text in sorted(text_pages.items()) if norm_quote in p_text]
            resolved_page = matched_pages[0] if len(matched_pages) == 1 else None
            final_status = (
                "needs_user_verification"
                if (ambiguous_or_unclear or uncertain_page)
                else "exact_quotation_found"
            )
            return VerificationResult(
                quotation_status=final_status,
                quotation_label=QUOTATION_DISPLAY_LABELS[final_status],
                claim_check="not_applicable",
                actual_page=resolved_page,
                page_corrected=False,
                similarity_score=100.0,
            )

    # 2. Fuzzy similarity check via rapidfuzz (threshold >= 85 -> possible_match, NEVER exact_quotation_found)
    best_score = 0.0
    best_page: int | None = None
    for p_num, p_text in sorted(text_pages.items()):
        score = _best_window_similarity(norm_quote, p_text)
        if score > best_score:
            best_score = score
            best_page = p_num

    if best_score >= 85.0:
        # Even if fuzzy similarity reaches 100.0 (e.g., punctuation/reordering), NEVER upgrade to exact_quotation_found
        status_fuzzy: QuotationStatus = (
            "needs_user_verification"
            if (ambiguous_or_unclear or uncertain_page)
            else "possible_match"
        )
        page_was_wrong = stated_page is not None and best_page is not None and best_page != stated_page
        return VerificationResult(
            quotation_status=status_fuzzy,
            quotation_label=QUOTATION_DISPLAY_LABELS[status_fuzzy],
            claim_check="not_applicable",
            actual_page=best_page,
            page_corrected=page_was_wrong,
            page_note=(
                f"Closest text match appears on page {best_page} (not page {stated_page})."
                if page_was_wrong
                else None
            ),
            similarity_score=round(best_score, 2),
        )

    return VerificationResult(
        quotation_status="not_found",
        quotation_label=QUOTATION_DISPLAY_LABELS["not_found"],
        claim_check="not_applicable",
        actual_page=None,
        page_corrected=False,
        similarity_score=round(best_score, 2),
    )


def _split_clauses(norm_quote: str) -> list[str]:
    """Split a normalized quotation into sentences and semi-colon/independent clauses."""
    parts = re.split(r"(?<=[.!?;])\s+|\s+(?:however|whereas|provided that)\s+", norm_quote)
    return [p.strip() for p in parts if p.strip()]


def _content_tokens(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-z0-9_-]{3,}", normalize_text(text)))
    return tokens - _STOPWORDS


def verify_deadline_claim_part_b(
    *,
    date_text: str,
    ambiguous: bool,
    evidence: str,
    part_a: VerificationResult,
    lang: str = "en",
) -> VerificationResult:
    """PART B (Deadline): date_text must appear in normalized quote AND quote must have a deadline cue."""
    if part_a.quotation_status != "exact_quotation_found":
        part_a.quotation_status = "needs_user_verification"
        part_a.quotation_label = QUOTATION_DISPLAY_LABELS["needs_user_verification"]
        part_a.claim_check = "failed" if part_a.quotation_status == "not_found" else "needs_user_verification"
        part_a.claim_note = (
            "Deadline cannot be confirmed because an exact quotation was not established. "
            "Verify against your original document."
        )
        return part_a

    if ambiguous:
        part_a.quotation_status = "needs_user_verification"
        part_a.quotation_label = QUOTATION_DISPLAY_LABELS["needs_user_verification"]
        part_a.claim_check = "needs_user_verification"
        part_a.claim_note = "Date wording is ambiguous. Verify against your original document."
        return part_a

    norm_quote = normalize_text(evidence)
    norm_date = normalize_text(date_text)
    cues = DEADLINE_CUES_BY_LANG.get(lang, DEADLINE_CUES_BY_LANG["en"])

    date_present = bool(norm_date) and (norm_date in norm_quote)
    cue_present = any(
        re.search(rf"\b{re.escape(cue)}\b", norm_quote) is not None for cue in cues
    )

    if date_present and cue_present:
        part_a.claim_check = "passed"
        part_a.claim_note = (
            "Date and deadline wording appear in the exact quote; confirm applicability in your original document."
        )
        return part_a

    part_a.claim_check = "failed"
    part_a.quotation_status = "needs_user_verification"
    part_a.quotation_label = QUOTATION_DISPLAY_LABELS["needs_user_verification"]
    if not date_present:
        part_a.claim_note = (
            "Stated date text was not found verbatim in the supporting quotation. "
            "Verify against your original document."
        )
    else:
        part_a.claim_note = (
            "Quote mentions a date without clear deadline wording (such as 'by' or 'before'). "
            "Verify against your original document."
        )
    return part_a


def verify_fee_claim_part_b(
    *,
    amount: str,
    evidence: str,
    part_a: VerificationResult,
) -> VerificationResult:
    """PART B (Fee): currency-normalized amount must appear in the exact quote."""
    if part_a.quotation_status != "exact_quotation_found":
        part_a.quotation_status = "needs_user_verification"
        part_a.quotation_label = QUOTATION_DISPLAY_LABELS["needs_user_verification"]
        part_a.claim_check = "failed"
        part_a.claim_note = (
            "Fee amount cannot be confirmed without an exact supporting quotation. "
            "Verify against your original document."
        )
        return part_a

    norm_amount = normalize_currency_tokens(amount)
    norm_quote = normalize_currency_tokens(evidence)

    if norm_amount and re.search(rf"(?<![a-z0-9]){re.escape(norm_amount)}(?![a-z0-9])", norm_quote):
        part_a.claim_check = "passed"
        part_a.claim_note = (
            "Fee amount matches the exact quote; confirm whether exemptions or conditions apply."
        )
        return part_a

    part_a.claim_check = "failed"
    part_a.quotation_status = "needs_user_verification"
    part_a.quotation_label = QUOTATION_DISPLAY_LABELS["needs_user_verification"]
    part_a.claim_note = (
        "Stated fee amount was not found in the supporting quotation. "
        "Verify against your original document."
    )
    return part_a


def verify_mandatory_requirement_claim_part_b(
    *,
    requirement_item: str,
    declared_status: Literal["mandatory", "optional", "unclear"],
    evidence: str,
    part_a: VerificationResult,
    lang: str = "en",
) -> VerificationResult:
    """PART B (Mandatory Requirement):
    - Only applies when declared_status == 'mandatory' (otherwise claim_check='not_applicable').
    - Mandatory wording must appear in the SAME clause/sentence that describes this specific
      requirement, without negation, exception, or optional modals ('may', 'optional', etc.).
    - If relationship is unclear or optional wording applies, returns needs_user_verification
      and downgrades effective_requirement_status to 'unclear' (never 'mandatory').
    """
    if declared_status != "mandatory":
        part_a.claim_check = "not_applicable"
        part_a.effective_requirement_status = declared_status
        if declared_status == "unclear":
            part_a.quotation_status = "needs_user_verification"
            part_a.quotation_label = QUOTATION_DISPLAY_LABELS["needs_user_verification"]
        return part_a

    if part_a.quotation_status != "exact_quotation_found":
        part_a.quotation_status = "needs_user_verification"
        part_a.quotation_label = QUOTATION_DISPLAY_LABELS["needs_user_verification"]
        part_a.claim_check = "failed"
        part_a.effective_requirement_status = "unclear"
        part_a.claim_note = (
            "Mandatory status cannot be confirmed without an exact quotation. "
            "Verify against your original document."
        )
        return part_a

    norm_quote = normalize_text(evidence)
    clauses = _split_clauses(norm_quote)
    item_tokens = _content_tokens(requirement_item)

    mandatory_cues = MANDATORY_CUES_BY_LANG.get(lang, MANDATORY_CUES_BY_LANG["en"])
    opt_neg_cues = OPTIONAL_OR_NEGATION_CUES_BY_LANG.get(
        lang, OPTIONAL_OR_NEGATION_CUES_BY_LANG["en"]
    )

    # Identify clauses that actually refer to this specific requirement item
    matching_clauses: list[str] = []
    if item_tokens:
        scored: list[tuple[int, str]] = []
        for clause in clauses:
            overlap = len(item_tokens & _content_tokens(clause))
            if overlap > 0:
                scored.append((overlap, clause))
        if scored:
            max_overlap = max(s[0] for s in scored)
            matching_clauses = [c for ov, c in scored if ov == max_overlap]
    else:
        matching_clauses = clauses

    if not matching_clauses:
        part_a.claim_check = "needs_user_verification"
        part_a.quotation_status = "needs_user_verification"
        part_a.quotation_label = QUOTATION_DISPLAY_LABELS["needs_user_verification"]
        part_a.effective_requirement_status = "unclear"
        part_a.claim_note = (
            "Could not link mandatory wording in the quote directly to this requirement. "
            "Verify against your original document."
        )
        return part_a

    # Inspect the target clause(s) for optional/negation cues vs mandatory cues
    target_text = " ".join(matching_clauses)
    has_optional_or_negation = any(
        re.search(rf"\b{re.escape(cue)}\b", target_text) is not None for cue in opt_neg_cues
    )
    has_mandatory = any(
        re.search(rf"\b{re.escape(cue)}\b", target_text) is not None for cue in mandatory_cues
    )

    if has_optional_or_negation or not has_mandatory:
        part_a.claim_check = "failed"
        part_a.quotation_status = "needs_user_verification"
        part_a.quotation_label = QUOTATION_DISPLAY_LABELS["needs_user_verification"]
        part_a.effective_requirement_status = "unclear"
        part_a.claim_note = (
            "Supporting clause uses optional, conditional, or non-mandatory wording. "
            "Shown as unclear—verify against your original document."
        )
        return part_a

    part_a.claim_check = "passed"
    part_a.effective_requirement_status = "mandatory"
    part_a.claim_note = (
        "Mandatory wording appears in the matching clause; automated checks cannot prove legal "
        "interpretation—verify against your original document."
    )
    return part_a


def verify_analysis_items(
    analysis_dict: dict[str, Any],
    redacted_pages: list[dict[str, Any]],
    *,
    has_image_content: bool = False,
    lang: str = "en",
) -> dict[str, Any]:
    """Run Part A and Part B across all structured items in a GeminiDocumentAnalysis payload.

    - Runs strictly against in-memory redacted_pages (never restores PII placeholders).
    - Overwrites/populates quotation_status and claim_check exclusively in code; any AI-supplied
      status fields are ignored/stripped.
    """
    is_scan_only = has_image_content and not any(
        p.get("kind") == "text" and p.get("redaction_applied") is True for p in redacted_pages
    )

    def _apply_part_a_dict(
        evidence: str,
        page: int | None,
        *,
        ambiguous_or_unclear: bool = False,
    ) -> VerificationResult:
        # If document has mixed image + text pages and page is None or points to an image page, treat as scan/uncertain
        page_is_image = False
        if page is not None:
            for p in redacted_pages:
                if int(p["page_number"]) == int(page) and p.get("kind") != "text":
                    page_is_image = True
                    break
        elif has_image_content:
            page_is_image = True

        return verify_quotation_part_a(
            evidence=evidence,
            stated_page=page,
            pages=redacted_pages,
            is_scan_or_image=is_scan_only or page_is_image,
            ambiguous_or_unclear=ambiguous_or_unclear,
            uncertain_page=False,
        )

    def _attach_result(target: dict[str, Any], vr: VerificationResult) -> dict[str, Any]:
        # Strip any AI-injected verification fields before writing deterministic results
        cleaned = {
            k: v
            for k, v in target.items()
            if k
            not in (
                "quotation_status",
                "quotation_label",
                "claim_check",
                "claim_note",
                "actual_page",
                "page_corrected",
                "page_note",
                "similarity_score",
            )
        }
        cleaned["quotation_status"] = vr.quotation_status
        cleaned["quotation_label"] = vr.quotation_label
        cleaned["claim_check"] = vr.claim_check
        cleaned["claim_note"] = vr.claim_note
        cleaned["actual_page"] = vr.actual_page
        cleaned["page_corrected"] = vr.page_corrected
        cleaned["page_note"] = vr.page_note
        cleaned["similarity_score"] = vr.similarity_score
        if vr.effective_requirement_status is not None and "status" in cleaned:
            cleaned["status"] = vr.effective_requirement_status
        return cleaned

    out = dict(analysis_dict)

    # Metadata fields (Part A only; Part B is not_applicable)
    for meta_key in ("document_title", "issuing_authority", "document_type"):
        meta_obj = out.get(meta_key)
        if isinstance(meta_obj, dict):
            ev = meta_obj.get("evidence", "")
            pg = meta_obj.get("page")
            if meta_obj.get("value") == "Not stated in the document." or not ev.strip():
                vr = VerificationResult(
                    quotation_status="not_found",
                    quotation_label=QUOTATION_DISPLAY_LABELS["not_found"],
                    claim_check="not_applicable",
                )
            else:
                vr = _apply_part_a_dict(ev, pg)
                vr.claim_check = "not_applicable"
            out[meta_key] = _attach_result(meta_obj, vr)

    # Simplified passages (Part A only; Part B is not_applicable)
    verified_passages = []
    for item in out.get("simplified_passages", []):
        vr = _apply_part_a_dict(item.get("original", ""), item.get("page"))
        vr.claim_check = "not_applicable"
        vr.claim_note = "Plain-language wording is for convenience; review the original quote."
        verified_passages.append(_attach_result(item, vr))
    out["simplified_passages"] = verified_passages

    # Action steps (Part A only; Part B is not_applicable)
    verified_steps = []
    for item in out.get("action_steps", []):
        vr = _apply_part_a_dict(item.get("evidence", ""), item.get("page"))
        vr.claim_check = "not_applicable"
        vr.claim_note = "Interpretation and ordering of steps are left for user review."
        verified_steps.append(_attach_result(item, vr))
    out["action_steps"] = verified_steps

    # Requirements (Part A + Part B for mandatory items)
    verified_reqs = []
    for item in out.get("requirements", []):
        decl_status = item.get("status", "unclear")
        vr = _apply_part_a_dict(
            item.get("evidence", ""),
            item.get("page"),
            ambiguous_or_unclear=(decl_status == "unclear"),
        )
        vr = verify_mandatory_requirement_claim_part_b(
            requirement_item=item.get("item", ""),
            declared_status=decl_status,
            evidence=item.get("evidence", ""),
            part_a=vr,
            lang=lang,
        )
        verified_reqs.append(_attach_result(item, vr))
    out["requirements"] = verified_reqs

    # Deadlines (Part A + Part B)
    verified_deadlines = []
    for item in out.get("deadlines", []):
        date_txt = item.get("date_text", "")
        is_ambig = bool(item.get("ambiguous", False))
        if date_txt.strip() in ("NO_DEADLINE", "Not stated in the document."):
            vr = VerificationResult(
                quotation_status="not_found",
                quotation_label=QUOTATION_DISPLAY_LABELS["not_found"],
                claim_check="not_applicable",
            )
        else:
            vr = _apply_part_a_dict(
                item.get("evidence", ""),
                item.get("page"),
                ambiguous_or_unclear=is_ambig,
            )
            vr = verify_deadline_claim_part_b(
                date_text=date_txt,
                ambiguous=is_ambig,
                evidence=item.get("evidence", ""),
                part_a=vr,
                lang=lang,
            )
        verified_deadlines.append(_attach_result(item, vr))
    out["deadlines"] = verified_deadlines

    # Fees (Part A + Part B)
    verified_fees = []
    for item in out.get("fees", []):
        amt = item.get("amount", "")
        if amt.strip() in ("NO_FEE", "Not stated in the document."):
            vr = VerificationResult(
                quotation_status="not_found",
                quotation_label=QUOTATION_DISPLAY_LABELS["not_found"],
                claim_check="not_applicable",
            )
        else:
            vr = _apply_part_a_dict(item.get("evidence", ""), item.get("page"))
            vr = verify_fee_claim_part_b(
                amount=amt,
                evidence=item.get("evidence", ""),
                part_a=vr,
            )
        verified_fees.append(_attach_result(item, vr))
    out["fees"] = verified_fees

    out["verification_limitation_note"] = PART_B_LIMITATION_NOTE
    return out