"""ElevenLabs Text-to-Speech (TTS) integration service.

Streams synthesized audio directly to the client without saving MP3 files to disk.
Credentials remain strictly backend-only.
"""
from __future__ import annotations

import logging
from typing import Generator

from fastapi import HTTPException
import requests
from starlette.responses import StreamingResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"


def generate_speech(text: str) -> StreamingResponse:
    """Call ElevenLabs TTS API and stream the audio response.

    Args:
        text: The text string to synthesize into speech.

    Returns:
        StreamingResponse with media_type="audio/mpeg"

    Raises:
        HTTPException(503): If ElevenLabs is not configured or fails.
    """
    api_key = settings.ELEVENLABS_API_KEY
    voice_id = settings.ELEVENLABS_VOICE_ID
    model_id = settings.ELEVENLABS_MODEL_ID or "eleven_multilingual_v2"

    if not api_key or not voice_id:
        logger.warning("ElevenLabs credentials (API key or Voice ID) are not configured.")
        raise HTTPException(
            status_code=503,
            detail="Voice service unavailable (not configured)",
        )

    clean_text = text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Text required for speech generation")

    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "model_id": model_id,
        "text": clean_text,
        "voice_settings": {
            "stability": 0.75,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            stream=True,
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.error("ElevenLabs request failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Voice service unavailable",
        ) from exc

    if response.status_code != 200:
        logger.error(
            "ElevenLabs returned status %d: %s",
            response.status_code,
            response.text[:200] if response.text else "No details",
        )
        raise HTTPException(
            status_code=503,
            detail="Voice service unavailable",
        )

    def iter_audio() -> Generator[bytes, None, None]:
        for chunk in response.iter_content(chunk_size=4096):
            if chunk:
                yield chunk

    return StreamingResponse(
        iter_audio(),
        media_type="audio/mpeg",
        headers={
            "Content-Type": "audio/mpeg",
            "Cache-Control": "no-cache",
        },
    )
