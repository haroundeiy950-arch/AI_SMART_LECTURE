from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Smart AI Glasses Web")
    secret_key: str = os.getenv("SECRET_KEY", "CHANGE-THIS-IN-PRODUCTION-2026")
    database_url: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'data' / 'smart_ai_glasses.db').as_posix()}"
    )
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))
    origin: str = os.getenv("ORIGIN", "http://localhost:8000")
    rp_id: str = os.getenv("WEBAUTHN_RP_ID", "localhost")
    rp_name: str = os.getenv("WEBAUTHN_RP_NAME", "Smart AI Glasses Web")
    secure_cookies: bool = os.getenv("SECURE_COOKIES", "false").lower() == "true"
    session_max_age: int = int(os.getenv("SESSION_MAX_AGE", "28800"))
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "ChangeMe@12345")
    admin_display_name: str = os.getenv("ADMIN_DISPLAY_NAME", "System Administrator")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    ai_text_model: str = os.getenv("AI_TEXT_MODEL", "gpt-5-mini")
    ai_vision_model: str = os.getenv("AI_VISION_MODEL", "gpt-5-mini")
    ai_voice_model: str = os.getenv("AI_VOICE_MODEL", "gpt-4o-mini-tts")
    ai_transcribe_model: str = os.getenv(
        "AI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe"
    )
    data_dir: Path = BASE_DIR / "data"
    known_faces_dir: Path = BASE_DIR / "data" / "known_faces"
    captures_dir: Path = BASE_DIR / "data" / "security_captures"
    audio_dir: Path = BASE_DIR / "data" / "audio"
    backups_dir: Path = BASE_DIR / "data" / "backups"
    products_dir: Path = BASE_DIR / "data" / "product_images"

    @property
    def ai_enabled(self) -> bool:
        return bool(self.openai_api_key.strip())


settings = Settings()

for directory in (
    settings.data_dir,
    settings.known_faces_dir,
    settings.captures_dir,
    settings.audio_dir,
    settings.backups_dir,
    settings.products_dir,
):
    directory.mkdir(parents=True, exist_ok=True)
