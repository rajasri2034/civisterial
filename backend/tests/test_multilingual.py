import os
import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.languages import detect_document_language
from app.main import app, limiter


def _make_unicode_pdf(text: str) -> bytes:
    """Create a PDF with embedded UTF-8 ToUnicode font mappings for Indic & RTL scripts."""
    doc = pymupdf.open()
    page = doc.new_page()
    rect = pymupdf.Rect(50, 50, 540, 750)

    # Use Windows Unicode fonts (Nirmala UI for Indic scripts, Segoe UI for Arabic/Urdu/Latin) if present
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