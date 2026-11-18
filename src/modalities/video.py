# Video Modality Handler. Interfaces with /v1/video/generations for async text/image-to-video models.

import os
import time
import asyncio
from typing import Optional, Dict, Any
import httpx

BASE_URL = "https://www.pusattokenai.com/v1"
DEFAULT_VIDEO_MODEL = "seedance-2.0-fast"
DEFAULT_DURATION = 4
DEFAULT_RESOLUTION = "480p"
DEFAULT_RATIO = "16:9"


def _auth_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def get_video_status(
    task_id: str,
    api_key: Optional[str] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """Polls the status of an async video generation task on PusatTokenAI.

    Args:
        task_id: Task ID returned by generate_video.
        api_key: User's PusatTokenAI API key.
        timeout: Request timeout in seconds.

    Returns:
        Dict containing status, task_status, progress, and video_url when complete.
    """
    token = api_key or os.getenv("PUSATTOKENAI_API_KEY")
    if not token:
        return {
            "status": "error",
            "message": "Missing API key. Provide api_key or send Authorization header from your MCP client.",
        }

    url = f"{BASE_URL}/video/generations/{task_id}"

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.get(url, headers=_auth_headers(token))
            resp.raise_for_status()
            body = resp.json()
            data = body.get("data") or {}
            inner = data.get("data") or {}

            task_status = data.get("status", "UNKNOWN")
            progress = data.get("progress", "0%")
            fail_reason = data.get("fail_reason")
            video_url = (
                data.get("result_url")
                or (inner.get("content") or {}).get("video_url")
            )

            if task_status == "FAILURE" or fail_reason:
                return {
                    "status": "error",
                    "task_id": task_id,
                    "task_status": task_status,
                    "message": fail_reason or "Video generation failed.",
                }

            return {
                "status": "success",
                "task_id": task_id,
                "task_status": task_status,
                "progress": progress,
                "video_url": video_url,
                "model": (data.get("properties") or {}).get("origin_model_name") or inner.get("model"),
                "duration": inner.get("duration"),
                "resolution": inner.get("resolution"),
                "ratio": inner.get("ratio"),
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


async def generate_video(
    prompt: str,
    api_key: Optional[str] = None,
    model: str = DEFAULT_VIDEO_MODEL,
    duration: int = DEFAULT_DURATION,
    resolution: str = DEFAULT_RESOLUTION,
    ratio: str = DEFAULT_RATIO,
    image_url: Optional[str] = None,
    generate_audio: Optional[bool] = None,
    wait_seconds: int = 45,
    poll_interval: float = 5.0,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """Generates a video using async video models available on PusatTokenAI.

    Args:
        prompt: Detailed description of the desired video scene and motion.
        api_key: User's PusatTokenAI API key.
        model: Model identifier (default: 'seedance-2.0-fast').
        duration: Video duration in seconds (e.g., 3, 4, 5, 10).
        resolution: Target resolution (e.g., '480p', '720p', '1080p').
        ratio: Aspect ratio (e.g., '16:9', '9:16', '1:1').
        image_url: Optional reference/first-frame image URL for image-to-video.
        generate_audio: Optional flag to enable/disable native audio generation.
        wait_seconds: Max seconds to poll before returning task_id (0 = return immediately).
        poll_interval: Seconds between status polls.
        timeout: HTTP request timeout in seconds.

    Returns:
        Dict with video_url if completed within wait_seconds, or task_id/progress if still rendering.
    """
    token = api_key or os.getenv("PUSATTOKENAI_API_KEY")
    if not token:
        return {
            "status": "error",
            "message": "Missing API key. Provide api_key or send Authorization header from your MCP client.",
        }

    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
        "ratio": ratio,
    }
    if image_url:
        payload["image_url"] = image_url
    if generate_audio is not None:
        payload["generate_audio"] = generate_audio

    url = f"{BASE_URL}/video/generations"

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, json=payload, headers=_auth_headers(token))
            resp.raise_for_status()
            data = resp.json()
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

    task_id = data.get("task_id") or data.get("id")
    if not task_id:
        return {
            "status": "error",
            "message": f"Unexpected gateway response (missing task_id): {data}",
        }

    if wait_seconds <= 0:
        return {
            "status": "pending",
            "task_id": task_id,
            "task_status": data.get("status", "queued"),
            "progress": "0%",
            "model": model,
        }

    deadline = time.monotonic() + wait_seconds
    last_status = data.get("status", "queued")
    last_progress = "0%"

    while time.monotonic() < deadline:
        await asyncio.sleep(min(poll_interval, max(0.5, deadline - time.monotonic())))
        polled = await get_video_status(task_id=task_id, api_key=token, timeout=timeout)
        if polled.get("status") == "error":
            return polled

        last_status = polled.get("task_status", last_status)
        last_progress = polled.get("progress", last_progress)

        if last_status == "SUCCESS" and polled.get("video_url"):
            return polled

    return {
        "status": "pending",
        "task_id": task_id,
        "task_status": last_status,
        "progress": last_progress,
        "model": model,
    }

