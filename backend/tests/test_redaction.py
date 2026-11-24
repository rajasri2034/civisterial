import io
import logging

import fitz  # PyMuPDF
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
from app.main import app, limiter
from app.redactor import (
    IMAGE_REDACTION_WARNING,
    build_gemini_input_payload,
    redact_extracted_pages,
    verhoeff_compute_check_digit,
)


def _synth_aadhaar(prefix_11: str = "49128374651", sep: str = " ") -> str:
    """Generate a synthetically valid 12-digit Verhoeff number for testing."""
    assert len(prefix_11) == 11 and prefix_11[0] in "23456789"
    check = verhoeff_compute_check_digit(prefix_11)
    full = prefix_11 + check
    if sep:
        return f"{full[:4]}{sep}{full[4:8]}{sep}{full[8:]}"
    return full


def _synth_invalid_verhoeff(prefix_11: str = "49128374651") -> str:
    """Generate a 12-digit number with a deliberately wrong Verhoeff check digit."""
    good_check = int(verhoeff_compute_check_digit(prefix_11))
    bad_check = (good_check + 1) % 10
    full = f"{prefix_11}{bad_check}"
    return f"{full[:4]} {full[4:8]} {full[8:]}"


def _make_pdf(pages: list[tuple[str, bytes | None]]) -> bytes:
    doc = fitz.open()
    for text, img_bytes in pages:
        page = doc.new_page()
        if text:
            page.insert_textbox(fitz.Rect(50, 50, 540, 750), text)
        if img_bytes:
            page.insert_image(fitz.Rect(50, 180, 200, 330), stream=img_bytes)
    data = doc.tobytes()
    doc.close()
    return data


def _make_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), color=(20, 40, 80)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def reset_limiter():
    limiter.reset()
    yield


def test_detects_all_synthetic_identifier_types():
    aadhaar_spaced = _synth_aadhaar("38291047562", " ")
    aadhaar_hyphen = _synth_aadhaar("51928374650", "-")
    indian_phone = "+91 98401 23456"
    intl_phone = "+44 20 7946 0958"
    email = "applicant.demo@example.org"
    bank_acct = "10293847561234"
    ifsc = "SBIN0001234"
    pan = "ABCDE1234F"

    sample_text = (
        f"Applicant Identity: {aadhaar_spaced} and secondary {aadhaar_hyphen}. "
        f"Mobile: {indian_phone}, Overseas Contact: {intl_phone}, Email: {email}. "
        f"Disbursement Bank Account: {bank_acct}, IFSC: {ifsc}, Tax PAN: {pan}."
    )

    result = redact_extracted_pages(
        [{"page_number": 1, "kind": "text", "text": sample_text, "notice": None}]
    )
    page = result[0]
    assert page["redaction_status"] == "redacted"
    assert page["redaction_applied"] is True
    assert page["redaction_counts"] == {
        "EMAIL": 1,
        "AADHAAR": 2,
        "PAN": 1,
        "IFSC": 1,
        "BANK_ACCOUNT": 1,
        "PHONE": 2,
    }

    masked = page["redacted_text"]
    for secret in [
        aadhaar_spaced,
        aadhaar_hyphen,
        indian_phone,
        intl_phone,
        email,
        bank_acct,
        ifsc,
        pan,
    ]:
        assert secret not in masked

    assert "[AADHAAR_1]" in masked
    assert "[AADHAAR_2]" in masked
    assert "[PHONE_1]" in masked
    assert "[PHONE_2]" in masked
    assert "[EMAIL_1]" in masked
    assert "[BANK_ACCOUNT_1]" in masked
    assert "[IFSC_1]" in masked
    assert "[PAN_1]" in masked


def test_near_miss_numbers_dates_fees_and_references_not_redacted():
    bad_verhoeff = _synth_invalid_verhoeff("61234567891")
    text = (
        f"Notice Date: 24/11/2026 and ISO Date: 2026-11-24. "
        f"Application Fee: Rs. 150000000 and INR 250000000. "
        f"Case Reference: REF-987654321012 and Order No: 12345678901. "
        f"Non-Verhoeff 12-digit serial: {bad_verhoeff}. "
        f"Short 6-digit PIN: 600001."
    )

    result = redact_extracted_pages(
        [{"page_number": 1, "kind": "text", "text": text, "notice": None}]
    )
    page = result[0]
    assert page["redaction_status"] == "nothing_detected"
    assert page["redaction_applied"] is True
    assert page["redaction_counts"] == {}
    assert page["redacted_text"] == text


def test_same_value_gets_same_placeholder_within_and_across_pages():
    aadhaar_spaced = _synth_aadhaar("72910485631", " ")
    aadhaar_compact = aadhaar_spaced.replace(" ", "")
    phone_a = "+91 98401 11223"
    phone_b = "9840111223"
    email = "citizen.one@example.net"

    pages = [
        {
            "page_number": 1,
            "kind": "text",
            "text": f"Page 1: ID {aadhaar_spaced}, Phone {phone_a}, Repeat Phone {phone_b}, Email {email}.",
            "notice": None,
        },
        {
            "page_number": 2,
            "kind": "text",
            "text": f"Page 2: Same ID without spaces {aadhaar_compact}, same email {email}.",
            "notice": None,
        },
    ]

    result = redact_extracted_pages(pages)
    p1_text = result[0]["redacted_text"]
    p2_text = result[1]["redacted_text"]

    assert "[AADHAAR_1]" in p1_text
    assert "[AADHAAR_1]" in p2_text
    assert "[AADHAAR_2]" not in p2_text

    assert p1_text.count("[PHONE_1]") == 2
    assert "[PHONE_2]" not in p1_text

    assert "[EMAIL_1]" in p1_text
    assert "[EMAIL_1]" in p2_text


def test_mixed_page_pdf_reports_per_page_status_and_image_warning(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "MOCK_MODE", True)
    aadhaar = _synth_aadhaar("83492017465", " ")
    email = "resident@example.com"
    pdf_bytes = _make_pdf(
        [
            (f"Page 1: Citizen Aadhaar {aadhaar} and Email {email} for housing subsidy.", None),
            ("Page 2: General eligibility criteria and statutory appeal timeline of 30 days.", None),
            ("", _make_png()),
        ]
    )

    client = TestClient(app)
    with caplog.at_level(logging.INFO):
        res = client.post(
            "/api/analyze",
            files={"file": ("mixed_pii.pdf", pdf_bytes, "application/pdf")},
            data={"image_confirmation": "I confirm this is a public or synthetic document"},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["page_count"] == 3

    # Page 1: PII detected and redacted
    assert body["pages"][0]["redaction_status"] == "redacted"
    assert body["pages"][0]["redaction_applied"] is True
    assert body["pages"][0]["redaction_counts"] == {"EMAIL": 1, "AADHAAR": 1}
    assert "[AADHAAR_1]" in body["pages"][0]["redacted_text"]
    assert "[EMAIL_1]" in body["pages"][0]["redacted_text"]

    # Page 2: Clean text page
    assert body["pages"][1]["redaction_status"] == "nothing_detected"
    assert body["pages"][1]["redaction_applied"] is True
    assert body["pages"][1]["redaction_counts"] == {}

    # Page 3: Image-based page (no protection claimed, explicit warning attached)
    assert body["pages"][2]["kind"] == "image_based"
    assert body["pages"][2]["redaction_status"] == "not_applicable_image_page"
    assert body["pages"][2]["redaction_applied"] is False
    assert IMAGE_REDACTION_WARNING in body["pages"][2]["notice"]

    # Verify neither original PII nor placeholders/mappings appear in logs
    assert aadhaar not in caplog.text
    assert aadhaar.replace(" ", "") not in caplog.text
    assert email not in caplog.text
    assert "[AADHAAR_1]" not in caplog.text


def test_no_original_identifier_in_gemini_payload_or_any_output_path(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "MOCK_MODE", True)
    aadhaar = _synth_aadhaar("91827364512", "-")
    pan = "PQRST5678K"
    ifsc = "HDFC0004321"
    acct = "50100293847561"
    phone = "+91 91234 56789"
    email = "person.test@example.org"

    pdf_bytes = _make_pdf(
        [
            (
                f"Name on file. Aadhaar {aadhaar}, PAN {pan}, Account {acct}, "
                f"IFSC {ifsc}, Phone {phone}, Email {email}.",
                None,
            )
        ]
    )

    client = TestClient(app)
    res = client.post(
        "/api/analyze",
        files={"file": ("check_leak.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 200
    response_json = res.json()
    raw_response_str = res.text

    gemini_payload = build_gemini_input_payload(response_json["pages"])

    sensitive_values = [
        aadhaar,
        aadhaar.replace("-", ""),
        pan,
        ifsc,
        acct,
        phone,
        "9123456789",
        email,
    ]

    for val in sensitive_values:
        assert val not in raw_response_str
        assert val not in gemini_payload

    assert "[AADHAAR_1]" in gemini_payload
    assert "[PAN_1]" in gemini_payload
    assert "[BANK_ACCOUNT_1]" in gemini_payload
    assert "[IFSC_1]" in gemini_payload
    assert "[PHONE_1]" in gemini_payload
    assert "[EMAIL_1]" in gemini_payload