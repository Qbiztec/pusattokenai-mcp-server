import os
from pathlib import Path
from typing import Optional, List
from starlette.responses import JSONResponse, FileResponse
from starlette.requests import Request
from starlette.routing import Route

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from .modalities.text import generate_text as _generate_text, DEFAULT_TEXT_MODEL
from .modalities.image import generate_image as _generate_image, DEFAULT_IMAGE_MODEL
from .modalities.audio import (
    generate_audio as _generate_audio,
    DEFAULT_AUDIO_MODEL,
    DEFAULT_VOICE,
    MEDIA_DIR,
)
from .modalities.video import (
    generate_video as _generate_video,
    get_video_status as _get_video_status,
    DEFAULT_VIDEO_MODEL,
    DEFAULT_DURATION,
    DEFAULT_RESOLUTION,
    DEFAULT_RATIO,
)

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://mcp.pusattokenai.com").rstrip("/")

mcp = MCPServer("pusattokenai-mcp")


@mcp.tool()
async def generate_text(
    prompt: str,
    model: str = DEFAULT_TEXT_MODEL,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
) -> str:
    """Generate text completions or reasoning using models available on PusatTokenAI (e.g., gemini-3.8-flash, gpt-4o, claude-sonnet-5-5)."""
    res = await _generate_text(
        prompt=prompt,
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
    )
    if res.get("status") == "success":
        output = res.get("text", "")
        if res.get("reasoning"):
            output = f"<thinking>\n{res['reasoning']}\n</thinking>\n\n{output}"
        return output
    return f"Error: {res.get('message')}"


@mcp.tool()
async def generate_image(
    prompt: str,
    model: str = DEFAULT_IMAGE_MODEL,
    size: str = "1024x1024",
    n: int = 1,
) -> str:
    """Generate images from text prompts using models available on PusatTokenAI (e.g., seedream-4.5, seedream-5.0-pro, gpt-image-2.5-flare)."""
    res = await _generate_image(
        prompt=prompt,
        model=model,
        size=size,
        n=n,
    )
    if res.get("status") == "success":
        images = res.get("images", [])
        lines = [f"Generated {len(images)} image(s) using {res.get('model')}:"]
        for idx, img_url in enumerate(images, 1):
            lines.append(f"{idx}. ![{prompt}]({img_url})")
        return "\n".join(lines)
    return f"Error: {res.get('message')}"


@mcp.tool()
async def generate_audio(
    text: str,
    model: str = DEFAULT_AUDIO_MODEL,
    voice: str = DEFAULT_VOICE,
) -> str:
    """Generate speech audio from text using models available on PusatTokenAI (e.g., qwen3.5-omni-flash with Serena or Ethan voice)."""
    res = await _generate_audio(
        text=text,
        model=model,
        voice=voice,
    )
    if res.get("status") == "success":
        audio_url = f"{PUBLIC_BASE_URL}/media/{res.get('filename')}"
        return (
            f"Generated audio using {res.get('model')} "
            f"(Voice: {res.get('voice')}, ~{res.get('duration_seconds')}s):\n"
            f"{audio_url}\n\n"
            f"*Spoken text: \"{res.get('text')}\"*"
        )
    return f"Error: {res.get('message')}"


@mcp.tool()
async def generate_video(
    prompt: str,
    model: str = DEFAULT_VIDEO_MODEL,
    duration: int = DEFAULT_DURATION,
    resolution: str = DEFAULT_RESOLUTION,
    ratio: str = DEFAULT_RATIO,
    image_url: Optional[str] = None,
    generate_audio: Optional[bool] = None,
    wait_seconds: int = 45,
) -> str:
    """Generate a video from text or an image using models available on PusatTokenAI (e.g., seedance-2.0-fast, seedance-2.0, kling-3.0-turbo)."""
    res = await _generate_video(
        prompt=prompt,
        model=model,
        duration=duration,
        resolution=resolution,
        ratio=ratio,
        image_url=image_url,
        generate_audio=generate_audio,
        wait_seconds=wait_seconds,
    )
    if res.get("status") == "success":
        return (
            f"Generated video using {res.get('model')} "
            f"({res.get('duration')}s, {res.get('resolution')}, {res.get('ratio')}):\n"
            f"{res.get('video_url')}"
        )
    if res.get("status") == "pending":
        return (
            f"Video generation submitted (task_id: `{res.get('task_id')}`, "
            f"status: {res.get('task_status')}, progress: {res.get('progress')}). "
            f"Call `get_video_status` with task_id `{res.get('task_id')}` to check completion and retrieve the video URL."
        )
    return f"Error: {res.get('message')}"


@mcp.tool()
async def get_video_status(task_id: str) -> str:
    """Check the status and retrieve the video URL of a pending PusatTokenAI video generation task."""
    res = await _get_video_status(task_id=task_id)
    if res.get("status") == "success":
        if res.get("task_status") == "SUCCESS" and res.get("video_url"):
            return (
                f"Video ready ({res.get('model')}, {res.get('duration')}s, "
                f"{res.get('resolution')}, {res.get('ratio')}):\n"
                f"{res.get('video_url')}"
            )
        return (
            f"Task `{task_id}` is still {res.get('task_status')} "
            f"(progress: {res.get('progress')}). Please check again shortly."
        )
    return f"Error: {res.get('message')}"


async def handle_media(request: Request) -> JSONResponse | FileResponse:
    """Serves generated temporary audio files."""
    filename = request.path_params.get("filename", "")
    if Path(filename).name != filename or not filename.endswith(".wav"):
        return JSONResponse({"error": "Invalid filename"}, status_code=400)
    file_path = MEDIA_DIR / filename
    if not file_path.is_file():
        return JSONResponse({"error": "Media not found or expired"}, status_code=404)
    return FileResponse(file_path, media_type="audio/wav", filename=filename)


async def handle_health(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(
        {
            "status": "healthy",
            "server": "pusattokenai-mcp",
            "modalities": ["text", "image", "audio", "video"],
        }
    )


class PureASGIAuthMiddleware:
    """Pure ASGI middleware to safely extract client API keys without breaking SSE streams."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            for name, value in scope.get("headers", []):
                if name.lower() == b"authorization":
                    val_str = value.decode("latin1", errors="ignore")
                    if val_str.startswith("Bearer "):
                        os.environ["PUSATTOKENAI_API_KEY"] = val_str[7:].strip()

            qs = scope.get("query_string", b"").decode("latin1", errors="ignore")
            for param in qs.split("&"):
                if param.startswith("api_key="):
                    os.environ["PUSATTOKENAI_API_KEY"] = param[8:].strip()

        await self.app(scope, receive, send)


# Allow reverse-proxied Host/Origin headers (e.g. mcp.pusattokenai.com via Nginx)
transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)

# Mount Streamable HTTP (/mcp) as base_app so its session_manager lifespan runs,
# then attach legacy SSE (/sse, /messages/) and /health routes.
base_app = mcp.streamable_http_app(transport_security=transport_security)
sse_app = mcp.sse_app(transport_security=transport_security)
base_app.routes.extend(sse_app.routes)
base_app.routes.append(Route("/media/{filename}", endpoint=handle_media, methods=["GET"]))
base_app.routes.append(Route("/health", endpoint=handle_health, methods=["GET"]))

# Wrap with pure ASGI middleware
app = PureASGIAuthMiddleware(base_app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.server:app", host="0.0.0.0", port=8088, reload=True)
