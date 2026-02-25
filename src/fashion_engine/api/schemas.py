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
