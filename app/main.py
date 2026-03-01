"""FastAPI application – SnapXAI product catalog generator."""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .catalog import generate_catalog_listing
from .models import CatalogResponse

load_dotenv()

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SnapXAI Catalog Generator",
    description="Convert any raw product photo into a ready-to-publish catalog listing.",
    version="1.0.0",
)

_BASE_DIR = Path(__file__).parent.parent
app.mount("/static", StaticFiles(directory=str(_BASE_DIR / "static")), name="static")

# ---------------------------------------------------------------------------
# Allowed image MIME types
# ---------------------------------------------------------------------------

_ALLOWED_MIME = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Serve the single-page UI."""
    html_path = _BASE_DIR / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/generate", response_model=CatalogResponse)
async def generate(file: UploadFile = File(...)) -> CatalogResponse:
    """Accept a product image and return an AI-generated catalog listing.

    - **file**: JPEG, PNG, WebP or GIF product photo (max 10 MB)
    """
    # Validate MIME type
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{content_type}'. "
            "Please upload a JPEG, PNG, WebP or GIF image.",
        )

    image_bytes = await file.read()

    # Validate file size
    if len(image_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum allowed size is 10 MB.",
        )

    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured. "
            "Please set it in the environment or .env file.",
        )

    try:
        listing = generate_catalog_listing(
            image_bytes=image_bytes,
            mime_type=content_type,
        )
    except ValueError as exc:
        return CatalogResponse(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return CatalogResponse(
            success=False,
            error=f"An unexpected error occurred: {exc}",
        )

    return CatalogResponse(
        success=True,
        listing=listing,
        image_filename=file.filename,
    )


@app.get("/health")
async def health() -> dict:
    """Simple health-check endpoint."""
    return {"status": "ok"}
