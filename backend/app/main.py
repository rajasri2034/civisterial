import asyncio
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
from app.gemini_service import (
    analyze_with_gemini,
    validate_image_confirmation,
    validate_language_selection,
)
from app.languages import SUPPORTED_LANGUAGES, detect_document_language
from app.parser_worker import run_isolated_parser
from app.redactor import redact_extracted_pages
from app.schemas import (
    AnalyzeUploadResponse,
    InspectUploadResponse,
    VerifiedDocumentAnalysis,
)
from app.security import (
    RequestContextAndSecurityMiddleware,
    detect_file_type,
    enforce_streaming_body_limit,
    sweep_temp_dir_files,
)
from app.verification_engine import verify_analysis_items

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


@app.get("/api/languages")
async def list_languages() -> dict[str, object]:
    return {"languages": SUPPORTED_LANGUAGES}


async def _run_with_disconnect_guard(request: Request, coro):
    """Run an async pipeline and immediately cancel it if the client aborts the connection."""
    work_task = asyncio.create_task(coro)

    async def _watch_disconnect() -> None:
        while not work_task.done():
            if await request.is_disconnected():
                work_task.cancel()
                return
            await asyncio.sleep(0.05)

    watcher = asyncio.create_task(_watch_disconnect())
    try:
        return await work_task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Request cancelled by client.")
    finally:
        watcher.cancel()
        try:
            await watcher
        except asyncio.CancelledError:
            pass


@app.post("/api/inspect", response_model=InspectUploadResponse)
@limiter.limit(settings.RATE_LIMIT_ANALYZE)
async def inspect_document(request: Request) -> InspectUploadResponse:
    tmp_dir = ensure_isolated_temp_dir()
    before_tmp = {p.name for p in tmp_dir.iterdir()}
    uploaded_file: UploadFile | None = None

    try:
        await enforce_streaming_body_limit(
            request, max_bytes=settings.MAX_UPLOAD_BYTES + 65536
        )

        form = await request.form(max_files=1, max_fields=1)
        items = list(form.multi_items())
        if len(items) != 1 or items[0][0] != "file" or not hasattr(items[0][1], "read"):
            raise HTTPException(
                status_code=400,
                detail="Upload exactly one file in the 'file' field.",
            )

        uploaded_file = items[0][1]  # type: ignore[assignment]
        raw_bytes = await uploaded_file.read(settings.MAX_UPLOAD_BYTES + 1)

        if len(raw_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        if len(raw_bytes) > settings.MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Uploaded file exceeds the maximum allowed size.",
            )

        file_type = detect_file_type(raw_bytes[:16], uploaded_file.content_type)
        parsed = await run_isolated_parser(
            raw_bytes=raw_bytes,
            file_type=file_type,
            request=request,
            extract_image_page_bytes=False,
        )

        safe_pages = redact_extracted_pages(parsed["pages"])
        combined_text = "\n".join(
            p["redacted_text"] for p in safe_pages if p.get("kind") == "text"
        )
        det_code, det_label, det_uncertain = detect_document_language(combined_text)

        request_id = getattr(request.state, "request_id", "unknown")
        return InspectUploadResponse(
            request_id=request_id,
            file_type=parsed["file_type"],
            page_count=parsed["page_count"],
            has_image_based_content=bool(parsed["has_image_based_content"]),
            requires_image_confirmation=bool(parsed["requires_image_confirmation"]),
            detected_language_code=det_code,
            detected_language_label=det_label,
            language_detection_uncertain=det_uncertain,
            pages=safe_pages,
        )
    finally:
        if uploaded_file is not None:
            try:
                await uploaded_file.close()
            except Exception:
                pass
        sweep_temp_dir_files(before_tmp)


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

        allowed_fields = {"image_confirmation", "document_language", "explanation_language"}
        form = await request.form(max_files=1, max_fields=4)
        items = list(form.multi_items())

        file_items = [val for name, val in items if name == "file" and hasattr(val, "read")]
        other_fields = {
            name: str(val) for name, val in items if name != "file" and not hasattr(val, "read")
        }

        if len(file_items) != 1 or any(k not in allowed_fields for k in other_fields):
            raise HTTPException(
                status_code=400,
                detail="Invalid upload fields provided.",
            )

        document_language = other_fields.get("document_language", "auto").strip() or "auto"
        explanation_language = other_fields.get("explanation_language", "en").strip() or "en"

        _, _, explanation_direction = validate_language_selection(
            document_language=document_language,
            explanation_language=explanation_language,
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

        async def _execute_pipeline() -> AnalyzeUploadResponse:
            parsed = await run_isolated_parser(
                raw_bytes=raw_bytes,
                file_type=file_type,
                request=request,
                extract_image_page_bytes=bool(
                    image_confirmation_raw and image_confirmation_raw.strip()
                ),
            )

            has_image_content = bool(parsed["has_image_based_content"])
            image_confirmed = validate_image_confirmation(
                has_image_content=has_image_content,
                image_confirmation_raw=image_confirmation_raw,
            )

            safe_pages = redact_extracted_pages(parsed["pages"])
            for idx, page_dict in enumerate(safe_pages):
                if parsed["pages"][idx].get("image_bytes"):
                    page_dict["image_bytes"] = parsed["pages"][idx]["image_bytes"]
                    page_dict["image_mime_type"] = parsed["pages"][idx].get("image_mime_type")

            combined_text = "\n".join(
                p["redacted_text"] for p in safe_pages if p.get("kind") == "text"
            )
            det_code, det_label, det_uncertain = detect_document_language(combined_text)

            resolved_doc_lang = (
                det_code if document_language.lower() == "auto" else document_language.lower()
            )

            raw_analysis = await analyze_with_gemini(
                redacted_pages=safe_pages,
                has_image_content=has_image_content,
                image_confirmed=image_confirmed,
                document_language=document_language,
                explanation_language=explanation_language,
            )

            verified_dict = verify_analysis_items(
                raw_analysis.model_dump(),
                redacted_pages=safe_pages,
                has_image_content=has_image_content,
                lang=resolved_doc_lang,
            )
            verified_analysis = VerifiedDocumentAnalysis.model_validate(verified_dict)

            request_id = getattr(request.state, "request_id", "unknown")
            return AnalyzeUploadResponse(
                request_id=request_id,
                file_type=parsed["file_type"],
                page_count=parsed["page_count"],
                has_image_based_content=has_image_content,
                image_confirmation_provided=image_confirmed,
                detected_language_code=det_code,
                detected_language_label=det_label,
                language_detection_uncertain=det_uncertain,
                document_language=resolved_doc_lang,
                explanation_language=explanation_language.lower(),
                explanation_direction=explanation_direction,  # type: ignore[arg-type]
                pages=safe_pages,
                analysis=verified_analysis,
            )

        return await _run_with_disconnect_guard(request, _execute_pipeline())
    finally:
        if uploaded_file is not None:
            try:
                await uploaded_file.close()
            except Exception:
                pass
        sweep_temp_dir_files(before_tmp)