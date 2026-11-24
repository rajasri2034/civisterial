import logging
import os
import stat
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import ensure_isolated_temp_dir

logger = logging.getLogger("civisterial.access")

PDF_MAGIC = b"%PDF-"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
}


def detect_file_type(header: bytes, content_type: str | None) -> str:
    """Validate both declared MIME type and leading magic bytes."""
    normalized_mime = (content_type or "").split(";")[0].strip().lower()
    if normalized_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Upload a PDF, PNG, or JPEG document.",
        )

    if normalized_mime == "application/pdf" and header.startswith(PDF_MAGIC):
        return "pdf"
    if normalized_mime == "image/png" and header.startswith(PNG_MAGIC):
        return "png"
    if normalized_mime == "image/jpeg" and header.startswith(JPEG_MAGIC):
        return "jpeg"

    raise HTTPException(
        status_code=400,
        detail="File signature does not match an allowed PDF, PNG, or JPEG format.",
    )


async def enforce_streaming_body_limit(request: Request, max_bytes: int) -> None:
    """Reject oversized requests via Content-Length and while streaming chunks."""
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared = int(content_length)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request headers.")
        if declared > max_bytes:
            raise HTTPException(
                status_code=413,
                detail="Uploaded file exceeds the maximum allowed size.",
            )

    buffered = bytearray()
    async for chunk in request.stream():
        buffered.extend(chunk)
        if len(buffered) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail="Uploaded file exceeds the maximum allowed size.",
            )

    # Cache buffered body on Request so Starlette's request.form() can parse it
    request._body = bytes(buffered)
    request._stream_consumed = False


@contextmanager
def isolated_secure_tempfile(suffix: str = ".bin") -> Generator[Path, None, None]:
    """Create a random 0600 temp file inside the isolated dir and delete in finally."""
    tmp_dir = ensure_isolated_temp_dir()
    fd, raw_path = tempfile.mkstemp(prefix="civ_", suffix=suffix, dir=str(tmp_dir))
    path = Path(raw_path)
    try:
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        os.close(fd)
        yield path
    finally:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass


def sweep_temp_dir_files(before_snapshot: set[str]) -> list[str]:
    """Remove any new temp files created during request handling and return their names."""
    tmp_dir = ensure_isolated_temp_dir()
    created: list[str] = []
    for entry in tmp_dir.iterdir():
        if entry.name not in before_snapshot:
            created.append(entry.name)
            try:
                if entry.is_file():
                    entry.unlink()
            except OSError:
                pass
    return created


class RequestContextAndSecurityMiddleware(BaseHTTPMiddleware):
    """Assigns request_id, sets security headers, and logs metadata only (never document text)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"

        logger.info(
            "request_id=%s method=%s route=%s status=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response