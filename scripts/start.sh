#!/bin/bash
# 퍼스널 쇼퍼 — 로컬 실행 스크립트

set -e
cd "$(dirname "$0")/.."

echo "🚀 백엔드 시작..."
uv run uvicorn fashion_engine.api.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "🌐 프론트엔드 시작..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo "✓ 실행 중"
echo "  백엔드: http://localhost:8000"
echo "  프론트: http://localhost:3000"
echo ""
echo "종료: Ctrl+C"

sleep 2
open http://localhost:3000

wait $BACKEND_PID $FRONTEND_PID
