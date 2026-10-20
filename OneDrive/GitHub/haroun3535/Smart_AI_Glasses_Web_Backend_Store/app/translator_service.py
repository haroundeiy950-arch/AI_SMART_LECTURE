from __future__ import annotations

import asyncio
import re
from functools import lru_cache
from typing import Final

from deep_translator import GoogleTranslator

# A small fallback list used only if the provider cannot return its language list.
_FALLBACK_LANGUAGES: Final[dict[str, str]] = {
    "arabic": "ar",
    "english": "en",
    "french": "fr",
    "kinyarwanda": "rw",
    "spanish": "es",
    "german": "de",
    "swahili": "sw",
    "chinese (simplified)": "zh-CN",
    "chinese (traditional)": "zh-TW",
    "turkish": "tr",
    "portuguese": "pt",
    "italian": "it",
    "japanese": "ja",
    "korean": "ko",
    "russian": "ru",
    "hindi": "hi",
    "dutch": "nl",
    "polish": "pl",
    "ukrainian": "uk",
    "indonesian": "id",
    "somali": "so",
    "amharic": "am",
}

# Friendly names for the languages most useful in this project.
_DISPLAY_NAMES: Final[dict[str, str]] = {
    "ar": "العربية",
    "en": "English",
    "fr": "Français",
    "rw": "Kinyarwanda",
    "es": "Español",
    "de": "Deutsch",
    "sw": "Kiswahili",
    "zh-CN": "中文（简体）",
    "zh-TW": "中文（繁體）",
    "tr": "Türkçe",
    "pt": "Português",
    "it": "Italiano",
    "ja": "日本語",
    "ko": "한국어",
    "ru": "Русский",
    "hi": "हिन्दी",
    "nl": "Nederlands",
    "pl": "Polski",
    "uk": "Українська",
    "id": "Bahasa Indonesia",
    "so": "Soomaali",
    "am": "አማርኛ",
}


@lru_cache(maxsize=1)
def _provider_languages() -> dict[str, str]:
    """Return a name-to-code mapping from the translation provider."""

    try:
        languages = GoogleTranslator().get_supported_languages(as_dict=True)
        if isinstance(languages, dict) and languages:
            return {str(name).lower(): str(code) for name, code in languages.items()}
    except Exception:
        pass

    return dict(_FALLBACK_LANGUAGES)


def get_supported_languages() -> list[dict[str, str]]:
    """Return languages for the HTML select list."""

    mapping = _provider_languages()
    items: list[dict[str, str]] = []

    for provider_name, code in mapping.items():
        items.append(
            {
                "code": code,
                "name": _DISPLAY_NAMES.get(code, provider_name.title()),
            }
        )

    # Put the most important project languages first, then sort the rest.
    priority = {
        "ar": 0,
        "en": 1,
        "fr": 2,
        "rw": 3,
        "sw": 4,
        "es": 5,
        "de": 6,
        "zh-CN": 7,
        "tr": 8,
        "pt": 9,
        "it": 10,
        "ja": 11,
        "ko": 12,
    }

    # Remove duplicate codes that can occur under different names.
    unique: dict[str, dict[str, str]] = {}
    for item in items:
        unique.setdefault(item["code"], item)

    return sorted(
        unique.values(),
        key=lambda item: (
            priority.get(item["code"], 999),
            item["name"].casefold(),
        ),
    )


def _normalise_language(value: str, *, allow_auto: bool) -> str:
    value = value.strip()
    if not value:
        return "auto" if allow_auto else "en"

    if allow_auto and value.lower() == "auto":
        return "auto"

    mapping = _provider_languages()
    available_codes = {code.lower(): code for code in mapping.values()}

    # The frontend normally sends a language code.
    if value.lower() in available_codes:
        return available_codes[value.lower()]

    # Also accept a provider language name for compatibility with the old page.
    if value.lower() in mapping:
        return mapping[value.lower()]

    raise ValueError(f"Unsupported language: {value}")


def _split_text(text: str, limit: int = 4000) -> list[str]:
    """Split long documents into provider-safe chunks."""

    text = text.strip()
    if len(text) <= limit:
        return [text]

    pieces = re.split(r"(?<=[.!?؟。])\s+|\n{2,}", text)
    chunks: list[str] = []
    current = ""

    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue

        if len(piece) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(piece[index : index + limit] for index in range(0, len(piece), limit))
            continue

        candidate = f"{current}\n{piece}".strip() if current else piece
        if len(candidate) <= limit:
            current = candidate
        else:
            chunks.append(current)
            current = piece

    if current:
        chunks.append(current)

    return chunks


def _translate_sync(text: str, source_language: str, target_language: str) -> str:
    source_code = _normalise_language(source_language, allow_auto=True)
    target_code = _normalise_language(target_language, allow_auto=False)

    if source_code.lower() == target_code.lower():
        return text.strip()

    translated_chunks: list[str] = []
    for chunk in _split_text(text):
        translator = GoogleTranslator(source=source_code, target=target_code)
        translated = translator.translate(text=chunk)
        translated_chunks.append(str(translated or "").strip())

    return "\n\n".join(part for part in translated_chunks if part)


async def translate_text(
    text: str,
    target_language: str,
    source_language: str = "auto",
) -> str:
    """Translate text without requiring an OpenAI API key."""

    text = text.strip()
    if not text:
        return ""

    try:
        return await asyncio.to_thread(
            _translate_sync,
            text,
            source_language,
            target_language,
        )
    except ValueError:
        raise
    except Exception as error:
        raise RuntimeError(
            "Translation failed. Check the internet connection and try again. "
            f"Details: {error}"
        ) from error
