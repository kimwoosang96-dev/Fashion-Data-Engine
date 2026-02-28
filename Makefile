.PHONY: setup api web dev news reclassify brand-mece fix-brands fix-null-brands

setup:
	uv sync
	uv run playwright install chromium

api:
	uv run uvicorn fashion_engine.api.main:app --reload

web:
	cd frontend && npm run dev

dev:
	./scripts/dev_oneclick.sh

news:
	uv run python scripts/crawl_news.py

reclassify:
	.venv/bin/python scripts/reclassify_products.py --dry-run

brand-mece:
	.venv/bin/python scripts/fix_brand_mece.py

fix-brands:
	.venv/bin/python scripts/cleanup_mixed_brand_channel.py

fix-null-brands:
	.venv/bin/python scripts/fix_null_brand_id.py
