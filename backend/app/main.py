import logging
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.formparsers import MultiPartParser

from app.config import ensure_isolated_temp_dir, settings
from app.gemini_service import analyze_with_gemini, validate_image_confirmation
from app.parser_worker import run_isolated_parser
from app.redactor import redact_extracted_pages
from app.schemas import AnalyzeUploadResponse
from app.security import (
    RequestContextAndSecurityMiddleware,
    detect_file_type,
    enforce_streaming_body_limit,
    sweep_temp_dir_files,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

MultiPartParser.spool_max_size = settings.UPLOAD_SPOOL_THRESHOLD_BYTES
ensure_isolated_temp_dir()

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Civisterial API", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(RequestContextAndSecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail), "request_id": request_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid upload request.", "request_id": request_id},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occurred.", "request_id": request_id},
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "civisterial"}


@app.post("/api/analyze", response_model=AnalyzeUploadResponse)
@limiter.limit(settings.RATE_LIMIT_ANALYZE)
async def analyze_document(request: Request) -> AnalyzeUploadResponse:
    tmp_dir = ensure_isolated_temp_dir()
    before_tmp = {p.name for p in tmp_dir.iterdir()}
    uploaded_file: UploadFile | None = None

    try:
        await enforce_streaming_body_limit(
            request, max_bytes=settings.MAX_UPLOAD_BYTES + 65536
        )

        # Allow 1 file ('file') and 1 optional declaration field ('image_confirmation')
        form = await request.form(max_files=1, max_fields=2)
        items = list(form.multi_items())

        file_items = [val for name, val in items if name == "file" and hasattr(val, "read")]
        other_fields = {
            name: str(val) for name, val in items if name != "file" and not hasattr(val, "read")
        }

        if len(file_items) != 1 or any(k != "image_confirmation" for k in other_fields):
            raise HTTPException(
                status_code=400,
                detail="Upload exactly one file in 'file' and optional 'image_confirmation' field.",
            )

        uploaded_file = file_items[0]  # type: ignore[assignment]
        raw_bytes = await uploaded_file.read(settings.MAX_UPLOAD_BYTES + 1)

        if len(raw_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        if len(raw_bytes) > settings.MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Uploaded file exceeds the maximum allowed size.",
            )

        file_type = detect_file_type(raw_bytes[:16], uploaded_file.content_type)
        image_confirmation_raw = other_fields.get("image_confirmation")

        # Initial parse checks structure and page types before deciding whether image bytes may be extracted
        parsed = await run_isolated_parser(
            raw_bytes=raw_bytes,
            file_type=file_type,
            request=request,
            extract_image_page_bytes=False,
        )

        has_image_content = bool(parsed["has_image_based_content"])
        image_confirmed = validate_image_confirmation(
            has_image_content=has_image_content,
            image_confirmation_raw=image_confirmation_raw,
        )

        # If image content is present and explicitly confirmed as public/synthetic, extract image bytes
        if has_image_content and image_confirmed:
            parsed = await run_isolated_parser(
                raw_bytes=raw_bytes,
                file_type=file_type,
                request=request,
                extract_image_page_bytes=True,
            )

        safe_pages = redact_extracted_pages(parsed["pages"])
        # Preserve confirmed image_bytes in memory for Gemini inline parts only (never serialized in response)
        for idx, page_dict in enumerate(safe_pages):
            if parsed["pages"][idx].get("image_bytes"):
                page_dict["image_bytes"] = parsed["pages"][idx]["image_bytes"]
                page_dict["image_mime_type"] = parsed["pages"][idx].get("image_mime_type")

        analysis = await analyze_with_gemini(
            redacted_pages=safe_pages,
            has_image_content=has_image_content,
            image_confirmed=image_confirmed,
        )

        request_id = getattr(request.state, "request_id", "unknown")
        return AnalyzeUploadResponse(
            request_id=request_id,
            file_type=parsed["file_type"],
            page_count=parsed["page_count"],
            has_image_based_content=has_image_content,
            image_confirmation_provided=image_confirmed,
            pages=safe_pages,
            analysis=analysis,
        )
    finally:
        if uploaded_file is not None:
            try:
                await uploaded_file.close()
            except Exception:
                pass
        sweep_temp_dir_files(before_tmp)