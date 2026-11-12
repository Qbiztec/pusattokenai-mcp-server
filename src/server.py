import os
from typing import Optional, List
from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.routing import Route

from mcp.server.mcpserver import MCPServer

from .modalities.text import generate_text as _generate_text, DEFAULT_TEXT_MODEL
from .modalities.image import generate_image as _generate_image, DEFAULT_IMAGE_MODEL

mcp = MCPServer("pusattokenai-mcp")


@mcp.tool()
async def generate_text(
    prompt: str,
    model: str = DEFAULT_TEXT_MODEL,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
) -> str:
    """Generate text completions or reasoning using models available on PusatTokenAI (e.g., deepseek-r1, gpt-4o, claude-3-5-sonnet)."""
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


async def handle_health(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(
        {
            "status": "healthy",
            "server": "pusattokenai-mcp",
            "modalities": ["text", "image"],
        }
    )


# Mount SSE Starlette app and add health check route
app = mcp.sse_app()
app.routes.append(Route("/health", endpoint=handle_health, methods=["GET"]))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8088"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("src.server:app", host=host, port=port, reload=True)
