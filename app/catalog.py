"""Core catalog generation logic using OpenAI GPT-4 Vision."""

import base64
import json
import os
from io import BytesIO
from typing import Optional

from openai import OpenAI
from PIL import Image

from .models import CatalogListing

# System prompt that instructs the model to act as a catalog copywriter
_SYSTEM_PROMPT = """You are an expert e-commerce catalog copywriter and product photographer assistant.
When given a product image, you analyze it thoroughly and produce a professional, ready-to-publish
catalog listing in JSON format.

Always return ONLY a valid JSON object — no markdown fences, no extra text — matching this schema:
{
  "title": "<short compelling product title, max 80 chars>",
  "category": "<product category>",
  "short_description": "<one-sentence marketing summary>",
  "long_description": "<full 2-3 paragraph catalog description>",
  "bullet_points": ["<feature 1>", "<feature 2>", "..."],
  "suggested_tags": ["<tag1>", "<tag2>", "..."],
  "suggested_price_range": "<price range or null>",
  "condition": "<New | Like New | Used | Unknown>",
  "target_audience": "<primary audience or null>",
  "color": "<primary color(s) or null>",
  "material": "<apparent material(s) or null>"
}

Rules:
- bullet_points: 3 to 6 items
- suggested_tags: 5 to 10 items
- Be accurate; do not invent features that are not visible in the image
- Write persuasive but honest marketing copy
"""

_USER_PROMPT = (
    "Please analyze this product image and generate a complete catalog listing."
)


def _encode_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """Return a base64-encoded data URL for the given image bytes."""
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type}:{encoded}"


def _normalise_image(image_bytes: bytes, max_side: int = 1024) -> tuple[bytes, str]:
    """Resize image if it exceeds max_side and convert to JPEG to reduce token cost."""
    img = Image.open(BytesIO(image_bytes))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue(), "image/jpeg"


def generate_catalog_listing(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    model: str = "gpt-4o",
    api_key: Optional[str] = None,
) -> CatalogListing:
    """Analyze *image_bytes* with GPT-4 Vision and return a :class:`CatalogListing`.

    Parameters
    ----------
    image_bytes:
        Raw bytes of the uploaded product image.
    mime_type:
        MIME type of the original upload (used only before normalisation).
    model:
        OpenAI model to use.  Must support vision input.
    api_key:
        OpenAI API key.  Falls back to ``OPENAI_API_KEY`` env variable.

    Raises
    ------
    ValueError
        If the model response cannot be parsed into a valid :class:`CatalogListing`.
    """
    resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=resolved_key)

    # Normalise the image for cost/latency efficiency
    jpeg_bytes, jpeg_mime = _normalise_image(image_bytes)
    data_url = _encode_image(jpeg_bytes, jpeg_mime)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url, "detail": "high"},
                    },
                    {"type": "text", "text": _USER_PROMPT},
                ],
            },
        ],
        max_tokens=1024,
        temperature=0.4,
    )

    raw = response.choices[0].message.content or ""
    # Strip markdown code fences if the model wrapped the JSON
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned non-JSON output: {raw[:200]}") from exc

    return CatalogListing(**data)
