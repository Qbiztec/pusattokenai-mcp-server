import os
from typing import Optional, List
from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.routing import Route

from mcp.server.mcpserver import MCPServer

from .modalities.text import generate_text as _generate_text, DEFAULT_TEXT_MODEL
from .modalities.image import generate_image as _generate_image, DEFAULT_IMAGE_MODEL
from .modalities.audio import generate_audio as _generate_audio, DEFAULT_AUDIO_MODEL, DEFAULT_VOICE

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
        return f"{res.get('html_player')}\n\n*Spoken text: \"{res.get('text')}\" (Voice: {res.get('voice')})*"
    return f"Error: {res.get('message')}"


async def handle_health(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(
        {
            "status": "healthy",
            "server": "pusattokenai-mcp",
            "modalities": ["text", "image", "audio"],
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


# Mount SSE Starlette app and add health check route
base_app = mcp.sse_app()
base_app.routes.append(Route("/health", endpoint=handle_health, methods=["GET"]))

# Wrap with pure ASGI middleware
app = PureASGIAuthMiddleware(base_app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.server:app", host="0.0.0.0", port=8088, reload=True)
