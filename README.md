# Fashion Data Engine

패션 편집샵 · 판매채널 데이터 플랫폼

## 개요

- **154개** 편집샵 · 판매채널 데이터 수집 및 전처리
- 채널별 취급 **브랜드 자동 추출** (Playwright 크롤러)
- 브랜드 → 취급 채널 **역방향 조회** API
- 가격 추적 · 세일 감지 · 신상품 알림 (Phase 2)
- AI 가상 모델 룩북 아카이브 (Phase 3)

## 빠른 시작

```bash
# 1. 의존성 설치
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env
uv sync
uv run playwright install chromium

# 2. 환경 설정
cp .env.example .env

# 3. 채널 전처리 → DB 저장
uv run python scripts/preprocess_channels.py
uv run python scripts/seed_channels.py

# 4. 브랜드 크롤링
uv run python scripts/crawl_brands.py

# 5. API 실행
uv run uvicorn fashion_engine.api.main:app --reload
# http://localhost:8000/docs
```

## CLI

```bash
uv run python -m fashion_engine.cli channels       # 전체 채널
uv run python -m fashion_engine.cli brands         # 전체 브랜드
uv run python -m fashion_engine.cli brand nike     # Nike 취급 채널
uv run python -m fashion_engine.cli search 아크테릭스
```

## 개발 가이드

- AI 에이전트용: AGENTS.md
- Claude Code용: CLAUDE.md
