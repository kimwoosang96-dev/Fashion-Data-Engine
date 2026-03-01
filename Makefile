.PHONY: setup api web dev crawl crawl-cafe24 crawl-news news update-rates scheduler-dry scheduler data-audit audit audit-railway reclassify brand-mece fix-brands fix-null-brands fix-null-brands-dry fix-null-brands-apply remap-product-brands remap-product-brands-apply seed-directors seed-directors-apply seed-brands-luxury seed-brands-luxury-apply enrich-brands enrich-brands-apply purge-fake-brands purge-fake-brands-apply backfill-normalized-key backfill-normalized-key-apply backfill-normalized-key-force detect-platforms detect-platforms-apply

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

crawl:
	uv run python scripts/crawl_products.py --no-alerts

crawl-cafe24:
	uv run python scripts/crawl_products.py --channel-type edit-shop --no-alerts

crawl-news:
	uv run python scripts/crawl_news.py

update-rates:
	uv run python scripts/update_exchange_rates.py

scheduler-dry:
	uv run python scripts/scheduler.py --dry-run

scheduler:
	uv run python scripts/scheduler.py

data-audit:
	uv run python scripts/data_audit.py

audit:
	uv run python scripts/data_audit.py

audit-railway:
	DATABASE_URL=$(RAILWAY_DATABASE_URL) uv run python scripts/data_audit.py

reclassify:
	uv run python scripts/reclassify_products.py --dry-run

brand-mece:
	uv run python scripts/fix_brand_mece.py

fix-brands:
	uv run python scripts/cleanup_mixed_brand_channel.py

fix-null-brands:
	uv run python scripts/fix_null_brand_id.py

fix-null-brands-dry:
	uv run python scripts/fix_null_brand_id.py --dry-run

fix-null-brands-apply:
	uv run python scripts/fix_null_brand_id.py --apply

remap-product-brands:
	uv run python scripts/remap_product_brands.py --dry-run

remap-product-brands-apply:
	uv run python scripts/remap_product_brands.py --apply

seed-directors:
	uv run python scripts/seed_directors.py --csv data/brand_directors.csv --dry-run

seed-directors-apply:
	uv run python scripts/seed_directors.py --csv data/brand_directors.csv --apply

seed-brands-luxury:
	uv run python scripts/seed_brands_luxury.py --dry-run

seed-brands-luxury-apply:
	uv run python scripts/seed_brands_luxury.py --apply

enrich-brands:
	uv run python scripts/enrich_brands.py --csv data/brand_enrichment.csv --dry-run

enrich-brands-apply:
	uv run python scripts/enrich_brands.py --csv data/brand_enrichment.csv --apply

purge-fake-brands:
	uv run python scripts/purge_fake_brands.py --dry-run

purge-fake-brands-apply:
	uv run python scripts/purge_fake_brands.py --apply

backfill-normalized-key:
	uv run python scripts/backfill_normalized_key.py

backfill-normalized-key-apply:
	uv run python scripts/backfill_normalized_key.py --apply

backfill-normalized-key-force:
	uv run python scripts/backfill_normalized_key.py --apply --force

detect-platforms:
	uv run python scripts/detect_platforms.py

detect-platforms-apply:
	uv run python scripts/detect_platforms.py --apply
