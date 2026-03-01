# 모든 모델을 여기서 임포트하여 SQLAlchemy mapper가 관계를 올바르게 해석하도록 함
from fashion_engine.models.channel import Channel
from fashion_engine.models.brand import Brand
from fashion_engine.models.channel_brand import ChannelBrand
from fashion_engine.models.category import Category
from fashion_engine.models.price_history import PriceHistory
from fashion_engine.models.product import Product
from fashion_engine.models.brand_collaboration import BrandCollaboration
from fashion_engine.models.fashion_news import FashionNews
from fashion_engine.models.exchange_rate import ExchangeRate
from fashion_engine.models.purchase import Purchase
from fashion_engine.models.watchlist import WatchListItem
from fashion_engine.models.drop import Drop
from fashion_engine.models.brand_director import BrandDirector
from fashion_engine.models.crawl_run import CrawlRun, CrawlChannelLog

__all__ = [
    "Channel", "Brand", "ChannelBrand", "Category", "PriceHistory", "Product",
    "BrandCollaboration", "FashionNews", "ExchangeRate",
    "Purchase", "WatchListItem", "Drop",
    "BrandDirector",
    "CrawlRun", "CrawlChannelLog",
]
