"""Pydantic models for catalog listing output."""

from typing import List, Optional
from pydantic import BaseModel, Field


class CatalogListing(BaseModel):
    """Structured catalog listing generated from a product image."""

    title: str = Field(..., description="Short, compelling product title (max 80 chars)")
    category: str = Field(..., description="Product category (e.g. Electronics, Clothing)")
    short_description: str = Field(
        ..., description="One-sentence marketing summary of the product"
    )
    long_description: str = Field(
        ..., description="Full catalog description (2-3 paragraphs)"
    )
    bullet_points: List[str] = Field(
        ..., description="3-6 key feature bullet points", min_length=1, max_length=6
    )
    suggested_tags: List[str] = Field(
        ..., description="SEO/search tags for the listing", min_length=1, max_length=10
    )
    suggested_price_range: Optional[str] = Field(
        None, description="Estimated retail price range (e.g. '$20 - $35')"
    )
    condition: Optional[str] = Field(
        None, description="Apparent product condition (New / Like New / Used / Unknown)"
    )
    target_audience: Optional[str] = Field(
        None, description="Primary target audience for the product"
    )
    color: Optional[str] = Field(None, description="Primary color(s) observed")
    material: Optional[str] = Field(None, description="Apparent material(s)")


class CatalogResponse(BaseModel):
    """API response wrapper for a catalog listing."""

    success: bool
    listing: Optional[CatalogListing] = None
    error: Optional[str] = None
    image_filename: Optional[str] = None
