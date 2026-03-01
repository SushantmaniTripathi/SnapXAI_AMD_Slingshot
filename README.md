# SnapXAI – Product Catalog Generator

An AI system that converts any raw product photo into a ready-to-publish catalog listing automatically.

---

## Features

- 📸 **Drag-and-drop** product image upload (JPEG, PNG, WebP, GIF)
- 🤖 **GPT-4o Vision** powered analysis and copywriting
- 📋 **Structured output**: title, category, description, bullet points, tags, price range, condition, color, material, and target audience
- 📄 **One-click copy** the full listing to clipboard
- ⚡ **FastAPI** backend with a clean single-page UI

---

## Quick Start

### 1. Clone and install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure your OpenAI API key

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Run the server

```bash
python run.py
```

Open your browser at **http://localhost:8000**

---

## API

### `POST /api/generate`

Upload a product image and receive a JSON catalog listing.

**Request** – `multipart/form-data`

| Field | Type        | Description                              |
|-------|-------------|------------------------------------------|
| file  | File (image)| Product photo (JPEG/PNG/WebP/GIF, ≤10 MB)|

**Response** – `application/json`

```json
{
  "success": true,
  "listing": {
    "title": "Stylish Red Ceramic Mug",
    "category": "Kitchen & Dining",
    "short_description": "...",
    "long_description": "...",
    "bullet_points": ["...", "..."],
    "suggested_tags": ["mug", "ceramic", "..."],
    "suggested_price_range": "$12 - $20",
    "condition": "New",
    "target_audience": "Coffee enthusiasts",
    "color": "Red",
    "material": "Ceramic"
  },
  "image_filename": "product.jpg",
  "error": null
}
```

### `GET /health`

Returns `{"status": "ok"}`.

---

## Project Structure

```
├── app/
│   ├── __init__.py
│   ├── main.py        # FastAPI application & routes
│   ├── catalog.py     # AI vision catalog generation logic
│   └── models.py      # Pydantic request/response models
├── static/
│   ├── style.css      # UI styles
│   └── app.js         # Frontend logic
├── templates/
│   └── index.html     # Single-page UI
├── tests/
│   └── test_catalog.py
├── .env.example
├── requirements.txt
└── run.py             # Uvicorn entry point
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Environment Variables

| Variable       | Required | Default   | Description                           |
|----------------|----------|-----------|---------------------------------------|
| `OPENAI_API_KEY` | ✅ Yes | –         | OpenAI API key                        |
| `OPENAI_MODEL`  | No       | `gpt-4o`  | Vision-capable OpenAI model to use    |
| `HOST`          | No       | `0.0.0.0` | Uvicorn bind host                     |
| `PORT`          | No       | `8000`    | Uvicorn bind port                     |

