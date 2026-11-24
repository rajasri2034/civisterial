import pytest
from pydantic import ValidationError
from rapidfuzz import fuzz

from app.schemas import GeminiDocumentAnalysis
from app.verification_engine import (
    QUOTATION_DISPLAY_LABELS,
    normalize_text,
    verify_analysis_items,
    verify_deadline_claim_part_b,
    verify_fee_claim_part_b,
    verify_mandatory_requirement_claim_part_b,
    verify_quotation_part_a,
)


def _pages(text_by_page: dict[int, str]) -> list[dict]:
    return [
        {
            "page_number": p_num,
            "kind": "text",
            "redaction_applied": True,
            "redacted_text": txt,
        }
        for p_num, txt in sorted(text_by_page.items())
    ]


def test_exact_match_and_label():
    pages = _pages({1: "Applicants must submit Form A at the district office."})
    res = verify_quotation_part_a(
        evidence="Applicants must submit Form A at the district office.",
        stated_page=1,
        pages=pages,
    )
    assert res.quotation_status == "exact_quotation_found"
    assert res.quotation_label == "Exact quotation found"
    assert "verified" not in res.quotation_label.lower()
    assert res.actual_page == 1
    assert res.page_corrected is False
    assert res.similarity_score == 100.0


def test_whitespace_hyphenation_linebreaks_and_smart_quotes():
    doc_text = (
        "“Applicants   must   submit   the   appli-\ncation   form   for   ‘housing   grant’   renewal.”"
    )
    quote = '"Applicants must submit the application form for \'housing grant\' renewal."'
    pages = _pages({1: doc_text})

    res = verify_quotation_part_a(evidence=quote, stated_page=1, pages=pages)
    assert res.quotation_status == "exact_quotation_found"
    assert res.quotation_label == "Exact quotation found"
    assert res.page_corrected is False


def test_fuzzy_thresholds_84_85_and_99():
    base = "".join(chr(97 + (i % 26)) for i in range(100))
    pages = _pages({1: base})

    def _corrupt_evenly(s: str, count: int) -> str:
        chars = list(s)
        step = len(s) // count
        for k in range(count):
            idx = min(len(s) - 2, k * step + 1)
            chars[idx] = "?"
        return "".join(chars)

    # 84% match (< 85) -> not_found
    q_84 = _corrupt_evenly(base, 16)
    assert round(fuzz.partial_ratio(q_84, base)) == 84
    res_84 = verify_quotation_part_a(evidence=q_84, stated_page=1, pages=pages)
    assert res_84.quotation_status == "not_found"
    assert res_84.quotation_label == "Could not verify"

    # 85% match (>= 85) -> possible_match
    q_85 = _corrupt_evenly(base, 15)
    assert round(fuzz.partial_ratio(q_85, base)) == 85
    res_85 = verify_quotation_part_a(evidence=q_85, stated_page=1, pages=pages)
    assert res_85.quotation_status == "possible_match"
    assert res_85.quotation_label == "Possible match: review required"

    # 99% match -> possible_match (never upgraded to exact_quotation_found)
    q_99 = base[:50] + "?" + base[51:]
    assert round(fuzz.partial_ratio(q_99, base)) == 99
    res_99 = verify_quotation_part_a(evidence=q_99, stated_page=1, pages=pages)
    assert res_99.quotation_status == "possible_match"
    assert res_99.quotation_label == "Possible match: review required"
    
def test_fuzzy_score_100_that_is_not_exact_substring_stays_possible_match():
    # fuzz.partial_ratio("ab", "a") == 100.0 even though "ab" is NOT a substring of "a"
    doc_text = "a"
    quote = "ab"
    norm_q = normalize_text(quote)
    norm_d = normalize_text(doc_text)
    assert norm_q not in norm_d
    assert fuzz.partial_ratio(norm_q, norm_d) == 100.0

    res = verify_quotation_part_a(evidence=quote, stated_page=1, pages=_pages({1: doc_text}))
    assert res.similarity_score == 100.0
    assert res.quotation_status == "possible_match"
    assert res.quotation_label == "Possible match: review required"

def test_wrong_page_sets_actual_page_and_page_corrected_flag():
    pages = _pages(
        {
            1: "Page one contains general welcome instructions.",
            2: "Applicants must attach an electricity bill from the last 3 months.",
        }
    )
    res = verify_quotation_part_a(
        evidence="Applicants must attach an electricity bill from the last 3 months.",
        stated_page=1,
        pages=pages,
    )
    assert res.quotation_status == "exact_quotation_found"
    assert res.actual_page == 2
    assert res.page_corrected is True
    assert "page 2" in (res.page_note or "").lower()
    assert "page 1" in (res.page_note or "").lower()


def test_fabricated_empty_and_very_long_quotes():
    pages = _pages({1: "Short official notice regarding municipal water connection."})

    # Fabricated quote
    fab = verify_quotation_part_a(
        evidence="Every resident automatically receives a lifetime tax waiver.",
        stated_page=1,
        pages=pages,
    )
    assert fab.quotation_status == "not_found"
    assert fab.quotation_label == "Could not verify"

    # Empty quote
    empty = verify_quotation_part_a(evidence="   \n\t  ", stated_page=1, pages=pages)
    assert empty.quotation_status == "not_found"

    # Very long quote (10,000 chars)
    long_quote = "Very long fabricated clause " * 400
    long_res = verify_quotation_part_a(evidence=long_quote, stated_page=1, pages=pages)
    assert long_res.quotation_status == "not_found"


def test_scan_input_returns_needs_user_verification():
    scan_pages = [
        {
            "page_number": 1,
            "kind": "image_based",
            "redaction_applied": False,
            "redacted_text": "",
        }
    ]
    res = verify_quotation_part_a(
        evidence="Submit application before Friday.",
        stated_page=1,
        pages=scan_pages,
        is_scan_or_image=True,
    )
    assert res.quotation_status == "needs_user_verification"
    assert res.quotation_label == QUOTATION_DISPLAY_LABELS["needs_user_verification"]
    assert res.quotation_label == "Verify against your original document."


def test_deadline_quote_containing_date_without_deadline_cue_fails():
    pages = _pages({1: "This circular was published on 14/09/2026 for public information."})
    part_a = verify_quotation_part_a(
        evidence="This circular was published on 14/09/2026 for public information.",
        stated_page=1,
        pages=pages,
    )
    assert part_a.quotation_status == "exact_quotation_found"

    part_b = verify_deadline_claim_part_b(
        date_text="14/09/2026",
        ambiguous=False,
        evidence="This circular was published on 14/09/2026 for public information.",
        part_a=part_a,
    )
    assert part_b.claim_check == "failed"
    assert part_b.quotation_status == "needs_user_verification"
    assert "without clear deadline wording" in (part_b.claim_note or "").lower()


def test_fee_currency_normalization_passes_and_missing_amount_fails():
    pages = _pages({1: "A non-refundable processing fee of Rs. 500 is payable at the counter."})
    quote = "A non-refundable processing fee of Rs. 500 is payable at the counter."

    # Equivalent currency formatting (₹500 vs Rs. 500) matches
    part_a_ok = verify_quotation_part_a(evidence=quote, stated_page=1, pages=pages)
    part_b_ok = verify_fee_claim_part_b(amount="₹500", evidence=quote, part_a=part_a_ok)
    assert part_b_ok.claim_check == "passed"

    # Amount not present in quote (₹1,500) fails
    part_a_fail = verify_quotation_part_a(evidence=quote, stated_page=1, pages=pages)
    part_b_fail = verify_fee_claim_part_b(amount="₹1,500", evidence=quote, part_a=part_a_fail)
    assert part_b_fail.claim_check == "failed"
    assert part_b_fail.quotation_status == "needs_user_verification"


def test_mandatory_requirement_whose_quote_says_may_or_separate_clause_becomes_unclear():
    quote = "Applicants must submit Form A. Payment of the optional service fee may be made separately."
    pages = _pages({1: quote})

    # Claiming the optional service fee is mandatory must fail and downgrade to unclear
    part_a = verify_quotation_part_a(evidence=quote, stated_page=1, pages=pages)
    part_b = verify_mandatory_requirement_claim_part_b(
        requirement_item="Pay the service fee",
        declared_status="mandatory",
        evidence=quote,
        part_a=part_a,
    )
    assert part_b.claim_check == "failed"
    assert part_b.quotation_status == "needs_user_verification"
    assert part_b.effective_requirement_status == "unclear"

    # Meanwhile, Form A in the first clause is genuinely mandatory
    part_a_form = verify_quotation_part_a(evidence=quote, stated_page=1, pages=pages)
    part_b_form = verify_mandatory_requirement_claim_part_b(
        requirement_item="Submit Form A",
        declared_status="mandatory",
        evidence=quote,
        part_a=part_a_form,
    )
    assert part_b_form.claim_check == "passed"
    assert part_b_form.effective_requirement_status == "mandatory"


def test_ai_cannot_set_quotation_status_or_claim_check():
    # 1. GeminiDocumentAnalysis schema forbids AI from supplying quotation_status or claim_check
    with pytest.raises(ValidationError):
        GeminiDocumentAnalysis(
            readability="good",
            document_title={"value": "Not stated in the document.", "evidence": "", "page": None},
            issuing_authority={"value": "Not stated in the document.", "evidence": "", "page": None},
            document_type={"value": "Not stated in the document.", "evidence": "", "page": None},
            summary="Summary.",
            requirements=[
                {
                    "item": "Submit Form A",
                    "status": "mandatory",
                    "evidence": "Applicants must submit Form A.",
                    "page": 1,
                    "quotation_status": "exact_quotation_found",
                    "claim_check": "passed",
                }
            ],
        )

    # 2. Even if a raw dict contains spoofed status fields, verify_analysis_items overwrites them
    spoofed_raw = {
        "readability": "good",
        "document_title": {"value": "Not stated in the document.", "evidence": "", "page": None},
        "issuing_authority": {"value": "Not stated in the document.", "evidence": "", "page": None},
        "document_type": {"value": "Not stated in the document.", "evidence": "", "page": None},
        "summary": "Summary.",
        "simplified_passages": [],
        "requirements": [
            {
                "item": "Submit Form A",
                "status": "mandatory",
                "evidence": "Completely fabricated quote not in document.",
                "page": 1,
                "quotation_status": "exact_quotation_found",
                "claim_check": "passed",
            }
        ],
        "action_steps": [],
        "deadlines": [],
        "fees": [],
        "missing_information": [],
        "warnings": [],
    }
    verified = verify_analysis_items(
        spoofed_raw,
        redacted_pages=_pages({1: "Actual document text about unrelated parking rules."}),
    )
    assert verified["requirements"][0]["quotation_status"] == "needs_user_verification"
    assert verified["requirements"][0]["claim_check"] == "failed"
    assert verified["requirements"][0]["status"] == "unclear"