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

    model_config = {"from_attributes": True}


class BrandWithChannels(BrandOut):
    channels: list[ChannelOut] = []


class ChannelWithBrands(ChannelOut):
    brands: list[BrandOut] = []
