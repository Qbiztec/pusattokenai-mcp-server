# Image Modality Handler. Interfaces with /v1/images/generations for text-to-image models.

import os
from typing import Optional, Dict, Any, List
import httpx

BASE_URL = "https://www.pusattokenai.com/v1"
DEFAULT_IMAGE_MODEL = "seedream-4.5"


async def generate_image(
    prompt: str,
    api_key: Optional[str] = None,
    model: str = DEFAULT_IMAGE_MODEL,
    size: str = "1024x1024",
    n: int = 1,
    response_format: str = "url",
    timeout: float = 90.0,
) -> Dict[str, Any]:
    """Generates images using text-to-image models available on PusatTokenAI.

    Args:
        prompt: Detailed description of the desired image.
        api_key: User's PusatTokenAI API key.
        model: Model name (default: 'seedream-4.5').
        size: Target resolution (default: '1024x1024').
        n: Number of images to generate (default 1).
        response_format: 'url' (hosted link) or 'b64_json'.
        timeout: Request timeout in seconds.

    Returns:
        Dict containing status, generated image URLs or base64 data, model, and prompt.
    """
    token = api_key or os.getenv("PUSATTOKENAI_API_KEY")
    if not token:
        return {
            "status": "error",
            "message": "Missing API key. Provide api_key or send Authorization header from your MCP client.",
        }

    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "n": n,
        "response_format": response_format,
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    url = f"{BASE_URL}/images/generations"

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            images: List[str] = []
            for item in data.get("data", []):
                if response_format == "url" and "url" in item:
                    images.append(item["url"])
                elif "b64_json" in item:
                    images.append(item["b64_json"])

            return {
                "status": "success",
                "model": model,
                "prompt": prompt,
                "images": images,
                "count": len(images),
                "created": data.get("created"),
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
