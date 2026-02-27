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


class FashionNewsOut(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    entity_name: str | None = None
    title: str
    url: str
    summary: str | None
    published_at: datetime | None
    source: str
    crawled_at: datetime

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
    gender: str | None
    subcategory: str | None
    url: str
    image_url: str | None
    is_sale: bool
    is_active: bool

    model_config = {"from_attributes": True}


class SaleHighlightOut(BaseModel):
    product_id: int
    product_name: str
    product_key: str | None
    product_url: str
    image_url: str | None
    channel_name: str
    channel_country: str | None
    is_new: bool
    is_active: bool
    price_krw: int
    original_price_krw: int | None
    discount_rate: int | None


class ChannelHighlightOut(BaseModel):
    channel_id: int
    channel_name: str
    channel_url: str
    channel_type: str | None
    country: str | None
    total_product_count: int
    sale_product_count: int
    new_product_count: int
    is_running_sales: bool
    is_selling_new_products: bool


class BrandHighlightOut(BaseModel):
    brand_id: int
    brand_name: str
    brand_slug: str
    tier: str | None
    total_product_count: int
    new_product_count: int
    is_selling_new_products: bool


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


class PriceHistoryPoint(BaseModel):
    date: str
    price_krw: int
    is_sale: bool


class ChannelPriceHistory(BaseModel):
    channel_name: str
    history: list[PriceHistoryPoint]


# ── 구매 이력 스키마 ───────────────────────────────────────────────────────────

class PurchaseIn(BaseModel):
    product_key: str
    product_name: str
    brand_slug: str | None = None
    channel_name: str
    channel_url: str | None = None
    paid_price_krw: int
    original_price_krw: int | None = None
    purchased_at: datetime | None = None
    notes: str | None = None


class PurchaseOut(BaseModel):
    id: int
    product_key: str
    product_name: str
    brand_slug: str | None
    channel_name: str
    channel_url: str | None
    paid_price_krw: int
    original_price_krw: int | None
    purchased_at: datetime
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScoreOut(BaseModel):
    purchase_id: int
    product_key: str
    product_name: str
    paid_price_krw: int
    grade: str
    percentile: float | None
    badge: str
    min_ever_krw: int | None
    max_ever_krw: int | None
    avg_krw: int | None
    data_points: int
    savings_vs_full: int | None
    savings_vs_avg: int | None
    verdict: str


class PurchaseStatsOut(BaseModel):
    total_purchases: int
    total_paid_krw: int
    total_savings_vs_full_krw: int
    best_deal: dict | None


# ── 드롭 스키마 ───────────────────────────────────────────────────────────────

class DropIn(BaseModel):
    product_name: str
    source_url: str
    product_key: str | None = None
    brand_id: int | None = None
    image_url: str | None = None
    price_krw: int | None = None
    release_date: datetime | None = None
    status: str = "upcoming"


class DropOut(BaseModel):
    id: int
    brand_id: int | None
    product_name: str
    product_key: str | None
    source_url: str
    image_url: str | None
    price_krw: int | None
    release_date: datetime | None
    status: str
    detected_at: datetime
    notified_at: datetime | None

    model_config = {"from_attributes": True}
