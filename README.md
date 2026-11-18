# PusatTokenAI MCP Server

A modular Model Context Protocol (MCP) server providing access to frontier text, reasoning, image generation, audio speech, and video generation models hosted on PusatTokenAI.

---

## 1. Quickstart Deployment (Server Host)

The server requires minimal configuration via environment variables:

```bash
# 1. Copy environment template (defaults to port 8088)
cp .env.example .env

# 2. (Optional) Customize settings in .env if needed:
# MCP_PORT=10234
# PUBLIC_BASE_URL=https://mcp.pusattokenai.com
# MEDIA_DIR=/tmp/pusattokenai_media

# 3. Start the container
docker compose up -d --build
```

### Endpoints
* **Health Check**: `GET http://<server-ip>:<MCP_PORT>/health`
* **Streamable HTTP (Recommended)**: `http://<server-ip>:<MCP_PORT>/mcp`
* **Legacy SSE Stream**: `GET http://<server-ip>:<MCP_PORT>/sse` & `POST http://<server-ip>:<MCP_PORT>/messages/`
* **Generated Audio Media**: `GET http://<server-ip>:<MCP_PORT>/media/{filename}` *(temporary `.wav` files, 24h TTL)*

---

## 2. Client Connection Setup

End users connect to this server remotely without installing Python, Docker, or any local dependencies.

### Connecting in Claude Code (Streamable HTTP)
```bash
claude mcp add --transport http pusattokenai https://mcp.pusattokenai.com/mcp \
  --header "Authorization: Bearer sk-your-pusattokenai-api-key"
```

### Connecting in Cherry Studio
1. Open **Settings → Tools → MCP → `+ Add`**.
2. Select **Streamable HTTP** (recommended) or **SSE**.
3. Configure the connection fields:
   * **Name**: `PusatTokenAI`
   * **Type**: `Streamable HTTP` or `SSE`
   * **Server URL**: `https://mcp.pusattokenai.com/mcp` (or `/sse` for legacy SSE)
   * **Headers**:
     * Key: `Authorization`
     * Value: `Bearer sk-your-pusattokenai-api-key`
4. Toggle the server to **Active / Enabled**.

---

## 3. Available Tools & Configuration Options

End users configure models, resolutions, voices, and settings dynamically per request directly through natural language or tool arguments in chat.

### Tool 1: `generate_text`
Handles text completions, coding, deep analysis, and chain-of-thought reasoning.

| Parameter | Type | Required | Default | Available Options / Examples |
| :--- | :--- | :--- | :--- | :--- |
| `prompt` | string | **Yes** | — | Any question, instruction, or reasoning task. |
| `model` | string | No | `gemini-3.8-flash` | `gemini-3.8-flash`, `gpt-4o`, `claude-sonnet-5-5`, `deepseek-v4-flash` |
| `system_prompt` | string | No | `None` | Optional persona or system-level constraints. |
| `temperature` | float | No | `0.7` | `0.0` (strict/coding) to `1.0` (creative). |

**Chat Prompt Example**:
> *"Use generate_text with model gemini-3.8-flash to explain quantum computing in 2 sentences."*

---

### Tool 2: `generate_image`
Generates high-resolution images from text descriptions.

| Parameter | Type | Required | Default | Available Options / Examples |
| :--- | :--- | :--- | :--- | :--- |
| `prompt` | string | **Yes** | — | Detailed visual description of the subject, style, and lighting. |
| `model` | string | No | `seedream-4.5` | `seedream-4.5`, `seedream-5.0-pro`, `gpt-image-2.5-flare`, `qwen-image-2.0-pro` |
| `size` | string | No | `1024x1024` | `1024x1024` (Square), `768x1024` (Portrait), `1024x768` (Landscape) |
| `n` | integer | No | `1` | Number of images to generate (e.g. `1` to `4`). |

**Chat Prompt Example**:
> *"Use generate_image to create an image of a cybernetic cat in neon Tokyo."*

---

### Tool 3: `generate_audio`
Generates realistic speech audio (Text-to-Speech) saved as a temporary `.wav` file and returned as a lightweight downloadable HTTP URL (`/media/{filename}`) to avoid bloating chat context.

| Parameter | Type | Required | Default | Available Options / Examples |
| :--- | :--- | :--- | :--- | :--- |
| `text` | string | **Yes** | — | The sentence, paragraph, or phrase to be read aloud. |
| `model` | string | No | `qwen3.5-omni-flash` | `qwen3.5-omni-flash`, `qwen-audio-3.0-realtime-flash` |
| `voice` | string | No | `Serena` | `Serena` (Warm Female), `Ethan` (Natural Male) |

**Chat Prompt Example**:
> *"Use generate_audio with Serena voice to read aloud: Welcome to PusatTokenAI, your frontier AI platform."*

---

### Tool 4: `generate_video`
Generates videos from text prompts or reference images using asynchronous video models. Polls up to `wait_seconds` and either returns the completed video URL or a `task_id` to check via `get_video_status`.

| Parameter | Type | Required | Default | Available Options / Examples |
| :--- | :--- | :--- | :--- | :--- |
| `prompt` | string | **Yes** | — | Detailed description of the desired video scene and motion. |
| `model` | string | No | `seedance-2.0-fast` | `seedance-2.0-fast`, `seedance-2.0`, `kling-3.0-turbo` |
| `duration` | integer | No | `4` | Video duration in seconds (e.g., `3`, `4`, `5`, `10`). |
| `resolution` | string | No | `480p` | `480p`, `720p`, `1080p` |
| `ratio` | string | No | `16:9` | `16:9`, `9:16`, `1:1` |
| `image_url` | string | No | `None` | Optional reference/first-frame image URL for image-to-video. |
| `generate_audio` | boolean | No | `None` | Optional flag to enable/disable native audio generation. |
| `wait_seconds` | integer | No | `45` | Max seconds to poll before returning a pending `task_id`. |

**Chat Prompt Example**:
> *"Use generate_video to create a 4s 480p 16:9 video of a drone flying over a misty tropical waterfall at sunrise."*

---

### Tool 5: `get_video_status`
Polls the status and retrieves the video URL of a pending video generation task returned by `generate_video`.

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `task_id` | string | **Yes** | — | The `task_id` returned by `generate_video`. |

---

## 4. Local Execution (CLI / Stdio Mode)

For power users who prefer running the server locally via standard I/O instead of Docker:

```bash
pip install -r requirements.txt

# Run via stdio transport
python3 -m src.cli --api-key "sk-your-api-key"
```

In Cherry Studio / Claude Desktop local settings:
```json
{
  "name": "pusattokenai",
  "command": "python3",
  "args": ["-m", "src.cli"],
  "env": {
    "PUSATTOKENAI_API_KEY": "sk-your-api-key"
  }
}
```
