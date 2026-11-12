# Audio Modality Handler. Interfaces with /v1/chat/completions for Text-to-Speech (TTS) audio streaming.

import os
import io
import wave
import json
import base64
from typing import Optional, Dict, Any
import httpx

BASE_URL = "https://www.pusattokenai.com/v1"
DEFAULT_AUDIO_MODEL = "qwen3.5-omni-flash"
DEFAULT_VOICE = "Serena"


def pcm_to_wav_base64(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, sampwidth: int = 2) -> str:
    """Wraps raw 16-bit PCM bytes into a standard RIFF WAV container and returns Base64."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return base64.b64encode(buf.getvalue()).decode("ascii")


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

            wav_b64 = pcm_to_wav_base64(pcm_data, sample_rate=24000)
            spoken_text = "".join(text_chunks).strip() or text

            return {
                "status": "success",
                "model": model,
                "voice": voice,
                "text": spoken_text,
                "audio_bytes": len(pcm_data),
                "audio_base64": wav_b64,
                "data_uri": f"data:audio/wav;base64,{wav_b64}",
                "html_player": f'<audio controls src="data:audio/wav;base64,{wav_b64}"></audio>',
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
