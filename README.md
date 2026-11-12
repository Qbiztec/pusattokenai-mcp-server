# PusatTokenAI MCP Server

A modular Model Context Protocol (MCP) server providing access to frontier text, reasoning, and image generation models hosted on PusatTokenAI.

---

## 1. Quickstart Deployment (Server Host)

The server requires only a single environment setting (`MCP_PORT`):

```bash
# 1. Copy environment template (defaults to port 8088)
cp .env.example .env

# 2. (Optional) Customize host port in .env if needed:
# MCP_PORT=10234

# 3. Start the container
docker compose up -d --build
```

### Endpoints
* **Health Check**: `GET http://<server-ip>:<MCP_PORT>/health`
* **SSE Stream**: `GET http://<server-ip>:<MCP_PORT>/sse`
* **Messages**: `POST http://<server-ip>:<MCP_PORT>/messages`

---

## 2. Client Connection Setup (Cherry Studio / Claude Desktop)

End users connect to this server remotely without installing Python, Docker, or any local dependencies.

### Connecting in Cherry Studio:
1. Open **Settings → Tools → MCP → `+ Add`**.
2. Select **Remote (SSE)**.
3. Configure the connection fields:
   * **Name**: `PusatTokenAI`
   * **Type**: `SSE`
   * **Server URL**: `http://<server-ip>:<MCP_PORT>/sse` (e.g., `http://localhost:8088/sse` or `https://mcp.pusattokenai.com/sse`)
   * **Headers**:
     * Key: `Authorization`
     * Value: `Bearer sk-your-pusattokenai-api-key`
4. Toggle the server to **Active / Enabled**.

---

## 3. Available Tools & Configuration Options

End users configure models, resolutions, and settings dynamically per request directly through natural language or tool arguments in chat.

### Tool 1: `generate_text`
Handles text completions, coding, deep analysis, and chain-of-thought reasoning.

| Parameter | Type | Required | Default | Available Options / Examples |
| :--- | :--- | :--- | :--- | :--- |
| `prompt` | string | **Yes** | — | Any question, instruction, or reasoning task. |
| `model` | string | No | `gemini-3.8-flash` | `gemini-3.8-flash`, `gpt-4o`, `claude-sonnet-5-5`, `deepseek-v4-flash` |
| `system_prompt` | string | No | `None` | Optional persona or system-level constraints. |
| `temperature` | float | No | `0.7` | `0.0` (strict/coding) to `1.0` (creative). |

**Chat Prompt Example**:
> *"Use generate_text with model deepseek-r1 and temperature 0.2 to analyze this SQL schema for bottlenecks."*

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
> *"Use generate_image with model seedream-5.0-pro and size 1024x768 to create a futuristic neon skyline at dusk."*

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
