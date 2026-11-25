import os
import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.languages import detect_document_language
from app.main import app, limiter
from app.verification_engine import EXPERIMENTAL_CLAIM_NOTE, verify_analysis_items


def _make_unicode_pdf(text: str) -> bytes:
    """Create a PDF with embedded UTF-8 ToUnicode font mappings for Indic & RTL scripts."""
    doc = pymupdf.open()
    page = doc.new_page()
    rect = pymupdf.Rect(50, 50, 540, 750)

    nirmala = r"C:\Windows\Fonts\Nirmala.ttf"
    segoe = r"C:\Windows\Fonts\segoeui.ttf"
    font_css = ""
    if os.path.exists(nirmala) and os.path.exists(segoe):
        font_css = """
        @font-face { font-family: TestIndic; src: url("file:///C:/Windows/Fonts/Nirmala.ttf"); }
        @font-face { font-family: TestGlobal; src: url("file:///C:/Windows/Fonts/segoeui.ttf"); }
        body { font-family: TestIndic, TestGlobal, sans-serif; }
        """

    html = f"<html><head><style>{font_css}</style></head><body><p style='font-size:14pt;'>{text}</p></body></html>"
    page.insert_htmlbox(rect, html)
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture(autouse=True)
def reset_state(monkeypatch: pytest.MonkeyPatch):
    limiter.reset()
    monkeypatch.setattr(settings, "MOCK_MODE", True)
    yield


def test_languages_endpoint_exposes_validated_and_experimental_tiers():
    client = TestClient(app)
    res = client.get("/api/languages")
    assert res.status_code == 200
    langs = {item["code"]: item for item in res.json()["languages"]}

    assert langs["en"]["tier"] == "validated"
    assert langs["ta"]["tier"] == "validated"
    assert langs["hi"]["tier"] == "validated"
    assert langs["fr"]["tier"] == "experimental"
    assert langs["te"]["tier"] == "experimental"
    assert langs["ar"]["direction"] == "rtl"


@pytest.mark.parametrize(
    "exp_lang,source_quote",
    [
        ("ta", "Applicants must submit Form A before the closing date."),
        ("hi", "Applicants must submit Form A before the closing date."),
        ("fr", "Applicants must submit Form A before the closing date."),
        ("te", "Applicants must submit Form A before the closing date."),
    ],
)
def test_quotes_remain_in_source_language_when_translating_explanations(
    exp_lang: str,
    source_quote: str,
):
    """(a) Quotes remain verbatim in the source language when translating explanations into ta, hi, fr, te."""
    client = TestClient(app)
    pdf_bytes = _make_unicode_pdf(source_quote)

    res = client.post(
        "/api/analyze",
        files={"file": ("notice.pdf", pdf_bytes, "application/pdf")},
        data={"document_language": "auto", "explanation_language": exp_lang},
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["document_language"] == "en"
    assert body["explanation_language"] == exp_lang
    passage = body["analysis"]["simplified_passages"][0]
    assert passage["original"] == source_quote
    assert passage["quotation_status"] == "exact_quotation_found"


@pytest.mark.parametrize(
    "lang,deadline_quote,date_text,req_quote",
    [
        (
            "en",
            "Applications must be submitted on or before 30 November 2026.",
            "30 November 2026",
            "Applicants must attach proof of residence.",
        ),
        (
            "ta",
            "விண்ணப்பங்களை 30 நவம்பர் 2026 க்கு முன்பாக சமர்ப்பிக்க வேண்டும்.",
            "30 நவம்பர் 2026",
            "விண்ணப்பதாரர்கள் முகவரி சான்று இணைக்க வேண்டும்.",
        ),
        (
            "hi",
            "आवेदन 30 नवंबर 2026 से पहले जमा करना अनिवार्य है।",
            "30 नवंबर 2026",
            "आवेदकों को निवास प्रमाण संलग्न करना अनिवार्य है।",
        ),
    ],
)
def test_part_b_runs_calibrated_cue_checks_for_validated_languages(
    lang: str,
    deadline_quote: str,
    date_text: str,
    req_quote: str,
):
    """(b) Part B runs full lexical cue checks for validated tier languages (en, ta, hi)."""
    pages = [
        {
            "page_number": 1,
            "kind": "text",
            "redacted_text": f"{deadline_quote}\n{req_quote}",
        }
    ]
    raw = {
        "readability": "good",
        "document_title": {"value": "Notice", "evidence": deadline_quote, "page": 1},
        "issuing_authority": {"value": "Not stated in the document.", "evidence": "", "page": None},
        "document_type": {"value": "Notice", "evidence": deadline_quote, "page": 1},
        "summary": "Summary",
        "simplified_passages": [],
        "requirements": [
            {"item": "Proof of residence", "status": "mandatory", "evidence": req_quote, "page": 1}
        ],
        "action_steps": [],
        "deadlines": [
            {
                "description": "Submission deadline",
                "date_text": date_text,
                "ambiguous": False,
                "evidence": deadline_quote,
                "page": 1,
            }
        ],
        "fees": [],
        "missing_information": [],
        "warnings": [],
    }

    verified = verify_analysis_items(raw, redacted_pages=pages, has_image_content=False, lang=lang)
    assert verified["deadlines"][0]["claim_check"] == "passed"
    assert verified["deadlines"][0]["quotation_status"] == "exact_quotation_found"
    assert verified["requirements"][0]["claim_check"] == "passed"
    assert verified["requirements"][0]["status"] == "mandatory"


@pytest.mark.parametrize(
    "exp_lang,quote,date_text",
    [
        (
            "fr",
            "Les candidats doivent déposer le dossier avant le 15 décembre 2026.",
            "15 décembre 2026",
        ),
        (
            "te",
            "దరఖాస్తుదారులు 15 డిసెంబర్ 2026 లోపు ఫారమ్ సమర్పించాలి.",
            "15 డిసెంబర్ 2026",
        ),
    ],
)
def test_experimental_languages_gracefully_fallback_to_needs_user_verification(
    exp_lang: str,
    quote: str,
    date_text: str,
):
    """(c) Experimental languages do not falsely fail claims; they set claim_check='not_applicable' and needs_user_verification."""
    pages = [{"page_number": 1, "kind": "text", "redacted_text": quote}]
    raw = {
        "readability": "good",
        "document_title": {"value": "Notice", "evidence": quote, "page": 1},
        "issuing_authority": {"value": "Not stated in the document.", "evidence": "", "page": None},
        "document_type": {"value": "Notice", "evidence": quote, "page": 1},
        "summary": "Summary",
        "simplified_passages": [],
        "requirements": [
            {"item": "Submit form", "status": "mandatory", "evidence": quote, "page": 1}
        ],
        "action_steps": [],
        "deadlines": [
            {
                "description": "Submission deadline",
                "date_text": date_text,
                "ambiguous": False,
                "evidence": quote,
                "page": 1,
            }
        ],
        "fees": [],
        "missing_information": [],
        "warnings": [],
    }

    verified = verify_analysis_items(raw, redacted_pages=pages, has_image_content=False, lang=exp_lang)

    # Part A still finds the exact quote
    assert verified["document_title"]["quotation_status"] == "exact_quotation_found"

    # Part B does not fail; gracefully sets not_applicable + needs_user_verification + calibration note
    assert verified["deadlines"][0]["claim_check"] == "not_applicable"
    assert verified["deadlines"][0]["quotation_status"] == "needs_user_verification"
    assert verified["deadlines"][0]["claim_note"] == EXPERIMENTAL_CLAIM_NOTE

    assert verified["requirements"][0]["claim_check"] == "not_applicable"
    assert verified["requirements"][0]["quotation_status"] == "needs_user_verification"
    assert verified["requirements"][0]["claim_note"] == EXPERIMENTAL_CLAIM_NOTE


def test_invalid_bcp47_language_rejected_without_english_fallback():
    client = TestClient(app)
    pdf_bytes = _make_unicode_pdf("Applicants must submit Form A at the office.")
    res = client.post(
        "/api/analyze",
        files={"file": ("notice.pdf", pdf_bytes, "application/pdf")},
        data={"document_language": "auto", "explanation_language": "invalid_lang_999"},
    )
    assert res.status_code == 400
    assert "not a supported BCP-47 language" in res.json()["error"]


def test_uncertain_language_detection_on_minimal_text():
    code, _, uncertain = detect_document_language("Form A")
    assert code == "en"
    assert uncertain is True