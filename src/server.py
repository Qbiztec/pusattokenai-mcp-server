import os
from typing import Optional, List
from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.routing import Route
from starlette.middleware.base import BaseHTTPMiddleware

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


async def handle_health(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(
        {
            "status": "healthy",
            "server": "pusattokenai-mcp",
            "modalities": ["text", "image"],
        }
    )


class AuthExtractionMiddleware(BaseHTTPMiddleware):
    """Dynamically extracts the user's API key from their incoming MCP client request."""
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            os.environ["PUSATTOKENAI_API_KEY"] = auth_header[7:].strip()

        api_key_query = request.query_params.get("api_key")
        if api_key_query:
            os.environ["PUSATTOKENAI_API_KEY"] = api_key_query.strip()

        return await call_next(request)


# Mount SSE Starlette app, add health check route, and add dynamic auth middleware
app = mcp.sse_app()
app.routes.append(Route("/health", endpoint=handle_health, methods=["GET"]))
app.add_middleware(AuthExtractionMiddleware)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.server:app", host="0.0.0.0", port=8088, reload=True)
