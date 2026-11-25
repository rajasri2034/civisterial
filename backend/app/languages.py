import re
from typing import Literal, TypedDict

LanguageTier = Literal["validated", "experimental"]
TextDirection = Literal["ltr", "rtl"]


class LanguageEntry(TypedDict):
    code: str
    name: str
    native_name: str
    tier: LanguageTier
    direction: TextDirection
    supports_document_input: bool
    supports_explanation_output: bool
    badge_label: str
    notes: str


# Comprehensive BCP-47 allow-list of Gemini-supported languages
SUPPORTED_LANGUAGES: list[LanguageEntry] = [
    # --- Tier 1: Validated (calibrated Part A + Part B lexical claim checks) ---
    {
        "code": "en",
        "name": "English",
        "native_name": "English",
        "tier": "validated",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Verified check",
        "notes": "Full automated quote verification and calibrated deadline/mandatory claim checks.",
    },
    {
        "code": "ta",
        "name": "Tamil",
        "native_name": "தமிழ்",
        "tier": "validated",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Verified check",
        "notes": "Full automated quote verification and calibrated Tamil deadline/mandatory claim checks.",
    },
    {
        "code": "hi",
        "name": "Hindi",
        "native_name": "हिन्दी",
        "tier": "validated",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Verified check",
        "notes": "Full automated quote verification and calibrated Hindi deadline/mandatory claim checks.",
    },
    # --- Tier 2: Experimental (Part A exact quote verification; manual review for Part B claims) ---
    {
        "code": "bn",
        "name": "Bengali",
        "native_name": "বাংলা",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Beta translation",
        "notes": "Exact quote verification enabled; manually review deadlines and mandatory terms.",
    },
    {
        "code": "te",
        "name": "Telugu",
        "native_name": "తెలుగు",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Beta translation",
        "notes": "Exact quote verification enabled; manually review deadlines and mandatory terms.",
    },
    {
        "code": "mr",
        "name": "Marathi",
        "native_name": "मराठी",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Beta translation",
        "notes": "Exact quote verification enabled; manually review deadlines and mandatory terms.",
    },
    {
        "code": "kn",
        "name": "Kannada",
        "native_name": "ಕನ್ನಡ",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Beta translation",
        "notes": "Exact quote verification enabled; manually review deadlines and mandatory terms.",
    },
    {
        "code": "ml",
        "name": "Malayalam",
        "native_name": "മലയാളം",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Beta translation",
        "notes": "Exact quote verification enabled; manually review deadlines and mandatory terms.",
    },
    {
        "code": "gu",
        "name": "Gujarati",
        "native_name": "ગુજરાતી",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Beta translation",
        "notes": "Exact quote verification enabled; manually review deadlines and mandatory terms.",
    },
    {
        "code": "pa",
        "name": "Punjabi",
        "native_name": "ਪੰਜਾਬੀ",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Beta translation",
        "notes": "Exact quote verification enabled; manually review deadlines and mandatory terms.",
    },
    {
        "code": "ur",
        "name": "Urdu",
        "native_name": "اردو",
        "tier": "experimental",
        "direction": "rtl",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Beta translation",
        "notes": "RTL script supported; exact quote verification enabled, manually review deadlines.",
    },
    {
        "code": "ar",
        "name": "Arabic",
        "native_name": "العربية",
        "tier": "experimental",
        "direction": "rtl",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Beta translation",
        "notes": "RTL script supported; exact quote verification enabled, manually review deadlines.",
    },
    {
        "code": "fr",
        "name": "French",
        "native_name": "Français",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Beta translation",
        "notes": "Exact quote verification enabled; manually review deadlines and mandatory terms.",
    },
    {
        "code": "es",
        "name": "Spanish",
        "native_name": "Español",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Beta translation",
        "notes": "Exact quote verification enabled; manually review deadlines and mandatory terms.",
    },
    {
        "code": "de",
        "name": "German",
        "native_name": "Deutsch",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Beta translation",
        "notes": "Exact quote verification enabled; manually review deadlines and mandatory terms.",
    },
    {
        "code": "pt",
        "name": "Portuguese",
        "native_name": "Português",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Beta translation",
        "notes": "Exact quote verification enabled; manually review deadlines and mandatory terms.",
    },
    {
        "code": "ja",
        "name": "Japanese",
        "native_name": "日本語",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Beta translation",
        "notes": "Exact quote verification enabled; manually review deadlines and mandatory terms.",
    },
    {
        "code": "ko",
        "name": "Korean",
        "native_name": "한국어",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Beta translation",
        "notes": "Exact quote verification enabled; manually review deadlines and mandatory terms.",
    },
    {
        "code": "zh",
        "name": "Chinese (Simplified)",
        "native_name": "简体中文",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "badge_label": "Beta translation",
        "notes": "Exact quote verification enabled; manually review deadlines and mandatory terms.",
    },
]

# Additional Gemini-supported BCP-47 primary tags accepted via validated BCP-47 format
ADDITIONAL_GEMINI_BCP47_TAGS: dict[str, tuple[str, TextDirection]] = {
    "as": ("Assamese", "ltr"),
    "or": ("Odia", "ltr"),
    "ne": ("Nepali", "ltr"),
    "si": ("Sinhala", "ltr"),
    "it": ("Italian", "ltr"),
    "nl": ("Dutch", "ltr"),
    "pl": ("Polish", "ltr"),
    "ru": ("Russian", "ltr"),
    "uk": ("Ukrainian", "ltr"),
    "tr": ("Turkish", "ltr"),
    "vi": ("Vietnamese", "ltr"),
    "th": ("Thai", "ltr"),
    "id": ("Indonesian", "ltr"),
    "ms": ("Malay", "ltr"),
    "sw": ("Swahili", "ltr"),
    "fa": ("Persian", "rtl"),
    "he": ("Hebrew", "rtl"),
}

_BCP47_PATTERN = re.compile(r"^[a-z]{2,3}(?:-[a-z]{4})?(?:-(?:[a-z]{2}|\d{3}))?$", re.IGNORECASE)
_LANGUAGE_MAP: dict[str, LanguageEntry] = {
    entry["code"].lower(): entry for entry in SUPPORTED_LANGUAGES
}
VALIDATED_LANGUAGE_CODES: frozenset[str] = frozenset(
    entry["code"] for entry in SUPPORTED_LANGUAGES if entry["tier"] == "validated"
)


def normalize_bcp47_code(code: str) -> str:
    return (code or "").strip().lower().replace("_", "-")


def get_language_entry(code: str) -> LanguageEntry | None:
    """Resolve a BCP-47 language code against the allow-list (supporting regional subtags like en-GB, fr-CA)."""
    norm = normalize_bcp47_code(code)
    if not norm or not _BCP47_PATTERN.match(norm):
        return None

    if norm in _LANGUAGE_MAP:
        return _LANGUAGE_MAP[norm]

    primary = norm.split("-", 1)[0]
    if primary in _LANGUAGE_MAP:
        base = _LANGUAGE_MAP[primary]
        return {
            **base,
            "code": norm,
        }

    if primary in ADDITIONAL_GEMINI_BCP47_TAGS:
        name, direction = ADDITIONAL_GEMINI_BCP47_TAGS[primary]
        return {
            "code": norm,
            "name": name,
            "native_name": name,
            "tier": "experimental",
            "direction": direction,
            "supports_document_input": True,
            "supports_explanation_output": True,
            "badge_label": "Beta translation",
            "notes": "Exact quote verification enabled; manually review deadlines and mandatory terms.",
        }

    return None


def is_validated_language(code: str) -> bool:
    entry = get_language_entry(code)
    return bool(entry and entry["tier"] == "validated")


# Unicode block ranges for fast, deterministic script detection
_SCRIPT_RANGES: list[tuple[str, str, int, int]] = [
    ("ta", "Tamil (தமிழ்)", 0x0B80, 0x0BFF),
    ("hi", "Devanagari / Hindi (हिन्दी)", 0x0900, 0x097F),
    ("bn", "Bengali (বাংলা)", 0x0980, 0x09FF),
    ("te", "Telugu (తెలుగు)", 0x0C00, 0x0C7F),
    ("kn", "Kannada (ಕನ್ನಡ)", 0x0C80, 0x0CFF),
    ("ml", "Malayalam (മലയാളം)", 0x0D00, 0x0D7F),
    ("gu", "Gujarati (ગુજરાતી)", 0x0A80, 0x0AFF),
    ("pa", "Gurmukhi / Punjabi (ਪੰਜਾਬੀ)", 0x0A00, 0x0A7F),
    ("ar", "Arabic / Urdu script", 0x0600, 0x06FF),
    ("ja", "Japanese", 0x3040, 0x30FF),
    ("ko", "Korean", 0xAC00, 0xD7AF),
    ("zh", "Chinese", 0x4E00, 0x9FFF),
]

_FRENCH_MARKERS = {"le", "la", "les", "des", "aux", "dans", "pour", "avec", "demande", "formulaire", "date", "limite"}
_SPANISH_MARKERS = {"el", "los", "las", "para", "con", "solicitud", "formulario", "fecha", "plazo", "debe"}
_GERMAN_MARKERS = {"der", "die", "das", "und", "für", "antrag", "formular", "frist", "muss", "bitte"}


def detect_document_language(text: str) -> tuple[str, str, bool]:
    """Detect primary language from extracted document text using Unicode script analysis."""
    cleaned = (text or "").strip()
    if not cleaned:
        return ("unknown", "Unknown (no readable text)", True)

    script_counts: dict[str, int] = {}
    latin_count = 0

    for ch in cleaned:
        cp = ord(ch)
        if (0x0041 <= cp <= 0x005A) or (0x0061 <= cp <= 0x007A) or (0x00C0 <= cp <= 0x024F):
            latin_count += 1
            continue
        for code, _, start, end in _SCRIPT_RANGES:
            if start <= cp <= end:
                script_counts[code] = script_counts.get(code, 0) + 1
                break

    total_alpha = latin_count + sum(script_counts.values())
    if total_alpha < 10:
        if script_counts:
            top_code = max(script_counts, key=lambda k: script_counts[k])
            entry = _LANGUAGE_MAP.get(top_code)
            label = f"{entry['name']} ({entry['native_name']})" if entry else top_code
            return (top_code, label, True)
        if latin_count > 0:
            return ("en", "English (English)", True)
        return ("unknown", "Unknown", True)

    candidates: list[tuple[str, int]] = []
    if latin_count > 0:
        words = set(re.findall(r"[a-zà-ÿ]{2,}", cleaned.lower()))
        if len(words & _FRENCH_MARKERS) >= 2:
            candidates.append(("fr", latin_count))
        elif len(words & _SPANISH_MARKERS) >= 2:
            candidates.append(("es", latin_count))
        elif len(words & _GERMAN_MARKERS) >= 2:
            candidates.append(("de", latin_count))
        else:
            candidates.append(("en", latin_count))
    for code, cnt in script_counts.items():
        candidates.append((code, cnt))

    candidates.sort(key=lambda item: item[1], reverse=True)
    primary_code, primary_count = candidates[0]
    primary_entry = _LANGUAGE_MAP.get(primary_code)
    primary_label = (
        f"{primary_entry['name']} ({primary_entry['native_name']})"
        if primary_entry
        else primary_code
    )

    if len(candidates) > 1 and candidates[1][1] >= 12 and candidates[1][1] / max(primary_count, 1) >= 0.15:
        second_code = candidates[1][0]
        second_entry = _LANGUAGE_MAP.get(second_code)
        second_label = second_entry["name"] if second_entry else second_code
        return (primary_code, f"Multilingual ({primary_label} + {second_label})", False)

    return (primary_code, primary_label, False)