import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    MOCK_MODE: bool = os.getenv("MOCK_MODE", "false").strip().lower() in ("1", "true", "yes")
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
    MAX_PDF_PAGES: int = int(os.getenv("MAX_PDF_PAGES", "30"))
    MAX_IMAGE_PIXELS: int = int(os.getenv("MAX_IMAGE_PIXELS", "25000000"))
    PARSE_TIMEOUT_SECONDS: float = float(os.getenv("PARSE_TIMEOUT_SECONDS", "30"))
    GEMINI_TIMEOUT_SECONDS: float = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "30"))
    WORKER_CPU_SECONDS: int = int(os.getenv("WORKER_CPU_SECONDS", "20"))
    WORKER_MEMORY_MB: int = int(os.getenv("WORKER_MEMORY_MB", "512"))
    UPLOAD_SPOOL_THRESHOLD_BYTES: int = int(
        os.getenv("UPLOAD_SPOOL_THRESHOLD_BYTES", str(10 * 1024 * 1024))
    )
    RATE_LIMIT_ANALYZE: str = os.getenv("RATE_LIMIT_ANALYZE", "10/minute")
    ISOLATED_TMP_DIR: Path = Path(
        os.getenv(
            "CIVISTERIAL_TMP_DIR",
            str(Path(tempfile.gettempdir()) / "civisterial_isolated_tmp"),
        )
    )


settings = Settings()


def ensure_isolated_temp_dir() -> Path:
    """Create and lock down the isolated temp directory (0700 where supported)."""
    tmp_path = settings.ISOLATED_TMP_DIR
    tmp_path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(tmp_path, 0o700)
    except OSError:
        pass
    tempfile.tempdir = str(tmp_path)
    return tmp_path