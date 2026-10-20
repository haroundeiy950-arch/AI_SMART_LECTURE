from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .config import settings

API_BASE = "https://api.openai.com/v1"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }


def _extract_output_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"].strip()
    parts: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts).strip()


async def assistant_reply(message: str, language: str = "ar") -> str:
    message = message.strip()
    if not message:
        return "Please enter a message."
    if not settings.ai_enabled:
        return (
            "وضع الذكاء الاصطناعي المتقدم غير مفعّل. أضف OPENAI_API_KEY داخل ملف .env. "
            f"تم استلام رسالتك: {message}"
        )

    language_name = {
        "ar": "Arabic",
        "en": "English",
        "fr": "French",
        "rw": "Kinyarwanda",
    }.get(language, language)
    body = {
        "model": settings.ai_text_model,
        "instructions": (
            "You are the voice assistant inside a Smart AI Glasses graduation project. "
            "Be practical, safety-aware, concise, and helpful. "
            f"Reply in {language_name}."
        ),
        "input": message,
    }
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(f"{API_BASE}/responses", headers=_headers(), json=body)
        response.raise_for_status()
        text = _extract_output_text(response.json())
        return text or "No response was generated."


async def generate_speech(text: str, voice: str = "coral") -> bytes | None:
    if not settings.ai_enabled:
        return None
    body = {
        "model": settings.ai_voice_model,
        "voice": voice,
        "input": text[:4096],
        "instructions": "Speak clearly, naturally, warmly, and professionally.",
        "response_format": "mp3",
    }
    headers = _headers()
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(f"{API_BASE}/audio/speech", headers=headers, json=body)
        response.raise_for_status()
        return response.content


async def transcribe_audio(filename: str, content: bytes, content_type: str) -> str:
    if not settings.ai_enabled:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    files = {"file": (filename, content, content_type or "audio/webm")}
    data = {"model": settings.ai_transcribe_model}
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{API_BASE}/audio/transcriptions", headers=headers, files=files, data=data
        )
        response.raise_for_status()
        return response.json().get("text", "").strip()


async def analyze_image(data_url: str) -> dict[str, Any]:
    if not settings.ai_enabled:
        return {
            "scene": "Image captured successfully. Online AI vision is not configured.",
            "objects": [],
            "visible_text": "",
            "people_count": 0,
            "general_emotion": "not analyzed",
            "safety_alerts": [],
        }
    prompt = (
        "Analyze this camera frame for an assistive smart-glasses system. "
        "Return only valid JSON with keys: scene (string), objects (array of strings), "
        "visible_text (string), people_count (integer), general_emotion (string; only a broad "
        "visible expression, do not infer sensitive traits), safety_alerts (array of strings)."
    )
    body = {
        "model": settings.ai_vision_model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": data_url},
                ],
            }
        ],
    }
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(f"{API_BASE}/responses", headers=_headers(), json=body)
        response.raise_for_status()
        text = _extract_output_text(response.json())
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.IGNORECASE).strip()
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    return {
        "scene": text or "Analysis completed.",
        "objects": [],
        "visible_text": "",
        "people_count": 0,
        "general_emotion": "unknown",
        "safety_alerts": [],
    }


async def translate_text(text: str, target_language: str) -> str:
    if not text.strip():
        return ""
    return await assistant_reply(
        f"Translate the following text into {target_language}. Return only the translation:\n{text}",
        language="en",
    )


async def summarize_meeting(transcript: str) -> tuple[str, str]:
    if not settings.ai_enabled:
        summary = transcript.strip()[:800] or "No transcript provided."
        return summary, "AI task extraction requires OPENAI_API_KEY."
    prompt = (
        "Analyze this meeting transcript. Return valid JSON with two string keys: summary and tasks. "
        "The tasks string should contain a numbered list with owner and deadline when stated.\n\n"
        f"TRANSCRIPT:\n{transcript}"
    )
    text = await assistant_reply(prompt, language="en")
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.IGNORECASE).strip()
    try:
        data = json.loads(cleaned)
        return str(data.get("summary", text)), str(data.get("tasks", ""))
    except json.JSONDecodeError:
        return text, ""
