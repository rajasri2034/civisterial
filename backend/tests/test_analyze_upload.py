import asyncio
import io
import logging
import multiprocessing as mp
import time

import fitz  # PyMuPDF
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from starlette.requests import Request

from app import main as main_module
from app import parser_worker
from app.config import ensure_isolated_temp_dir, settings
from app.main import app, limiter
from app.parser_worker import run_isolated_parser


def _make_text_pdf(pages_text: list[str]) -> bytes:
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        if text:
            page.insert_textbox(fitz.Rect(50, 50, 540, 750), text)
    data = doc.tobytes()
    doc.close()
    return data


def _make_png(width: int = 32, height: int = 32) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=(11, 31, 58))
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_mixed_pdf() -> bytes:
    doc = fitz.open()
    # Page 1: text page
    p1 = doc.new_page()
    p1.insert_textbox(
        fitz.Rect(50, 50, 540, 200),
        "Official Council Tax Notice: Payment due within 14 days.",
    )

    # Page 2: scanned/image-based page (embedded PNG, no selectable text)
    p2 = doc.new_page()
    png_bytes = _make_png(64, 64)
    p2.insert_image(fitz.Rect(50, 50, 200, 200), stream=png_bytes)

    # Page 3: empty page
    doc.new_page()

    data = doc.tobytes()
    doc.close()
    return data


def _make_encrypted_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(50, 50, 540, 200), "Confidential protected text")
    data = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner123",
        user_pw="user123",
    )
    doc.close()
    return data


def _slow_worker(raw_bytes: bytes, file_type: str, cfg, result_queue: mp.Queue) -> None:
    time.sleep(5.0)
    result_queue.put({"ok": True})


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter.reset()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def test_valid_pdf_upload(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "MOCK_MODE", True)
    pdf_bytes = _make_text_pdf(["Your housing benefit renewal requires proof of address."])
    res = client.post(
        "/api/analyze",
        files={"file": ("notice.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["file_type"] == "pdf"
    assert body["page_count"] == 1
    assert body["has_image_based_content"] is False
    assert body["image_confirmation_provided"] is False
    assert body["pages"][0]["kind"] == "text"
    assert "proof of address" in body["pages"][0]["text"]
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["Cache-Control"] == "no-store"
    assert res.headers["Referrer-Policy"] == "no-referrer"


def test_valid_png_upload_requires_confirmation_without_sending(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "MOCK_MODE", True)
    png_bytes = _make_png()
    res = client.post(
        "/api/analyze",
        files={"file": ("letter.png", png_bytes, "image/png")},
        data={"image_confirmation": "I confirm this is a public or synthetic document"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["file_type"] == "png"
    assert body["page_count"] == 1
    assert body["has_image_based_content"] is True
    assert body["image_confirmation_provided"] is True
    assert body["pages"][0]["kind"] == "image_based"
    assert body["pages"][0]["text"] == ""


def test_renamed_exe_rejected(client: TestClient):
    mz_exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff" + b"\x00" * 128
    res = client.post(
        "/api/analyze",
        files={"file": ("payload.pdf", mz_exe_bytes, "application/pdf")},
    )
    assert res.status_code == 400
    assert "signature" in res.json()["error"].lower()


def test_fake_pdf_header_with_garbage_body_rejected(client: TestClient):
    fake_pdf = b"%PDF-1.7\nThis is completely corrupted non-PDF garbage bytes \x00\xff\xfe"
    res = client.post(
        "/api/analyze",
        files={"file": ("corrupt.pdf", fake_pdf, "application/pdf")},
    )
    assert res.status_code == 400
    assert "unable to process" in res.json()["error"].lower()


def test_oversized_file_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 1024)
    big_pdf = b"%PDF-1.4\n" + (b"A" * 2048)
    res = client.post(
        "/api/analyze",
        files={"file": ("large.pdf", big_pdf, "application/pdf")},
    )
    assert res.status_code == 413


def test_too_many_pages_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "MAX_PDF_PAGES", 2)
    three_page_pdf = _make_text_pdf(["Page one text", "Page two text", "Page three text"])
    res = client.post(
        "/api/analyze",
        files={"file": ("many.pdf", three_page_pdf, "application/pdf")},
    )
    assert res.status_code == 400
    assert "maximum limit" in res.json()["error"].lower()


def test_encrypted_pdf_rejected(client: TestClient):
    enc_pdf = _make_encrypted_pdf()
    res = client.post(
        "/api/analyze",
        files={"file": ("secret.pdf", enc_pdf, "application/pdf")},
    )
    assert res.status_code == 400
    assert "encrypted" in res.json()["error"].lower()


def test_zero_byte_file_rejected(client: TestClient):
    res = client.post(
        "/api/analyze",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert res.status_code == 400
    assert "empty" in res.json()["error"].lower()


def test_mixed_text_and_image_based_pdf(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "MOCK_MODE", True)
    mixed_pdf = _make_mixed_pdf()
    res = client.post(
        "/api/analyze",
        files={"file": ("mixed.pdf", mixed_pdf, "application/pdf")},
        data={"image_confirmation": "I confirm this is a public or synthetic document"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["page_count"] == 3
    assert body["has_image_based_content"] is True
    assert body["image_confirmation_provided"] is True
    assert body["pages"][0]["kind"] == "text"
    assert body["pages"][1]["kind"] == "image_based"
    assert body["pages"][2]["kind"] == "empty"
    assert "not been text-verified" in body["pages"][1]["notice"].lower()


def test_temp_file_creation_check(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "MOCK_MODE", True)
    tmp_dir = ensure_isolated_temp_dir()
    before = {p.name for p in tmp_dir.iterdir()}

    # Small upload below UPLOAD_SPOOL_THRESHOLD_BYTES stays in memory (no temp file left on disk)
    pdf_bytes = _make_text_pdf(["In-memory spool threshold verification document."])
    res = client.post(
        "/api/analyze",
        files={"file": ("spool_check.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 200
    after = {p.name for p in tmp_dir.iterdir()}
    assert after == before


def test_temp_file_cleanup_after_forced_exception(monkeypatch: pytest.MonkeyPatch):
    tmp_dir = ensure_isolated_temp_dir()
    # Force Starlette MultipartParser to spool to disk by lowering threshold to 10 bytes
    monkeypatch.setattr(main_module.MultiPartParser, "spool_max_size", 10)

    async def boom_parser(*args, **kwargs):
        # Verify a spooled temp file actually appeared inside tmp_dir during parsing
        assert len(list(tmp_dir.iterdir())) >= 1
        raise RuntimeError("Simulated parser crash")

    monkeypatch.setattr(main_module, "run_isolated_parser", boom_parser)

    pdf_bytes = _make_text_pdf(["Document triggering forced exception after disk spool."])
    no_raise_client = TestClient(app, raise_server_exceptions=False)
    res = no_raise_client.post(
        "/api/analyze",
        files={"file": ("crash.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 500
    assert "unexpected error" in res.json()["error"].lower()
    # Confirm finally-block cleaned up the spooled temp file
    assert list(tmp_dir.iterdir()) == []


def test_worker_timeout_kills_process(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "PARSE_TIMEOUT_SECONDS", 0.15)
    orig_run = parser_worker.run_isolated_parser

    async def patched_run(
        raw_bytes,
        file_type,
        request,
        timeout_seconds=None,
        worker_target=None,
        extract_image_page_bytes=False,
    ):
        return await orig_run(
            raw_bytes,
            file_type,
            request,
            timeout_seconds=0.15,
            worker_target=_slow_worker,
            extract_image_page_bytes=extract_image_page_bytes,
        )

    monkeypatch.setattr(main_module, "run_isolated_parser", patched_run)

    pdf_bytes = _make_text_pdf(["Timeout test document content."])
    res = client.post(
        "/api/analyze",
        files={"file": ("slow.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 504
    assert "timed out" in res.json()["error"].lower()


def test_worker_kill_on_client_cancellation():
    async def _run():
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/analyze",
            "headers": [],
        }

        async def receive():
            return {"type": "http.disconnect"}

        req = Request(scope, receive=receive)
        with pytest.raises(Exception) as exc_info:
            await run_isolated_parser(
                raw_bytes=b"%PDF-1.4\n",
                file_type="pdf",
                request=req,
                timeout_seconds=10.0,
                worker_target=_slow_worker,
            )
        assert getattr(exc_info.value, "status_code", None) == 499

    asyncio.run(_run())


def test_document_text_never_appears_in_logs(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "MOCK_MODE", True)
    secret_phrase = "SUPER_SENSITIVE_CITIZEN_ACCOUNT_99887766"
    pdf_bytes = _make_text_pdf([f"Confidential notice containing {secret_phrase}"])

    with caplog.at_level(logging.INFO):
        res = client.post(
            "/api/analyze",
            files={"file": ("private.pdf", pdf_bytes, "application/pdf")},
        )

    assert res.status_code == 200
    assert secret_phrase not in caplog.text
    assert "request_id=" in caplog.text
    assert "route=/api/analyze" in caplog.text