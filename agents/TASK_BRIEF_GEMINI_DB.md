# Task Brief — Gemini DB

## Role
- Agent: `gemini-db`
- Mission: DB 품질/정합성/성능 관점에서 프로젝트 신뢰도 향상

## Current Priority (P1)
1. 크롤 데이터 품질 감사
   - edit-shop 0결과 채널 원인 분류(SSL, anti-bot, selector mismatch, empty inventory)
   - 채널별 위험도 레이블 작성(high/medium/low)
2. 브랜드-채널 혼재 정제 정책 수립
   - 자동 삭제 가능/수동 검토 필요 기준 제안
   - 잘못된 brand 레코드가 products/channel_brands에 미치는 영향 분석
3. 쿼리/인덱스 점검
   - 자주 쓰는 API 기준으로 인덱스 개선안 제시
   - `/products/search`, `/products/sales-highlights`, `/channels/highlights`, `/brands/highlights` 우선

## Deliverables
- `agents/archive/` 또는 `agents/` 하위에 DB 감사 리포트 1개
- `TASK_DIRECTIVE.md`의 본인 담당 태스크 상태 업데이트
- `WORK_LOG.md`에 최소 3회 로그
  - 착수
  - 중간 결과
  - 완료(핵심 결론)

## Command Policy
- 로그:
  - `python scripts/agent_coord.py log --agent gemini-db --task-id <id> --message "..."`
- 완료:
  - `python scripts/agent_coord.py complete-task --id <id> --agent gemini-db --summary "..."`

## Completion Criteria
- 원인 분류 가능한 0결과 채널 비율 90% 이상
- 혼재 후보를 `safe-delete / manual-review / keep` 3분류로 명확히 분리
- 인덱스/쿼리 개선안이 실행 순서 포함하여 제시됨
