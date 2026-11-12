# PusatTokenAI MCP Server

A modular Model Context Protocol (MCP) server providing access to frontier models on PusatTokenAI.

## Supported Modalities & Tools

| Modality | Tool Name | Target Endpoint | Default Model | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Text** | `generate_text` | `POST /v1/chat/completions` | `deepseek-r1` | Text completions, coding, and reasoning. |
| **Image** | `generate_image` | `POST /v1/images/generations` | `seedream-4.5` | Text-to-Image generation at custom resolutions. |

---

## Deployment (Docker & SSE)

### 1. Using Docker Compose (Recommended)
```bash
# Copy environment configuration
cp .env.example .env

# Start container
docker compose up -d --build
```
The server will start at `http://localhost:8088` (configurable via `MCP_PORT` in `.env`):
* Health check: `GET http://localhost:8088/health`
* SSE Endpoint: `GET http://localhost:8088/sse`
* Messages: `POST http://localhost:8088/messages`

### 2. Running Locally with Python
```bash
pip install -r requirements.txt
export PUSATTOKENAI_API_KEY="sk-..."
export PORT=8088
uvicorn src.server:app --host 0.0.0.0 --port 8088
```

---

## Client Configuration (Cherry Studio / Claude Desktop)

### Option A: Remote SSE (Zero-Install for End Users)
In Cherry Studio:
1. Go to **Settings → Tools → MCP → `+ Add`**.
2. Select **Remote (SSE)**.
3. Configure:
   * **URL**: `http://<your-server-ip>:8088/sse` (or `https://mcp.pusattokenai.com/sse`)
   * **Headers**:
     * `Authorization`: `Bearer sk-your-api-key`

### Option B: Local Stdio Command
If running locally on your own machine:
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
