#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "[1/5] Python 의존성 동기화 (uv sync)"
uv sync

echo "[2/5] Playwright Chromium 설치 확인"
uv run playwright install chromium

if [ ! -f ".env" ]; then
  echo "[3/5] .env 생성 (.env.example 복사)"
  cp .env.example .env
else
  echo "[3/5] .env 이미 존재"
fi

if command -v npm >/dev/null 2>&1; then
  echo "[4/5] 프론트 의존성 설치 (frontend)"
  (cd frontend && npm install)
else
  echo "[4/5] npm 미설치: 프론트 의존성 설치 단계 건너뜀"
fi

echo "[5/5] 개발 서버 실행"

if command -v npm >/dev/null 2>&1; then
  echo "백엔드: http://localhost:8000"
  echo "프론트: http://localhost:3000"

  uv run uvicorn fashion_engine.api.main:app --reload &
  API_PID=$!

  (cd frontend && npm run dev) &
  WEB_PID=$!

  cleanup() {
    kill "$API_PID" "$WEB_PID" 2>/dev/null || true
  }
  trap cleanup INT TERM EXIT

  wait -n "$API_PID" "$WEB_PID"
else
  echo "npm 미설치: 백엔드만 실행합니다."
  uv run uvicorn fashion_engine.api.main:app --reload
fi
