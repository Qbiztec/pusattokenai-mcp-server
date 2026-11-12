import os
import sys
import asyncio
import argparse
from mcp.server.stdio import stdio_server

from .server import app_server


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="PusatTokenAI MCP Server (Stdio Transport)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="PusatTokenAI API key. If omitted, reads from PUSATTOKENAI_API_KEY env var.",
    )
    args = parser.parse_args()

    if args.api_key:
        os.environ["PUSATTOKENAI_API_KEY"] = args.api_key

    async with stdio_server() as (read_stream, write_stream):
        await app_server.run(
            read_stream,
            write_stream,
            app_server.create_initialization_options(),
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
