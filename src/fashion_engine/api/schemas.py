from datetime import datetime
from pydantic import BaseModel


class ChannelOut(BaseModel):
    id: int
    name: str
    url: str
    channel_type: str | None
    country: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class BrandOut(BaseModel):
    id: int
    name: str
    slug: str
    name_ko: str | None
    origin_country: str | None
    official_url: str | None
    tier: str | None
    description_ko: str | None

    model_config = {"from_attributes": True}


class BrandWithChannels(BrandOut):
    channels: list[ChannelOut] = []


class ChannelWithBrands(ChannelOut):
    brands: list[BrandOut] = []


class CollabOut(BaseModel):
    id: int
    brand_a_id: int
    brand_b_id: int
    collab_name: str
    collab_category: str | None
    release_year: int | None
    hype_score: int
    source_url: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LandscapeNode(BaseModel):
    id: int
    name: str
    slug: str
    tier: str | None
    channel_count: int
    channels: list[str]


class LandscapeEdge(BaseModel):
    brand_id: int
    channel_id: int


class BrandLandscape(BaseModel):
    nodes: list[LandscapeNode]
    edges: list[LandscapeEdge]
    stats: dict


class ChannelLandscapeItem(BaseModel):
    id: int
    name: str
    country: str | None
    channel_type: str | None
    brand_count: int
    top_tiers: list[str]


class ChannelLandscape(BaseModel):
    channels: list[ChannelLandscapeItem]
    stats: dict


# ── 제품 / 가격 스키마 ─────────────────────────────────────────────────────

class PriceHistoryOut(BaseModel):
    id: int
    price: float
    original_price: float | None
    currency: str
    is_sale: bool
    discount_rate: int | None
    crawled_at: datetime

    model_config = {"from_attributes": True}


class ProductOut(BaseModel):
    id: int
    channel_id: int
    brand_id: int | None
    name: str
    product_key: str | None
    url: str
    image_url: str | None
    is_sale: bool
    is_active: bool

    model_config = {"from_attributes": True}


class ProductDetailOut(ProductOut):
    channel: ChannelOut
    brand: BrandOut | None


class PriceComparisonItem(BaseModel):
    channel_name: str
    channel_country: str | None
    channel_url: str
    price_krw: int
    original_price_krw: int | None
    is_sale: bool
    discount_rate: int | None
    product_url: str
    image_url: str | None


class PriceComparisonOut(BaseModel):
    product_key: str
    product_name: str
    listings: list[PriceComparisonItem]
    cheapest_channel: str | None
    cheapest_price_krw: int | None
    total_listings: int
