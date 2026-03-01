"""Unit tests for the SnapXAI catalog generator."""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.catalog import _encode_image, _normalise_image, generate_catalog_listing
from app.main import app
from app.models import CatalogListing, CatalogResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_jpeg_bytes(width: int = 200, height: int = 200) -> bytes:
    """Create a tiny JPEG image in memory."""
    img = Image.new("RGB", (width, height), color=(255, 120, 50))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def make_png_bytes(width: int = 100, height: int = 100) -> bytes:
    """Create a tiny PNG image in memory."""
    img = Image.new("RGB", (width, height), color=(50, 100, 200))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


_SAMPLE_LISTING = {
    "title": "Stylish Red Ceramic Mug",
    "category": "Kitchen & Dining",
    "short_description": "A vibrant red ceramic mug perfect for your morning coffee.",
    "long_description": "Start your mornings right with this beautifully crafted red ceramic mug. "
    "Made from high-quality stoneware, it retains heat longer than standard mugs. "
    "Dishwasher and microwave safe.\n\n"
    "The ergonomic handle ensures a comfortable grip, while the bold colour adds a "
    "pop of personality to your kitchen cupboard.",
    "bullet_points": [
        "Premium stoneware ceramic",
        "Heat-retaining design keeps drinks warm longer",
        "Dishwasher & microwave safe",
        "Comfortable ergonomic handle",
        "Bold red finish",
    ],
    "suggested_tags": ["mug", "ceramic", "coffee", "red", "kitchen", "drinkware"],
    "suggested_price_range": "$12 - $20",
    "condition": "New",
    "target_audience": "Coffee and tea enthusiasts",
    "color": "Red",
    "material": "Ceramic / Stoneware",
}


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestCatalogListing:
    def test_valid_listing(self):
        listing = CatalogListing(**_SAMPLE_LISTING)
        assert listing.title == "Stylish Red Ceramic Mug"
        assert len(listing.bullet_points) == 5
        assert len(listing.suggested_tags) == 6

    def test_optional_fields_nullable(self):
        minimal = {
            "title": "Test Product",
            "category": "General",
            "short_description": "A test product.",
            "long_description": "This is a test product description.",
            "bullet_points": ["Feature A"],
            "suggested_tags": ["test"],
        }
        listing = CatalogListing(**minimal)
        assert listing.suggested_price_range is None
        assert listing.condition is None
        assert listing.color is None

    def test_catalog_response_success(self):
        listing = CatalogListing(**_SAMPLE_LISTING)
        response = CatalogResponse(success=True, listing=listing, image_filename="mug.jpg")
        assert response.success is True
        assert response.listing is not None
        assert response.error is None

    def test_catalog_response_failure(self):
        response = CatalogResponse(success=False, error="Something went wrong")
        assert response.success is False
        assert response.listing is None
        assert response.error == "Something went wrong"


# ---------------------------------------------------------------------------
# Catalog generation helper tests
# ---------------------------------------------------------------------------


class TestEncodeImage:
    def test_returns_data_url(self):
        data = b"fake_image_bytes"
        result = _encode_image(data, "image/jpeg")
        assert result.startswith("data:image/jpeg:")
        assert len(result) > 20

    def test_base64_roundtrip(self):
        import base64

        data = b"hello world"
        result = _encode_image(data, "image/png")
        prefix = "data:image/png:"
        encoded = result[len(prefix):]
        assert base64.b64decode(encoded) == data


class TestNormaliseImage:
    def test_jpeg_output(self):
        img_bytes = make_jpeg_bytes(300, 300)
        out_bytes, mime = _normalise_image(img_bytes)
        assert mime == "image/jpeg"
        img = Image.open(BytesIO(out_bytes))
        assert img.format == "JPEG"

    def test_large_image_resized(self):
        img_bytes = make_jpeg_bytes(2000, 2000)
        out_bytes, _ = _normalise_image(img_bytes, max_side=512)
        img = Image.open(BytesIO(out_bytes))
        assert max(img.size) <= 512

    def test_small_image_not_upscaled(self):
        img_bytes = make_jpeg_bytes(100, 100)
        out_bytes, _ = _normalise_image(img_bytes, max_side=1024)
        img = Image.open(BytesIO(out_bytes))
        assert max(img.size) <= 100

    def test_png_converted_to_jpeg(self):
        img_bytes = make_png_bytes(200, 200)
        out_bytes, mime = _normalise_image(img_bytes)
        assert mime == "image/jpeg"
        img = Image.open(BytesIO(out_bytes))
        assert img.format == "JPEG"


class TestGenerateCatalogListing:
    def _make_mock_client(self, payload: dict) -> MagicMock:
        """Return a mock OpenAI client that yields *payload* as JSON content."""
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(payload)
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    @patch("app.catalog.OpenAI")
    def test_returns_catalog_listing(self, mock_openai_cls):
        mock_openai_cls.return_value = self._make_mock_client(_SAMPLE_LISTING)
        result = generate_catalog_listing(make_jpeg_bytes(), api_key="test-key")
        assert isinstance(result, CatalogListing)
        assert result.title == "Stylish Red Ceramic Mug"
        assert result.category == "Kitchen & Dining"

    @patch("app.catalog.OpenAI")
    def test_strips_markdown_fences(self, mock_openai_cls):
        """Model sometimes wraps JSON in ```json ... ``` fences."""
        wrapped = f"```json\n{json.dumps(_SAMPLE_LISTING)}\n```"
        mock_choice = MagicMock()
        mock_choice.message.content = wrapped
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        result = generate_catalog_listing(make_jpeg_bytes(), api_key="test-key")
        assert isinstance(result, CatalogListing)

    @patch("app.catalog.OpenAI")
    def test_raises_on_invalid_json(self, mock_openai_cls):
        mock_choice = MagicMock()
        mock_choice.message.content = "this is not json"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        with pytest.raises(ValueError, match="non-JSON"):
            generate_catalog_listing(make_jpeg_bytes(), api_key="test-key")


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


client = TestClient(app)


class TestHealthEndpoint:
    def test_health_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestIndexEndpoint:
    def test_index_returns_html(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "SnapXAI" in response.text


class TestGenerateEndpoint:
    def test_no_api_key_returns_503(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        jpeg_bytes = make_jpeg_bytes()
        response = client.post(
            "/api/generate",
            files={"file": ("product.jpg", BytesIO(jpeg_bytes), "image/jpeg")},
        )
        assert response.status_code == 503

    def test_unsupported_mime_returns_415(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        response = client.post(
            "/api/generate",
            files={"file": ("product.txt", BytesIO(b"hello"), "text/plain")},
        )
        assert response.status_code == 415

    def test_file_too_large_returns_413(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        big_data = b"x" * (10 * 1024 * 1024 + 1)
        response = client.post(
            "/api/generate",
            files={"file": ("big.jpg", BytesIO(big_data), "image/jpeg")},
        )
        assert response.status_code == 413

    @patch("app.main.generate_catalog_listing")
    def test_successful_generation(self, mock_gen, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        mock_gen.return_value = CatalogListing(**_SAMPLE_LISTING)
        jpeg_bytes = make_jpeg_bytes()
        response = client.post(
            "/api/generate",
            files={"file": ("product.jpg", BytesIO(jpeg_bytes), "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["listing"]["title"] == "Stylish Red Ceramic Mug"
        assert data["image_filename"] == "product.jpg"

    @patch("app.main.generate_catalog_listing")
    def test_catalog_generation_error_returns_failure(self, mock_gen, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        mock_gen.side_effect = ValueError("Model returned non-JSON output")
        jpeg_bytes = make_jpeg_bytes()
        response = client.post(
            "/api/generate",
            files={"file": ("product.jpg", BytesIO(jpeg_bytes), "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "non-JSON" in data["error"]
