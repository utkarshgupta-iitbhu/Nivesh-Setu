"""Application settings loaded from environment variables (.env).

We keep all secrets (like SARVAM_API_KEY) on the backend so they are never
exposed to the browser.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> Path | None:
    """Load key=value pairs from root .env without requiring external packages."""
    root = Path(__file__).resolve().parents[2]
    env_path = root / ".env"
    if not env_path.is_file():
        return None
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
    return env_path


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    sarvam_api_key: str = os.getenv("SARVAM_API_KEY", "").strip()
    sarvam_chat_model: str = os.getenv("SARVAM_CHAT_MODEL", "sarvam-105b-conversations")
    sarvam_tts_model: str = os.getenv("SARVAM_TTS_MODEL", "bulbul:v3")
    sarvam_stt_model: str = os.getenv("SARVAM_STT_MODEL", "saarika:v2.5")
    sarvam_tts_speaker: str = os.getenv("SARVAM_TTS_SPEAKER", "simran")

    @property
    def ai_enabled(self) -> bool:
        return bool(self.sarvam_api_key)


settings = Settings()
