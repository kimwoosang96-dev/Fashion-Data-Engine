# 모든 모델을 여기서 임포트하여 SQLAlchemy mapper가 관계를 올바르게 해석하도록 함
from fashion_engine.models.channel import Channel
from fashion_engine.models.brand import Brand
from fashion_engine.models.channel_brand import ChannelBrand
from fashion_engine.models.category import Category
from fashion_engine.models.price_history import PriceHistory
from fashion_engine.models.product import Product

__all__ = ["Channel", "Brand", "ChannelBrand", "Category", "PriceHistory", "Product"]
