# PusatTokenAI MCP Server

A modular Model Context Protocol (MCP) server providing unified access across all 4 output modalities supported by PusatTokenAI:

1. **Text**: Chat completion and deep reasoning models.
2. **Image**: Text-to-Image generation (`/v1/images/generations`).
3. **Audio**: Streaming Text-to-Speech (`/v1/chat/completions` with audio stream).
4. **Video**: Asynchronous Text-to-Video generation (`/v1/video/generations`) with automated background polling.

## Project Structure

```
pusattokenai-mcp-server/
└── src/
    └── modalities/
```
