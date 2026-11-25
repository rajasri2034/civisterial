import asyncio
import io
import logging
import os
import re
import subprocess
import zipfile
from pathlib import Path

import httpx
import pymupdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import main as main_module
from app.config import ensure_isolated_temp_dir, settings
from app.main import app, limiter


def _make_text_pdf(pages_text: list[str], *, embed_js: bool = False, attach_file: bool = False) -> bytes:
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page()
        if text:
            page.insert_text((50, 72), text)
    if embed_js:
        doc.embfile_add("payload.js", b"app.alert('xss');", filename="payload.js")
    if attach_file:
        doc.embfile_add("secret.txt", b"embedded payload", filename="secret.txt")
    data = doc.tobytes()
    doc.close()
    return data


def _make_encrypted_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Confidential encrypted text.")
    data = doc.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner123",
        user_pw="user123",
    )
    doc.close()
    return data


def _make_mixed_pdf() -> bytes:
    """Page 1: text with fake PII; Page 2: pure raster image page with zero text layer."""
    doc = pymupdf.open()
    p1 = doc.new_page()
    p1.insert_text(
        (50, 72),
        "Applicant Priya Nair (Email: priya.nair@example.org, Phone: +91-9876543210, ID: ABCDE1234F) must submit Form A.",
    )
    p2 = doc.new_page()
    img = Image.new("RGB", (200, 120), color=(230, 235, 240))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    p2.insert_image(pymupdf.Rect(50, 50, 250, 170), stream=buf.getvalue())
    data = doc.tobytes()
    doc.close()
    return data


def _make_png_bytes(width: int = 120, height: int = 80) -> bytes:
    img = Image.new("RGB", (width, height), color=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def reset_security_env(monkeypatch: pytest.MonkeyPatch):
    limiter.reset()
    monkeypatch.setattr(settings, "MOCK_MODE", True)
    yield


# ---------------------------------------------------------------------------
# 1. Upload limits, rate limits, and wrong HTTP methods
# ---------------------------------------------------------------------------
def test_1_upload_limits_rate_limits_and_http_methods():
    client = TestClient(app)

    assert client.get("/api/analyze").status_code == 405
    assert client.put("/api/analyze").status_code == 405
    assert client.delete("/api/analyze").status_code == 405
    assert client.post("/api/health").status_code == 405
    assert client.post("/api/languages").status_code == 405

    assert client.post("/api/analyze").status_code == 400

    oversized = b"%PDF-1.4\n" + (b"0" * (settings.MAX_UPLOAD_BYTES + 1024))
    res_big = client.post(
        "/api/analyze",
        files={"file": ("huge.pdf", oversized, "application/pdf")},
    )
    assert res_big.status_code == 413

    valid_pdf = _make_text_pdf(["Valid administrative notice text."])
    statuses = [
        client.post(
            "/api/inspect",
            files={"file": ("ok.pdf", valid_pdf, "application/pdf")},
        ).status_code
        for _ in range(25)
    ]
    assert 429 in statuses


# ---------------------------------------------------------------------------
# 2. Stateless isolation: no history endpoints & concurrent request isolation
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_2_no_history_endpoints_and_concurrent_request_isolation():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        for path in ("/api/results", "/api/history", "/api/uploads", "/api/files"):
            resp = await client.get(path)
            assert resp.status_code == 404

        pdf_alpha = _make_text_pdf(["ALPHA_UNIQUE_DOCUMENT_TOKEN_9911 must be filed."])
        pdf_beta = _make_text_pdf(["BETA_UNIQUE_DOCUMENT_TOKEN_7722 must be filed."])

        res_a, res_b = await asyncio.gather(
            client.post(
                "/api/analyze",
                files={"file": ("alpha.pdf", pdf_alpha, "application/pdf")},
            ),
            client.post(
                "/api/analyze",
                files={"file": ("beta.pdf", pdf_beta, "application/pdf")},
            ),
        )

        assert res_a.status_code == 200
        assert res_b.status_code == 200

        body_a = res_a.text
        body_b = res_b.text

        assert "ALPHA_UNIQUE_DOCUMENT_TOKEN_9911" in body_a
        assert "BETA_UNIQUE_DOCUMENT_TOKEN_7722" not in body_a

        assert "BETA_UNIQUE_DOCUMENT_TOKEN_7722" in body_b
        assert "ALPHA_UNIQUE_DOCUMENT_TOKEN_9911" not in body_b


# ---------------------------------------------------------------------------
# 3. Malicious uploads: polyglots, fake headers, zip-in-image, JS/embedded PDF, encrypted, traversal
# ---------------------------------------------------------------------------
def test_3_malicious_uploads_rejected_or_safely_contained():
    client = TestClient(app)

    # (a) Fake PDF header wrapping HTML/JS script
    fake_pdf = b"%PDF-1.7\n<html><script>alert(1)</script></html>"
    r_fake = client.post(
        "/api/analyze",
        files={"file": ("fake.pdf", fake_pdf, "application/pdf")},
    )
    assert r_fake.status_code == 400

    # (b) Polyglot PNG + trailing ZIP archive
    png_bytes = _make_png_bytes()
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("bomb.txt", b"A" * 50000)
    polyglot = png_bytes + zip_buf.getvalue()
    r_poly_no_confirm = client.post(
        "/api/analyze",
        files={"file": ("poly.png", polyglot, "image/png")},
    )
    assert r_poly_no_confirm.status_code == 400

    # (c) Encrypted / password-protected PDF rejected
    enc_pdf = _make_encrypted_pdf()
    r_enc = client.post(
        "/api/analyze",
        files={"file": ("locked.pdf", enc_pdf, "application/pdf")},
    )
    assert r_enc.status_code == 400

    # (d) PDF with embedded JS/file attachment rejected cleanly by parser worker
    js_pdf = _make_text_pdf(["Visible official clause."], embed_js=True, attach_file=True)
    r_js = client.post(
        "/api/analyze",
        files={"file": ("with_js.pdf", js_pdf, "application/pdf")},
    )
    assert r_js.status_code == 400
    assert "app.alert" not in r_js.text
    assert "embedded payload" not in r_js.text

    # (e) Path traversal filename cannot write outside temp dir
    tmp_dir = ensure_isolated_temp_dir()
    before_tmp = set(tmp_dir.iterdir())
    valid_pdf = _make_text_pdf(["Safe document text."])
    r_trav = client.post(
        "/api/analyze",
        files={"file": ("../../../../evil_escape.pdf", valid_pdf, "application/pdf")},
    )
    assert r_trav.status_code == 200
    assert not (tmp_dir.parent / "evil_escape.pdf").exists()
    assert set(tmp_dir.iterdir()) == before_tmp


# ---------------------------------------------------------------------------
# 4. DoS resilience: huge page counts & expensive-to-parse file stopped by worker limits
# ---------------------------------------------------------------------------
def test_4_dos_huge_page_count_and_worker_timeout(monkeypatch: pytest.MonkeyPatch):
    client = TestClient(app)

    over_pages_pdf = _make_text_pdf(["Page text"] * (settings.MAX_PDF_PAGES + 5))
    r_pages = client.post(
        "/api/analyze",
        files={"file": ("many_pages.pdf", over_pages_pdf, "application/pdf")},
    )
    assert r_pages.status_code == 400
    assert "page" in r_pages.json()["error"].lower()

    # Worker subprocess timeout kills expensive parse cleanly and returns a friendly HTTP error
    from fastapi import HTTPException

    valid_pdf = _make_text_pdf(["Normal text"])

    async def _timeout_isolated_parser(*args, **kwargs):
        raise HTTPException(
            status_code=504,
            detail="Document parsing took too long and was stopped by worker limits.",
        )

    monkeypatch.setattr(main_module, "run_isolated_parser", _timeout_isolated_parser)
    r_slow_worker = client.post(
        "/api/analyze",
        files={"file": ("slow_parse.pdf", valid_pdf, "application/pdf")},
    )
    assert r_slow_worker.status_code in (400, 408, 504)
# ---------------------------------------------------------------------------
# 5. API-key exposure check across frontend build, API responses, errors, and Git history
# ---------------------------------------------------------------------------
def test_5_no_api_key_in_frontend_responses_errors_or_git_history(monkeypatch: pytest.MonkeyPatch):
    fake_secret_key = ("AIzaSy" + "TestDummySecretKey9876543210XYZ")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", fake_secret_key)
    monkeypatch.setattr(settings, "MOCK_MODE", True)

    client = TestClient(app)
    valid_pdf = _make_text_pdf(["Official notice text."])

    ok_res = client.post(
        "/api/analyze",
        files={"file": ("notice.pdf", valid_pdf, "application/pdf")},
    )
    assert fake_secret_key not in ok_res.text
    assert "AIzaSy" not in ok_res.text

    err_res = client.post(
        "/api/analyze",
        files={"file": ("bad.pdf", b"not-a-pdf", "application/pdf")},
    )
    assert fake_secret_key not in err_res.text
    assert "AIzaSy" not in err_res.text

    repo_root = Path(__file__).resolve().parents[2]
    for folder in (repo_root / "frontend" / "src", repo_root / "frontend" / "dist"):
        if folder.exists():
            for file_path in folder.rglob("*"):
                if file_path.is_file() and file_path.suffix in {".js", ".jsx", ".html", ".css"}:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    assert not re.search(r"AIza[0-9A-Za-z\-_]{20,}", content), f"Key leaked in {file_path}"

    git_check = subprocess.run(
        ["git", "log", "-p", "-n", "30"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    if git_check.returncode == 0:
        assert not re.search(r"AIza[0-9A-Za-z\-_]{25,}", git_check.stdout)


# ---------------------------------------------------------------------------
# 6. Temp-file cleanup after failures, timeouts, cancellation & multipart spooling
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_6_temp_file_cleanup_and_multipart_spooling(monkeypatch: pytest.MonkeyPatch):
    tmp_dir = ensure_isolated_temp_dir()
    before_files = set(tmp_dir.iterdir())

    small_pdf = _make_text_pdf(["Small in-memory upload test."])
    assert len(small_pdf) < settings.UPLOAD_SPOOL_THRESHOLD_BYTES

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        res_ok = await client.post(
            "/api/analyze",
            files={"file": ("small.pdf", small_pdf, "application/pdf")},
        )
        assert res_ok.status_code == 200
        assert set(tmp_dir.iterdir()) == before_files

        res_fail = await client.post(
            "/api/analyze",
            files={"file": ("corrupt.pdf", b"%PDF-corrupt", "application/pdf")},
        )
        assert res_fail.status_code == 400
        assert set(tmp_dir.iterdir()) == before_files

        started = asyncio.Event()

        async def _slow_ai(*args, **kwargs):
            started.set()
            await asyncio.sleep(5)

        monkeypatch.setattr(main_module, "analyze_with_gemini", _slow_ai)
        task = asyncio.create_task(
            client.post(
                "/api/analyze",
                files={"file": ("cancel.pdf", small_pdf, "application/pdf")},
            )
        )
        await asyncio.wait_for(started.wait(), timeout=2.0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    await asyncio.sleep(0.1)
    assert set(tmp_dir.iterdir()) == before_files


# ---------------------------------------------------------------------------
# 7. Accidental personal-data logging check
# ---------------------------------------------------------------------------
def test_7_no_personal_data_written_to_logs(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.DEBUG)
    client = TestClient(app)

    fake_pii_pdf = _make_text_pdf(
        [
            "Applicant: Rahul Deshmukh | Email: rahul.deshmukh.secret@example.org | "
            "Phone: +91-9988776655 | Aadhaar: 4321 8765 9012"
        ]
    )

    res = client.post(
        "/api/analyze",
        files={"file": ("pii_check.pdf", fake_pii_pdf, "application/pdf")},
    )
    assert res.status_code == 200

    all_logs = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "Rahul Deshmukh" not in all_logs
    assert "rahul.deshmukh.secret@example.org" not in all_logs
    assert "9988776655" not in all_logs
    assert "4321 8765 9012" not in all_logs


# ---------------------------------------------------------------------------
# 8. Privacy behavior: redaction preserved, image confirmation enforced, mixed PDF page statuses
# ---------------------------------------------------------------------------
def test_8_privacy_redaction_image_gate_and_mixed_pdf_status():
    client = TestClient(app)
    mixed_pdf = _make_mixed_pdf()

    r_blocked = client.post(
        "/api/analyze",
        files={"file": ("mixed.pdf", mixed_pdf, "application/pdf")},
    )
    assert r_blocked.status_code == 400

    r_ok = client.post(
        "/api/analyze",
        files={"file": ("mixed.pdf", mixed_pdf, "application/pdf")},
        data={"image_confirmation": "I confirm this is a public or synthetic document"},
    )
    assert r_ok.status_code == 200
    body = r_ok.json()

    raw_text = r_ok.text
    assert "priya.nair@example.org" not in raw_text
    assert "9876543210" not in raw_text
    assert "ABCDE1234F" not in raw_text

    pages = body["pages"]
    assert len(pages) == 2
    assert pages[0]["kind"] == "text"
    assert pages[0]["redaction_applied"] is True
    assert pages[0]["redaction_counts"].get("EMAIL", 0) >= 1
    assert pages[1]["kind"] == "image_based"
    assert pages[1]["redaction_applied"] is False


# ---------------------------------------------------------------------------
# 9. CORS origin restriction, security headers, and non-leaky error responses
# ---------------------------------------------------------------------------
def test_9_cors_security_headers_and_sanitized_errors():
    client = TestClient(app)

    r_allowed = client.get(
        "/api/health",
        headers={"Origin": settings.FRONTEND_ORIGIN},
    )
    assert r_allowed.status_code == 200
    assert r_allowed.headers.get("access-control-allow-origin") == settings.FRONTEND_ORIGIN

    r_evil = client.get(
        "/api/health",
        headers={"Origin": "https://evil-attacker.example.com"},
    )
    assert r_evil.headers.get("access-control-allow-origin") is None

    # Security headers present on responses
    assert r_allowed.headers.get("x-content-type-options") == "nosniff"
    assert "no-store" in (r_allowed.headers.get("cache-control") or "").lower()
    assert r_allowed.headers.get("referrer-policy") == "no-referrer"

    # Error responses expose no file paths, stack traces, or internal module names
    r_err = client.post(
        "/api/analyze",
        files={"file": ("broken.pdf", b"%PDF-broken", "application/pdf")},
    )
    assert r_err.status_code == 400
    err_text = r_err.text
    assert "Traceback" not in err_text
    assert "C:\\" not in err_text
    assert "/app/" not in err_text