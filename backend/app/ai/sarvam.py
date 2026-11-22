"""Async Sarvam AI client (Chat, Bulbul v3 TTS, Saarika v2.5 STT).

All network calls use `httpx` with strict timeouts and automatic fallback
handling so the app works reliably even on slow networks or without an API key.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

import httpx

from app.config import settings

SARVAM_BASE_URL = "https://api.sarvam.ai"


class SarvamError(RuntimeError):
    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


def extract_json_object(raw: str) -> dict[str, Any] | None:
    """Strip markdown fences and extract the first valid JSON object from model output."""
    cleaned = re.sub(r"```(?:json)?", "", raw or "", flags=re.IGNORECASE).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(cleaned[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


async def chat_completion(
    system_prompt: str,
    user_prompt: str,
    *,
    expect_json: bool = False,
    max_tokens: int = 450,
    temperature: float = 0.25,
    timeout_sec: float = 18.0,
) -> str:
    """Call Sarvam chat completions API."""
    if not settings.ai_enabled:
        raise SarvamError("no_key", "SARVAM_API_KEY is not configured")

    sys_text = system_prompt
    if expect_json:
        sys_text += "\n\nReturn ONLY one valid JSON object. No markdown, no code fences, no extra text."

    payload = {
        "model": settings.sarvam_chat_model,
        "messages": [
            {"role": "system", "content": sys_text},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    headers = {
        "api-subscription-key": settings.sarvam_api_key,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.post(f"{SARVAM_BASE_URL}/v1/chat/completions", json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        raise SarvamError("timeout", f"Sarvam request timed out: {exc}") from exc
    except httpx.HTTPError as exc:
        raise SarvamError("network", f"Sarvam network error: {exc}") from exc

    if resp.status_code >= 400:
        raise SarvamError(f"http:{resp.status_code}", f"Sarvam HTTP {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise SarvamError("bad_response", "Unexpected Sarvam response structure") from exc
    return str(content or "").strip()


async def think_json_validated(
    system_prompt: str,
    user_prompt: str,
    validator: Callable[[dict[str, Any]], str | None],
    *,
    max_tokens: int = 450,
    temperature: float = 0.25,
    retries: int = 1,
) -> dict[str, Any]:
    """Call Sarvam expecting JSON, validate with Layer 3 guardrails, retry once on failure."""
    last_reason = "error"
    for _ in range(retries + 1):
        raw = await chat_completion(
            system_prompt,
            user_prompt,
            expect_json=True,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        obj = extract_json_object(raw)
        if obj is None:
            last_reason = "not_json"
            continue
        problem = validator(obj)
        if problem is None:
            return obj
        last_reason = f"validation:{problem}"

    raise SarvamError(last_reason, f"Sarvam output rejected ({last_reason})")


async def synthesize_speech(text: str, lang: str = "hi") -> dict[str, Any]:
    """Convert text to speech via Sarvam Bulbul v3, or signal browser fallback."""
    if not settings.ai_enabled:
        return {"source": "browser_fallback", "reason": "no_key", "audio_base64": None}

    lang_code = "hi-IN" if lang == "hi" else "en-IN"
    payload = {
        "inputs": [text[:500]],
        "target_language_code": lang_code,
        "speaker": settings.sarvam_tts_speaker,
        "model": settings.sarvam_tts_model,
    }
    headers = {
        "api-subscription-key": settings.sarvam_api_key,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{SARVAM_BASE_URL}/text-to-speech", json=payload, headers=headers)
        if resp.status_code >= 400:
            return {"source": "browser_fallback", "reason": f"http:{resp.status_code}", "audio_base64": None}
        data = resp.json()
        audios = data.get("audios") or []
        if not audios:
            return {"source": "browser_fallback", "reason": "empty_audio", "audio_base64": None}
        return {
            "source": "sarvam",
            "mime_type": "audio/wav",
            "audio_base64": audios[0],
        }
    except httpx.HTTPError:
        return {"source": "browser_fallback", "reason": "network", "audio_base64": None}


async def transcribe_speech(audio_bytes: bytes, filename: str = "voice.webm", lang: str = "hi") -> dict[str, Any]:
    """Transcribe short voice audio via Sarvam Saarika v2.5 and immediately drop audio from memory."""
    if not settings.ai_enabled:
        return {"source": "browser_fallback", "reason": "no_key", "transcript": ""}

    lang_code = "hi-IN" if lang == "hi" else "en-IN"
    headers = {"api-subscription-key": settings.sarvam_api_key}
    files = {"file": (filename, audio_bytes, "audio/webm")}
    data = {"model": settings.sarvam_stt_model, "language_code": lang_code}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(f"{SARVAM_BASE_URL}/speech-to-text", headers=headers, files=files, data=data)
        if resp.status_code >= 400:
            return {"source": "browser_fallback", "reason": f"http:{resp.status_code}", "transcript": ""}
        body = resp.json()
        return {"source": "sarvam", "transcript": str(body.get("transcript", "")).strip()}
    except httpx.HTTPError:
        return {"source": "browser_fallback", "reason": "network", "transcript": ""}
