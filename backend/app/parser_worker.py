import asyncio
import io
import multiprocessing as mp
import queue
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request

from app.config import settings


@dataclass
class ParseConfig:
    max_pdf_pages: int
    max_image_pixels: int
    cpu_seconds: int
    memory_mb: int
    extract_image_page_bytes: bool = False


def _apply_worker_resource_limits(cpu_seconds: int, memory_mb: int) -> None:
    """Apply OS CPU and address-space limits on POSIX platforms."""
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        mem_bytes = memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    except (ImportError, ValueError, OSError):
        pass


def _pdf_has_embedded_files_or_js(doc: Any) -> bool:
    """Inspect PDF catalog, names tree, and page annotations for JavaScript or embedded files."""
    try:
        if doc.embfile_count() > 0:
            return True
    except Exception:
        return True

    try:
        trailer = doc.pdf_trailer() or ""
        if "/JavaScript" in trailer or "/JS" in trailer or "/EmbeddedFiles" in trailer:
            return True
    except Exception:
        pass

    xref_len = doc.xref_length()
    for xref in range(1, xref_len):
        try:
            obj_str = doc.xref_object(xref, compressed=False) or ""
            if (
                "/JavaScript" in obj_str
                or "/JS " in obj_str
                or "/JS(" in obj_str
                or "/JS<" in obj_str
                or "/EmbeddedFile" in obj_str
                or "/EmbeddedFiles" in obj_str
            ):
                return True
        except Exception:
            continue

    for page in doc:
        try:
            for annot in page.annots() or []:
                info = annot.info or {}
                if info.get("content") and "/JS" in str(info):
                    return True
            for link in page.get_links() or []:
                uri = str(link.get("uri", "")).strip().lower()
                if uri.startswith("javascript:"):
                    return True
        except Exception:
            continue

    return False


def _worker_parse_entrypoint(
    raw_bytes: bytes,
    file_type: str,
    cfg: ParseConfig,
    result_queue: mp.Queue,
) -> None:
    """Isolated child-process entrypoint for PDF and image parsing."""
    _apply_worker_resource_limits(cfg.cpu_seconds, cfg.memory_mb)

    try:
        if file_type == "pdf":
            import pymupdf

            try:
                doc = pymupdf.open(stream=raw_bytes, filetype="pdf")
            except Exception:
                result_queue.put(
                    {"ok": False, "status": 400, "detail": "Unable to process the uploaded PDF file."}
                )
                return

            try:
                if doc.needs_pass or doc.is_encrypted:
                    result_queue.put(
                        {
                            "ok": False,
                            "status": 400,
                            "detail": "Encrypted or password-protected PDFs are not supported.",
                        }
                    )
                    return

                page_count = len(doc)
                if page_count == 0:
                    result_queue.put(
                        {
                            "ok": False,
                            "status": 400,
                            "detail": "Unable to process the uploaded PDF file.",
                        }
                    )
                    return

                if page_count > cfg.max_pdf_pages:
                    result_queue.put(
                        {
                            "ok": False,
                            "status": 400,
                            "detail": f"PDF exceeds the maximum limit of {cfg.max_pdf_pages} pages.",
                        }
                    )
                    return

                if _pdf_has_embedded_files_or_js(doc):
                    result_queue.put(
                        {
                            "ok": False,
                            "status": 400,
                            "detail": "PDF files containing active scripts or attachments are not allowed.",
                        }
                    )
                    return

                pages: list[dict[str, Any]] = []
                has_image_based = False

                for idx in range(page_count):
                    page = doc.load_page(idx)
                    extracted = (page.get_text("text") or "").strip()
                    images_on_page = page.get_images(full=False)

                    if len(extracted) >= 20:
                        pages.append(
                            {
                                "page_number": idx + 1,
                                "kind": "text",
                                "char_count": len(extracted),
                                "text": extracted,
                                "notice": None,
                            }
                        )
                    elif len(images_on_page) > 0:
                        has_image_based = True
                        rendered_png: bytes | None = None
                        if cfg.extract_image_page_bytes:
                            pix = page.get_pixmap(dpi=100)
                            rendered_png = pix.tobytes("png")
                        pages.append(
                            {
                                "page_number": idx + 1,
                                "kind": "image_based",
                                "char_count": len(extracted),
                                "text": "",
                                "image_bytes": rendered_png,
                                "image_mime_type": "image/png" if rendered_png else None,
                                "notice": (
                                    "Image-based page detected. Content has not been text-verified."
                                ),
                            }
                        )
                    else:
                        pages.append(
                            {
                                "page_number": idx + 1,
                                "kind": "empty",
                                "char_count": 0,
                                "text": "",
                                "notice": "No extractable text or image layer detected on this page.",
                            }
                        )

                result_queue.put(
                    {
                        "ok": True,
                        "file_type": "pdf",
                        "page_count": page_count,
                        "has_image_based_content": has_image_based,
                        "requires_image_confirmation": has_image_based,
                        "pages": pages,
                    }
                )
            finally:
                doc.close()

        elif file_type in ("png", "jpeg"):
            from PIL import Image

            Image.MAX_IMAGE_PIXELS = cfg.max_image_pixels
            try:
                with Image.open(io.BytesIO(raw_bytes)) as img:
                    expected_format = "PNG" if file_type == "png" else "JPEG"
                    if img.format != expected_format:
                        result_queue.put(
                            {
                                "ok": False,
                                "status": 400,
                                "detail": "Unable to process the uploaded image file.",
                            }
                        )
                        return
                    width, height = img.size
                    if width <= 0 or height <= 0 or (width * height) > cfg.max_image_pixels:
                        result_queue.put(
                            {
                                "ok": False,
                                "status": 400,
                                "detail": "Image dimensions exceed allowed limits.",
                            }
                        )
                        return
                    img.verify()

                with Image.open(io.BytesIO(raw_bytes)) as img_decode:
                    img_decode.load()
            except Image.DecompressionBombError:
                result_queue.put(
                    {
                        "ok": False,
                        "status": 400,
                        "detail": "Image dimensions exceed allowed limits.",
                    }
                )
                return
            except Exception:
                result_queue.put(
                    {
                        "ok": False,
                        "status": 400,
                        "detail": "Unable to process the uploaded image file.",
                    }
                )
                return

            mime_str = "image/png" if file_type == "png" else "image/jpeg"
            result_queue.put(
                {
                    "ok": True,
                    "file_type": file_type,
                    "page_count": 1,
                    "has_image_based_content": True,
                    "requires_image_confirmation": True,
                    "pages": [
                        {
                            "page_number": 1,
                            "kind": "image_based",
                            "char_count": 0,
                            "text": "",
                            "image_bytes": raw_bytes if cfg.extract_image_page_bytes else None,
                            "image_mime_type": mime_str if cfg.extract_image_page_bytes else None,
                            "notice": "Image upload validated locally.",
                        }
                    ],
                }
            )
        else:
            result_queue.put(
                {"ok": False, "status": 415, "detail": "Unsupported file type."}
            )
    except Exception:
        result_queue.put(
            {"ok": False, "status": 400, "detail": "Unable to process the uploaded file."}
        )


def _terminate_process(proc: mp.Process) -> None:
    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=1.0)
    if proc.is_alive():
        proc.kill()
        proc.join(timeout=1.0)


async def run_isolated_parser(
    raw_bytes: bytes,
    file_type: str,
    request: Request,
    timeout_seconds: float | None = None,
    worker_target: Any = None,
    extract_image_page_bytes: bool = False,
) -> dict[str, Any]:
    """Run parsing in a spawned worker process with hard timeout and disconnect cancellation."""
    effective_timeout = (
        timeout_seconds if timeout_seconds is not None else settings.PARSE_TIMEOUT_SECONDS
    )
    target = worker_target or _worker_parse_entrypoint
    ctx = mp.get_context("spawn")
    result_queue: mp.Queue = ctx.Queue(maxsize=1)
    cfg = ParseConfig(
        max_pdf_pages=settings.MAX_PDF_PAGES,
        max_image_pixels=settings.MAX_IMAGE_PIXELS,
        cpu_seconds=settings.WORKER_CPU_SECONDS,
        memory_mb=settings.WORKER_MEMORY_MB,
        extract_image_page_bytes=extract_image_page_bytes,
    )

    proc = ctx.Process(
        target=target,
        args=(raw_bytes, file_type, cfg, result_queue),
        daemon=True,
    )
    proc.start()

    loop = asyncio.get_running_loop()
    deadline = loop.time() + effective_timeout
    payload: dict[str, Any] | None = None

    try:
        # Drain queue while polling process so large PNG payloads never block pipe flush on Windows
        while True:
            if await request.is_disconnected():
                _terminate_process(proc)
                raise HTTPException(status_code=499, detail="Request cancelled.")

            try:
                payload = result_queue.get_nowait()
                break
            except queue.Empty:
                pass

            if not proc.is_alive():
                try:
                    payload = result_queue.get(timeout=0.2)
                except queue.Empty:
                    payload = None
                break

            if loop.time() >= deadline:
                _terminate_process(proc)
                raise HTTPException(
                    status_code=504,
                    detail="Document processing timed out.",
                )

            await asyncio.sleep(0.02)

        proc.join(timeout=0.5)

        if payload is None:
            raise HTTPException(
                status_code=400,
                detail="Unable to process the uploaded file.",
            )

        if not payload.get("ok"):
            raise HTTPException(
                status_code=payload.get("status", 400),
                detail=payload.get("detail", "Unable to process the uploaded file."),
            )

        return payload
    finally:
        _terminate_process(proc)
        try:
            result_queue.close()
        except Exception:
            pass
        