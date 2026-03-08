from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.api.schemas import ActivityFeedItemOut, FeedIngestIn
from fashion_engine.config import settings
from fashion_engine.database import get_db
from fashion_engine.services import feed_service, product_service

router = APIRouter(prefix="/feed", tags=["feed"])

_bearer = HTTPBearer(auto_error=False)


async def require_bearer(
    creds: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> None:
    expected = (settings.admin_bearer_token or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="ADMIN_BEARER_TOKEN not configured")
    if creds is None or creds.credentials != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing Bearer token")


@router.get("", response_model=list[ActivityFeedItemOut])
async def list_activity_feed(
    event_type: str | None = Query(None, pattern="^(sale_start|new_drop|price_cut|sold_out|restock)$"),
    brand_id: int | None = Query(None, ge=1),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await feed_service.get_activity_feed(
        db,
        event_type=event_type,
        brand_id=brand_id,
        limit=limit,
        offset=offset,
    )


@router.post("/ingest", response_model=ActivityFeedItemOut, status_code=201)
async def ingest_activity_feed(
    payload: FeedIngestIn,
    _: None = Depends(require_bearer),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await feed_service.ingest_activity_feed(
            db,
            event_type=payload.event_type,
            product_name=payload.product_name,
            source_url=payload.source_url,
            brand_slug=payload.brand_slug,
            price_krw=payload.price_krw,
            discount_rate=payload.discount_rate,
            image_url=payload.image_url,
            notes=payload.notes,
            detected_at=payload.detected_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/google-shopping", response_class=Response)
async def google_shopping_feed(
    db: AsyncSession = Depends(get_db),
):
    products = await product_service.get_sale_products(db, limit=1000)
    items: list[str] = []
    for product in products:
        brand_name = product.brand.name if product.brand else ""
        items.append(
            f"""
    <item>
      <g:id>{product.id}</g:id>
      <title>{escape(product.name)}</title>
      <link>{escape(product.url)}</link>
      <g:image_link>{escape(product.image_url or '')}</g:image_link>
      <g:price>{product.original_price_krw or product.price_krw or 0} KRW</g:price>
      <g:sale_price>{product.price_krw or 0} KRW</g:sale_price>
      <g:availability>{"in stock" if product.is_active else "out of stock"}</g:availability>
      <g:brand>{escape(brand_name)}</g:brand>
      <g:condition>new</g:condition>
    </item>""".strip()
        )
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
  <channel>
    <title>Fashion Data Engine — Sale Products</title>
    <link>{escape(settings.public_site_url)}</link>
    <description>Sale product feed for Google Merchant Center</description>
    {''.join(items)}
  </channel>
</rss>"""
    return Response(content=feed, media_type="application/xml")
