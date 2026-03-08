from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field


class ChannelOut(BaseModel):
    id: int
    name: str
    url: str
    channel_type: str | None
    platform: str | None
    country: str | None
    instagram_url: str | None
    poll_priority: int
    use_gpt_parser: bool = False
    is_active: bool

    model_config = {"from_attributes": True}


class BrandOut(BaseModel):
    id: int
    name: str
    slug: str
    name_ko: str | None
    origin_country: str | None
    official_url: str | None
    instagram_url: str | None
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


class BrandDirectorOut(BaseModel):
    id: int
    brand_id: int
    brand_name: str | None = None
    brand_slug: str | None = None
    name: str
    role: str
    start_year: int | None
    end_year: int | None
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DirectorsByBrand(BaseModel):
    brand_slug: str
    brand_name: str
    current_directors: list[BrandDirectorOut]
    past_directors: list[BrandDirectorOut]


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
    normalized_key: str | None
    match_confidence: float | None
    gender: str | None
    subcategory: str | None
    url: str
    image_url: str | None
    price_krw: int | None = None
    original_price_krw: int | None = None
    discount_rate: int | None = None
    currency: str | None = None
    price_updated_at: datetime | None = None
    sale_started_at: datetime | None = None
    is_sale: bool
    is_active: bool
    archived_at: datetime | None

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
    total_channels: int


class ChannelHighlightOut(BaseModel):
    channel_id: int
    channel_name: str
    channel_url: str
    instagram_url: str | None
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
    instagram_url: str | None
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
    channel_type: str | None
    is_official: bool
    price_krw: int
    original_price_krw: int | None
    is_sale: bool
    discount_rate: int | None
    product_url: str
    image_url: str | None


class PriceComparisonOut(BaseModel):
    product_key: str
    product_name: str
    brand_name: str | None = None
    image_url: str | None = None
    listings: list[PriceComparisonItem]
    cheapest_channel: str | None
    cheapest_price_krw: int | None
    total_listings: int


class ProductKeyOut(BaseModel):
    product_key: str


class SearchSuggestionOut(BaseModel):
    type: Literal["brand", "product"]
    label: str
    slug: str | None = None
    product_key: str | None = None
    channel_name: str | None = None
    product_url: str | None = None


class ProductRankingOut(BaseModel):
    product_key: str | None
    product_name: str
    brand_name: str | None
    image_url: str | None
    channel_name: str
    channel_country: str | None
    product_url: str
    price_krw: int
    original_price_krw: int | None
    discount_rate: int | None
    total_channels: int
    price_drop_pct: float | None = None
    price_drop_krw: int | None = None
    sale_started_at: datetime | None = None
    hours_since_sale_start: float | None = None
    badges: list[str] = Field(default_factory=list)


class BrandRankingOut(BaseModel):
    brand_id: int
    brand_name: str
    brand_slug: str
    tier: str | None
    origin_country: str | None
    sale_product_count: int
    avg_discount_rate: float
    max_discount_rate: int | None
    active_channel_count: int
    event_count_72h: int = 0
    latest_event_at: datetime | None = None


class MultiChannelProductOut(BaseModel):
    product_key: str
    product_name: str
    image_url: str | None
    channel_count: int
    min_price_krw: int
    max_price_krw: int
    price_spread_krw: int
    spread_rate_pct: float


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


class DropsCalendarEntryOut(BaseModel):
    brand_name: str | None = None
    title: str
    event_type: str
    source_url: str | None = None


class BrandsHeatmapBrandOut(BaseModel):
    id: int
    name: str
    slug: str
    tier: str | None = None


class BrandsHeatmapChannelOut(BaseModel):
    id: int
    name: str
    country: str | None = None


class BrandsHeatmapCellOut(BaseModel):
    brand_id: int
    channel_id: int
    discount_rate: float
    product_count: int


class BrandsHeatmapOut(BaseModel):
    brands: list[BrandsHeatmapBrandOut]
    channels: list[BrandsHeatmapChannelOut]
    cells: list[BrandsHeatmapCellOut]


class CrawlChannelLogOut(BaseModel):
    id: int
    channel_id: int
    channel_name: str
    status: str
    products_found: int
    products_new: int
    products_updated: int
    error_msg: str | None
    error_type: str | None
    strategy: str | None
    duration_ms: int
    crawled_at: datetime

    model_config = {"from_attributes": True}


class CrawlRunOut(BaseModel):
    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    total_channels: int
    done_channels: int
    new_products: int
    updated_products: int
    error_channels: int
    gpt_fallback_count: int = 0

    model_config = {"from_attributes": True}


class CrawlRunDetail(CrawlRunOut):
    logs: list[CrawlChannelLogOut]


class ChannelSignalOut(BaseModel):
    channel_id: int
    name: str
    channel_type: str | None
    country: str | None
    poll_priority: int
    product_count: int
    active_count: int
    inactive_count: int
    last_crawled_at: str | None
    crawl_status: str
    recent_success_rate: float
    last_error_msg: str | None
    error_type: str | None = None
    traffic_light: str


# ── ChannelNote 스키마 ────────────────────────────────────────────────────────


class ChannelNoteOut(BaseModel):
    id: int
    channel_id: int
    channel_name: str
    note_type: str
    body: str
    operator: str
    created_at: datetime
    resolved_at: datetime | None


class IntelEventOut(BaseModel):
    id: int
    event_type: str
    layer: str
    title: str
    summary: str | None
    event_time: str | None
    detected_at: str
    severity: str
    confidence: str
    brand_id: int | None
    brand_name: str | None
    brand_slug: str | None
    channel_id: int | None
    channel_name: str | None
    product_id: int | None
    product_name: str | None
    product_key: str | None
    geo_country: str | None
    geo_city: str | None
    geo_lat: float | None
    geo_lng: float | None
    geo_precision: str
    source_url: str | None
    source_domain: str | None
    source_type: str
    is_verified: bool


class IntelEventsPage(BaseModel):
    items: list[IntelEventOut]
    next_cursor: str | None
    total: int


class IntelMapPointOut(BaseModel):
    id: int
    layer: str
    severity: str
    confidence: str
    lat: float
    lng: float
    title: str
    event_time: str
    geo_precision: str


class IntelTimelineBucket(BaseModel):
    bucket: str
    total: int
    layers: dict[str, int]


class IntelTimelineOut(BaseModel):
    granularity: str
    items: list[IntelTimelineBucket]


class ChannelNoteCreate(BaseModel):
    note_type: str = "observation"
    body: str
    operator: str = "admin"


class ActivityFeedItemOut(BaseModel):
    id: int
    event_type: str
    product_name: str | None
    brand_name: str | None
    channel_name: str | None
    price_krw: int | None
    discount_rate: int | None
    source_url: str | None
    image_url: str | None
    product_key: str | None
    detected_at: datetime


class FeedIngestIn(BaseModel):
    event_type: Literal["sale_start", "new_drop", "price_cut", "sold_out", "restock"]
    brand_slug: str | None = None
    product_name: str
    price_krw: int | None = None
    discount_rate: int | None = None
    source_url: str
    image_url: str | None = None
    notes: str | None = None
    detected_at: datetime | None = None


class SearchV2ItemOut(BaseModel):
    id: int
    product_key: str | None
    normalized_key: str | None = None
    product_name: str
    brand_name: str | None
    channel_name: str | None
    url: str
    image_url: str | None
    price_krw: int | None
    similarity: float | None = None


class BrandSaleChannelOut(BaseModel):
    channel_name: str
    url: str
    products_on_sale: int


class BrandSaleHistoryOut(BaseModel):
    month: str
    product_count: int
    avg_discount: float | None


class BrandSaleIntelOut(BaseModel):
    brand_slug: str
    brand_name: str
    is_currently_on_sale: bool
    current_sale_products: int
    current_max_discount_rate: int | None
    sale_channels: list[BrandSaleChannelOut]
    monthly_sale_history: list[BrandSaleHistoryOut]
    last_sale_started_at: datetime | None
    typical_sale_months: list[int]


class CrossChannelPriceHistoryPointOut(BaseModel):
    date: date
    channel_name: str
    price_krw: int
    is_sale: bool


class CrossChannelPriceHistoryOut(BaseModel):
    product_key: str
    product_name: str
    history: list[CrossChannelPriceHistoryPointOut]
    all_time_low: CrossChannelPriceHistoryPointOut | None
    current_lowest: CrossChannelPriceHistoryPointOut | None
    price_trend: Literal["falling", "stable", "rising"]


class ProductAvailabilityChannelOut(BaseModel):
    channel_name: str
    channel_country: str | None
    channel_url: str
    product_url: str
    price_krw: int | None
    original_price_krw: int | None
    discount_rate: int | None
    stock_status: str | None
    size_availability: list[dict] | None
    is_sale: bool
    image_url: str | None


class ProductAvailabilityOut(BaseModel):
    product_key: str
    normalized_key: str | None
    product_name: str
    brand_name: str | None
    image_url: str | None
    in_stock_anywhere: bool
    lowest_price: ProductAvailabilityChannelOut | None
    channels: list[ProductAvailabilityChannelOut]


class AdminDraftChannelOut(BaseModel):
    id: int
    name: str
    url: str
    channel_type: str | None
    platform: str | None
    country: str | None
    description: str | None
    created_at: datetime
    product_count: int
    poll_priority: int
    use_gpt_parser: bool = False


# ── ProductCatalog 스키마 ────────────────────────────────────────────────────

class CatalogOut(BaseModel):
    id: int
    normalized_key: str
    canonical_name: str
    brand_id: int | None
    brand_name: str | None
    brand_slug: str | None
    gender: str | None
    subcategory: str | None
    tags: str | None
    trend_score: float | None
    listing_count: int
    channel_count: int = 1
    min_price_krw: int | None
    max_price_krw: int | None
    is_sale_anywhere: bool | None
    first_seen_at: datetime

    model_config = {"from_attributes": True}


class CatalogListingOut(BaseModel):
    channel_id: int
    channel_name: str
    channel_url: str
    product_id: int
    product_url: str
    latest_price_krw: int | None
    is_sale: bool
    discount_rate: int | None

    model_config = {"from_attributes": True}


class CatalogDetailOut(CatalogOut):
    listings: list[CatalogListingOut]
