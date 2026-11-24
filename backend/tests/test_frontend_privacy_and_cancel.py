import asyncio
import re
from pathlib import Path

import httpx
import pymupdf
import pytest

from app import main as main_module
from app.config import ensure_isolated_temp_dir, settings
from app.main import app, limiter


def _make_sample_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Official administrative notice regarding housing grant renewal.")
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture(autouse=True)
def reset_state(monkeypatch: pytest.MonkeyPatch):
    limiter.reset()
    monkeypatch.setattr(settings, "MOCK_MODE", True)
    yield


@pytest.mark.anyio
async def test_backend_cancels_work_and_leaves_no_temp_files_on_client_abort(
    monkeypatch: pytest.MonkeyPatch,
):
    tmp_dir = ensure_isolated_temp_dir()
    before_files = set(tmp_dir.iterdir())
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def _slow_gemini(*args, **kwargs):
        started.set()
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    monkeypatch.setattr(main_module, "analyze_with_gemini", _slow_gemini)

    pdf_bytes = _make_sample_pdf()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        req_task = asyncio.create_task(
            client.post(
                "/api/analyze",
                files={"file": ("cancel_me.pdf", pdf_bytes, "application/pdf")},
            )
        )
        await asyncio.wait_for(started.wait(), timeout=3.0)
        # Abort the client request mid-flight (simulating AbortController.abort())
        req_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await req_task

    # Give event loop a brief tick to finalize cleanup
    await asyncio.sleep(0.1)
    after_files = set(tmp_dir.iterdir())
    assert after_files == before_files


def test_frontend_forbids_storage_cookies_analytics_and_secrets():
    repo_root = Path(__file__).resolve().parents[2]
    frontend_src = repo_root / "frontend" / "src"
    frontend_html = repo_root / "frontend" / "index.html"

    forbidden_patterns = [
        (r"\blocalStorage\b", "localStorage is forbidden"),
        (r"\bsessionStorage\b", "sessionStorage is forbidden"),
        (r"\bdocument\.cookie\b", "document.cookie is forbidden"),
        (r"google-analytics\.com|googletagmanager\.com|\bgtag\s*\(|\bplausible\.io|\bmixpanel\b|\bsegment\.com", "analytics scripts are forbidden"),
        (r"AIza[0-9A-Za-z\-_]{20,}", "Google API keys must never appear in the frontend"),
    ]

    files_to_scan = [frontend_html] + [
        p for p in frontend_src.rglob("*") if p.suffix in {".js", ".jsx", ".ts", ".tsx", ".html"}
    ]
    assert len(files_to_scan) > 1

    for file_path in files_to_scan:
        content = file_path.read_text(encoding="utf-8")
        for pattern, reason in forbidden_patterns:
            match = re.search(pattern, content)
            assert match is None, f"{reason}: found '{match.group(0)}' in {file_path}"