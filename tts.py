# JARVIS — Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI
"""
tts.py — text-to-speech for JARVIS.

Primary: ElevenLabs (the British "George" voice) → returns MP3 bytes that the
backend base64-encodes and streams over the WebSocket for browser playback.

Fallback: macOS `say` (built in, no key required). If ElevenLabs has no key or
errors out, JARVIS still talks — it just speaks through the Mac's local voice.
"""

from __future__ import annotations

import os
import platform
import subprocess
import tempfile

import httpx

DEFAULT_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")  # George
ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice}"
IS_MACOS = platform.system() == "Darwin"


class TTSResult:
    """Either MP3 audio bytes (ElevenLabs) or a flag that `say` already spoke."""

    def __init__(self, audio: bytes | None, engine: str, spoke_locally: bool = False):
        self.audio = audio
        self.engine = engine
        self.spoke_locally = spoke_locally


async def _elevenlabs(text: str, voice_id: str) -> bytes:
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key or api_key == "your-elevenlabs-api-key-here":
        raise RuntimeError("no ElevenLabs API key")
    headers = {
        "xi-api-key": api_key,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {"stability": 0.4, "similarity_boost": 0.75, "style": 0.2},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            ELEVEN_URL.format(voice=voice_id), headers=headers, json=payload
        )
        resp.raise_for_status()
        return resp.content


def _say(text: str) -> bool:
    """Speak via macOS `say`. Returns True if it ran."""
    if not IS_MACOS:
        return False
    try:
        # Daniel is the built-in British male voice — a fitting butler fallback.
        subprocess.run(["say", "-v", "Daniel", text], check=False, timeout=60)
        return True
    except Exception:
        return False


async def synthesize(text: str, voice_id: str | None = None) -> TTSResult:
    """Try ElevenLabs first; fall back to macOS `say`."""
    text = (text or "").strip()
    if not text:
        return TTSResult(None, "none")
    voice = voice_id or DEFAULT_VOICE_ID
    try:
        audio = await _elevenlabs(text, voice)
        return TTSResult(audio, "elevenlabs")
    except Exception:
        spoke = _say(text)
        return TTSResult(None, "macos-say" if spoke else "none", spoke_locally=spoke)
