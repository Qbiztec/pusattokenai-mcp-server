import os
import json
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse, Response
from starlette.requests import Request

from mcp.server import Server
from mcp.server.sse import SseServerTransport
import mcp.types as types

from .modalities.text import generate_text, DEFAULT_TEXT_MODEL
from .modalities.image import generate_image, DEFAULT_IMAGE_MODEL

# Initialize MCP Server
app_server = Server("pusattokenai-mcp")
sse_transport = SseServerTransport("/messages")


@app_server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """Exposes available modality tools to MCP clients."""
    return [
        types.Tool(
            name="generate_text",
            description="Generate text completions or reasoning using models available on PusatTokenAI (e.g., deepseek-r1, gpt-4o, claude-3-5-sonnet).",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "User instruction, query, or prompt.",
                    },
                    "model": {
                        "type": "string",
                        "description": f"Model identifier. Default: {DEFAULT_TEXT_MODEL}.",
                        "default": DEFAULT_TEXT_MODEL,
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "Optional system prompt or instructions.",
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Sampling temperature between 0.0 and 1.0.",
                        "default": 0.7,
                    },
                },
                "required": ["prompt"],
            },
        ),
        types.Tool(
            name="generate_image",
            description="Generate images from text prompts using models available on PusatTokenAI (e.g., seedream-4.5, seedream-5.0-pro, gpt-image-2.5-flare).",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed visual description of the desired image.",
                    },
                    "model": {
                        "type": "string",
                        "description": f"Model identifier. Default: {DEFAULT_IMAGE_MODEL}.",
                        "default": DEFAULT_IMAGE_MODEL,
                    },
                    "size": {
                        "type": "string",
                        "description": "Target image resolution (e.g., '1024x1024', '768x1024').",
                        "default": "1024x1024",
                    },
                    "n": {
                        "type": "integer",
                        "description": "Number of images to generate.",
                        "default": 1,
                    },
                },
                "required": ["prompt"],
            },
        ),
    ]


@app_server.call_tool()
async def handle_call_tool(
    name: str, arguments: Optional[Dict[str, Any]]
) -> List[types.TextContent | types.ImageContent]:
    """Executes requested modality tool."""
    args = arguments or {}

    if name == "generate_text":
        res = await generate_text(
            prompt=args.get("prompt", ""),
            model=args.get("model", DEFAULT_TEXT_MODEL),
            system_prompt=args.get("system_prompt"),
            temperature=float(args.get("temperature", 0.7)),
        )

        if res.get("status") == "success":
            output = res.get("text", "")
            if res.get("reasoning"):
                output = f"<thinking>\n{res['reasoning']}\n</thinking>\n\n{output}"
            return [types.TextContent(type="text", text=output)]
        else:
            return [types.TextContent(type="text", text=f"Error: {res.get('message')}")]

    elif name == "generate_image":
        res = await generate_image(
            prompt=args.get("prompt", ""),
            model=args.get("model", DEFAULT_IMAGE_MODEL),
            size=args.get("size", "1024x1024"),
            n=int(args.get("n", 1)),
        )

        if res.get("status") == "success":
            images = res.get("images", [])
            lines = [f"Generated {len(images)} image(s) using {res.get('model')}:"]
            for idx, img_url in enumerate(images, 1):
                lines.append(f"{idx}. ![{args.get('prompt', 'image')}]({img_url})")
            return [types.TextContent(type="text", text="\n".join(lines))]
        else:
            return [types.TextContent(type="text", text=f"Error: {res.get('message')}")]

    return [types.TextContent(type="text", text=f"Tool not found: {name}")]


# --- HTTP / SSE Transport Endpoints ---

async def handle_sse(request: Request) -> Response:
    """Connects client to the SSE stream and initializes session."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        os.environ["PUSATTOKENAI_API_KEY"] = auth_header[7:].strip()

    api_key_query = request.query_params.get("api_key")
    if api_key_query:
        os.environ["PUSATTOKENAI_API_KEY"] = api_key_query.strip()

    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await app_server.run(
            read_stream,
            write_stream,
            app_server.create_initialization_options(),
        )
    return Response(status_code=200)


async def handle_messages(request: Request) -> Response:
    """Handles JSON-RPC message exchange for connected SSE sessions."""
    return await sse_transport.handle_post_message(
        request.scope, request.receive, request._send
    )


async def handle_health(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(
        {
            "status": "healthy",
            "server": "pusattokenai-mcp",
            "modalities": ["text", "image"],
        }
    )


# Starlette Application Instance
routes = [
    Route("/health", endpoint=handle_health, methods=["GET"]),
    Route("/sse", endpoint=handle_sse, methods=["GET"]),
    Route("/messages", endpoint=handle_messages, methods=["POST"]),
]

app = Starlette(routes=routes)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("src.server:app", host=host, port=port, reload=True)
