.PHONY: setup api web dev news

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
