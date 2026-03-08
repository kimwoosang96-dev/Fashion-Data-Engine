from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select, text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.config import settings  # noqa: E402
from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.product import Product  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate semantic embeddings for products.")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def _load_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.semantic_embedding_model)


async def run(*, limit: int, apply: bool) -> int:
    await init_db()
    model = await asyncio.to_thread(_load_model)

    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(Product.id, Product.name, Product.description)
                .where(Product.is_active == True)  # noqa: E712
                .order_by(Product.id.asc())
                .limit(limit)
            )
        ).all()
        texts = [
            " ".join(part for part in [row.name, row.description] if part).strip()
            for row in rows
        ]
        embeddings = await asyncio.to_thread(model.encode, texts, normalize_embeddings=True)
        bind = db.get_bind()

        if apply:
            for row, embedding in zip(rows, embeddings, strict=False):
                payload = json.dumps(embedding.tolist())
                if bind.dialect.name == "postgresql":
                    await db.execute(
                        text(
                            "UPDATE products "
                            "SET name_embedding = CAST(:embedding AS vector) "
                            "WHERE id = :product_id"
                        ),
                        {"embedding": payload, "product_id": row.id},
                    )
                else:
                    await db.execute(
                        text(
                            "UPDATE products SET name_embedding = :embedding WHERE id = :product_id"
                        ),
                        {"embedding": payload, "product_id": row.id},
                    )
            await db.commit()

    print(f"generate_embeddings processed={len(rows)} apply={apply}")
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(asyncio.run(run(limit=args.limit, apply=bool(args.apply))))
