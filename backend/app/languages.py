from typing import Literal, TypedDict

LanguageTier = Literal["verified", "experimental", "unavailable"]
TextDirection = Literal["ltr", "rtl"]


class LanguageConfigEntry(TypedDict):
    code: str
    name: str
    native_name: str
    tier: LanguageTier
    direction: TextDirection
    supports_document_input: bool
    supports_explanation_output: bool
    notes: str | None


SUPPORTED_LANGUAGES: list[LanguageConfigEntry] = [
    {
        "code": "en",
        "name": "English",
        "native_name": "English",
        "tier": "verified",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "notes": "Verified full pipeline and lexical claim checks.",
    },
    {
        "code": "ta",
        "name": "Tamil",
        "native_name": "தமிழ்",
        "tier": "verified",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "notes": "Verified full pipeline and Tamil script rendering.",
    },
    {
        "code": "hi",
        "name": "Hindi",
        "native_name": "हिन्दी",
        "tier": "verified",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "notes": "Verified full pipeline and Devanagari script rendering.",
    },
    {
        "code": "bn",
        "name": "Bengali",
        "native_name": "বাংলা",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "notes": "Experimental: verify all terminology against your original document.",
    },
    {
        "code": "te",
        "name": "Telugu",
        "native_name": "తెలుగు",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "notes": "Experimental: verify all terminology against your original document.",
    },
    {
        "code": "mr",
        "name": "Marathi",
        "native_name": "मराठी",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "notes": "Experimental: verify all terminology against your original document.",
    },
    {
        "code": "ar",
        "name": "Arabic",
        "native_name": "العربية",
        "tier": "experimental",
        "direction": "rtl",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "notes": "Experimental right-to-left (RTL) script support.",
    },
    {
        "code": "ur",
        "name": "Urdu",
        "native_name": "اردو",
        "tier": "experimental",
        "direction": "rtl",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "notes": "Experimental right-to-left (RTL) script support.",
    },
    {
        "code": "fr",
        "name": "French",
        "native_name": "Français",
        "tier": "experimental",
        "direction": "ltr",
        "supports_document_input": True,
        "supports_explanation_output": True,
        "notes": "Experimental Latin-script support.",
    },
    {
        "code": "sa",
        "name": "Sanskrit (Classical)",
        "native_name": "संस्कृतम्",
        "tier": "unavailable",
        "direction": "ltr",
        "supports_document_input": False,
        "supports_explanation_output": False,
        "notes": "Unavailable in this release.",
    },
]

LANGUAGE_BY_CODE: dict[str, LanguageConfigEntry] = {
    entry["code"]: entry for entry in SUPPORTED_LANGUAGES
}


def get_language_entry(code: str | None) -> LanguageConfigEntry | None:
    if not code:
        return None
    return LANGUAGE_BY_CODE.get(code.strip().lower())


def detect_document_language(text: str) -> tuple[str, str, bool]:
    """Detect primary script/language from extracted text.

    Returns (language_code, language_label, is_uncertain).
    Never guesses silently when text is empty, mixed, or ambiguous.
    """
    if not text or not text.strip():
        return ("unknown", "Uncertain — please select document language", True)

    counts: dict[str, int] = {
        "ta": 0,  # Tamil U+0B80..U+0BFF
        "hi": 0,  # Devanagari U+0900..U+097F
        "bn": 0,  # Bengali U+0980..U+09FF
        "te": 0,  # Telugu U+0C00..U+0C7F
        "ar": 0,  # Arabic/Urdu U+0600..U+06FF
        "en": 0,  # Basic Latin letters
    }

    for ch in text:
        cp = ord(ch)
        if 0x0B80 <= cp <= 0x0BFF:
            counts["ta"] += 1
        elif 0x0900 <= cp <= 0x097F:
            counts["hi"] += 1
        elif 0x0980 <= cp <= 0x09FF:
            counts["bn"] += 1
        elif 0x0C00 <= cp <= 0x0C7F:
            counts["te"] += 1
        elif 0x0600 <= cp <= 0x06FF:
            counts["ar"] += 1
        elif ("A" <= ch <= "Z") or ("a" <= ch <= "z"):
            counts["en"] += 1

    total_alpha = sum(counts.values())
    if total_alpha < 10:
        return ("unknown", "Uncertain — please select document language", True)

    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    top_code, top_count = ranked[0]
    second_code, second_count = ranked[1]

    # Detect bilingual / multi-script documents
    if second_count > 0 and (second_count / total_alpha) >= 0.20:
        top_name = LANGUAGE_BY_CODE[top_code]["name"]
        second_name = LANGUAGE_BY_CODE[second_code]["name"]
        return (
            top_code,
            f"Multiple languages detected ({top_name} + {second_name})",
            True,
        )

    entry = LANGUAGE_BY_CODE[top_code]
    return (top_code, entry["name"], False)