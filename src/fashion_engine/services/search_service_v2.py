from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_engine.config import settings
from fashion_engine.services import product_service

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is not None:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return None
    _model = SentenceTransformer(settings.semantic_embedding_model)
    return _model


async def _encode_query(query: str) -> list[float] | None:
    model = _get_model()
    if model is None:
        return None
    embedding = await asyncio.to_thread(model.encode, query, normalize_embeddings=True)
    return embedding.tolist()


async def keyword_search(db: AsyncSession, q: str, limit: int = 20) -> list[dict[str, Any]]:
    rows = await product_service.search_products(db, q=q, limit=limit)
    return [
        {
            "id": row.id,
            "product_key": row.product_key,
            "normalized_key": row.normalized_key,
            "product_name": row.name,
            "brand_name": row.brand.name if row.brand else None,
            "channel_name": row.channel.name if row.channel else None,
            "url": row.url,
            "image_url": row.image_url,
            "price_krw": int(row.price_krw) if row.price_krw is not None else None,
            "similarity": None,
        }
        for row in rows
    ]


async def semantic_search(db: AsyncSession, q: str, limit: int = 20) -> list[dict[str, Any]]:
    embedding = await _encode_query(q)
    if embedding is None:
        logger.info("sentence-transformers unavailable; semantic search falls back to keyword")
        return await keyword_search(db, q=q, limit=limit)

    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return await keyword_search(db, q=q, limit=limit)

    rows = (
        await db.execute(
            text(
                """
                SELECT
                    p.id,
                    p.product_key,
                    p.normalized_key,
                    p.name AS product_name,
                    b.name AS brand_name,
                    c.name AS channel_name,
                    p.url,
                    p.image_url,
                    p.price_krw,
                    1 - (p.name_embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM products p
                LEFT JOIN brands b ON b.id = p.brand_id
                LEFT JOIN channels c ON c.id = p.channel_id
                WHERE p.is_active = true
                  AND p.name_embedding IS NOT NULL
                ORDER BY p.name_embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
                """
            ),
            {"embedding": json.dumps(embedding), "limit": limit},
        )
    ).mappings().all()

    if not rows:
        return await keyword_search(db, q=q, limit=limit)

    return [
        {
            "id": int(row["id"]),
            "product_key": row["product_key"],
            "normalized_key": row["normalized_key"],
            "product_name": row["product_name"],
            "brand_name": row["brand_name"],
            "channel_name": row["channel_name"],
            "url": row["url"],
            "image_url": row["image_url"],
            "price_krw": int(row["price_krw"]) if row["price_krw"] is not None else None,
            "similarity": round(float(row["similarity"]), 4) if row["similarity"] is not None else None,
        }
        for row in rows
    ]
