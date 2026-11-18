# Audio Modality Handler. Interfaces with /v1/chat/completions for Text-to-Speech (TTS) audio streaming.

import os
import io
import time
import uuid
import wave
import json
import base64
from pathlib import Path
from typing import Optional, Dict, Any
import httpx

BASE_URL = "https://www.pusattokenai.com/v1"
DEFAULT_AUDIO_MODEL = "qwen3.5-omni-flash"
DEFAULT_VOICE = "Serena"
MEDIA_DIR = Path(os.getenv("MEDIA_DIR", "/tmp/pusattokenai_media"))
MEDIA_TTL_SECONDS = 86400  # 24 hours


def pcm_to_wav_bytes(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, sampwidth: int = 2) -> bytes:
    """Wraps raw 16-bit PCM bytes into a standard RIFF WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def _cleanup_expired_media() -> None:
    """Removes expired audio files from MEDIA_DIR."""
    if not MEDIA_DIR.exists():
        return
    cutoff = time.time() - MEDIA_TTL_SECONDS
    for path in MEDIA_DIR.iterdir():
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
        except OSError:
            continue


def save_wav_file(wav_bytes: bytes) -> Dict[str, str]:
    """Saves WAV bytes to MEDIA_DIR and returns filename and path."""
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    _cleanup_expired_media()
    filename = f"{uuid.uuid4().hex}.wav"
    file_path = MEDIA_DIR / filename
    file_path.write_bytes(wav_bytes)
    return {"filename": filename, "file_path": str(file_path)}


async def generate_audio(
    text: str,
    api_key: Optional[str] = None,
    model: str = DEFAULT_AUDIO_MODEL,
    voice: str = DEFAULT_VOICE,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """Generates speech audio from text using audio models available on PusatTokenAI.

    Args:
        text: Text to speak or read aloud.
        api_key: User's PusatTokenAI API key.
        model: Audio model identifier (default: 'qwen3.5-omni-flash').
        voice: Voice name (e.g., 'Serena' for female, 'Ethan' for male).
        timeout: Request timeout in seconds.

    Returns:
        Dict containing status, transcription text, Base64 WAV data, and ready-to-render HTML5 player.
    """
    token = api_key or os.getenv("PUSATTOKENAI_API_KEY")
    if not token:
        return {
            "status": "error",
            "message": "Missing API key. Provide api_key or send Authorization header from your MCP client.",
        }

    payload = {
        "model": model,
        "modalities": ["text", "audio"],
        "audio": {
            "voice": voice,
            "format": "wav",
        },
        "stream": True,
        "messages": [
            {
                "role": "user",
                "content": f"Please say the following text clearly: {text}",
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    url = f"{BASE_URL}/chat/completions"
    audio_chunks = []
    text_chunks = []

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if "content" in delta and delta["content"]:
                            text_chunks.append(delta["content"])
                        if "audio" in delta and "data" in delta["audio"]:
                            audio_chunks.append(base64.b64decode(delta["audio"]["data"]))
                    except Exception:
                        continue

            pcm_data = b"".join(audio_chunks)
            if not pcm_data:
                return {
                    "status": "error",
                    "message": "No audio stream received from gateway.",
                    "text": "".join(text_chunks),
                }

            wav_bytes = pcm_to_wav_bytes(pcm_data, sample_rate=24000)
            saved = save_wav_file(wav_bytes)
            spoken_text = "".join(text_chunks).strip() or text
            duration_seconds = round(len(pcm_data) / (24000 * 2), 2)

            return {
                "status": "success",
                "model": model,
                "voice": voice,
                "text": spoken_text,
                "audio_bytes": len(wav_bytes),
                "duration_seconds": duration_seconds,
                "filename": saved["filename"],
                "file_path": saved["file_path"],
            }

        except httpx.HTTPStatusError as e:
            return {
                "status": "error",
                "status_code": e.response.status_code,
                "message": f"Gateway HTTP error: {e.response.text}",
            }
        except httpx.RequestError as e:
            return {
                "status": "error",
                "message": f"Connection error: {str(e)}",
            }
