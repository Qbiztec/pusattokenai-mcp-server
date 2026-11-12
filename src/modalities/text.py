# Text Modality Handler. Interfaces with /v1/chat/completions for text generation and reasoning models.

import os
from typing import Optional, Dict, Any
import httpx

DEFAULT_BASE_URL = "https://www.pusattokenai.com/v1"
DEFAULT_TEXT_MODEL = "deepseek-r1"


async def generate_text(
    prompt: str,
    api_key: Optional[str] = None,
    model: str = DEFAULT_TEXT_MODEL,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """
    Args:
        prompt: User instruction or question.
        api_key: PusatTokenAI API key. Defaults to PUSATTOKENAI_API_KEY env var.
        model: Model identifier (e.g., 'deepseek-r1', 'gpt-4o', 'claude-3-5-sonnet').
        system_prompt: Optional system persona or instructions.
        temperature: Sampling temperature (0.0 to 1.0).
        base_url: Gateway base URL.
        timeout: Request timeout in seconds.

    Returns:
        Dict containing status, response text, model used, and token usage metrics.
    """
    token = api_key or os.getenv("PUSATTOKENAI_API_KEY")
    if not token:
        return {
            "status": "error",
            "message": "Missing API key. Provide api_key parameter or set PUSATTOKENAI_API_KEY.",
        }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    url = f"{base_url.rstrip('/')}/chat/completions"

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            reasoning = message.get("reasoning_content")

            return {
                "status": "success",
                "model": data.get("model", model),
                "text": content,
                "reasoning": reasoning,
                "usage": data.get("usage", {}),
            }

        except httpx.HTTPStatusError as e:
            return {
                "status": "error",
                "status_code": e.response.status_code,
                "message": f"Gateway HTTP error: {e.response.text}",
            }
        except httpx.RequestError as e:
            return {
                "status": "error",
                "message": f"Connection error: {str(e)}",
            }
