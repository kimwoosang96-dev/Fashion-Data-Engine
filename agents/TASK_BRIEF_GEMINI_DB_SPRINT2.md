# Gemini DB Sprint 2 — DB 운영 준비 계획

대상 에이전트: `gemini-db`
태스크 ID: `T-20260227-002`
우선순위: `P1`
시작일: `2026-02-27`

## 목표

다음 3가지 문제를 해결하여 "DB 운영 준비 완료" 상태 달성:

1. 채널별 크롤 완료율 확보
2. 브랜드-채널 데이터 정합성 (혼재 엔티티 제거)
3. 대시보드/검색 API 쿼리 지연 안정화

## 범위

### A) 크롤 완료 감사 (채널 전수 분류)

모든 채널에 대해 단일 현황표 작성:

- `channel_id`, `channel_name`, `channel_type`, `country`
- `brand_count`, `product_count`, `last_crawled_at`
- `crawl_status`: `done / partial / failed / not_started`
- `failure_reason`: `ssl_error / timeout / blocked_or_bot / selector_mismatch / empty_inventory / unknown`

결과물:
- `agents/archive/gemini_db/crawl_completion_audit_2026-02-27.csv`

### B) 혼재 데이터 해소 (브랜드 vs 채널)

의심 브랜드 레코드를 3분류:

- `safe_delete`: `products.brand_id` 참조 없음 + `channel_brands` 영향 없음
- `manual_review`: 제품 참조 있거나 다중 채널 링크
- `keep`: 명칭 충돌에도 실제 브랜드임이 명확

결과물:
- `agents/archive/gemini_db/mixed_entity_decisions_2026-02-27.csv`
- `agents/archive/gemini_db/mixed_entity_cleanup_sql_2026-02-27.sql`

### C) 쿼리/인덱스 강화 (API 기준)

대상 엔드포인트:
- `/products/search`
- `/products/sales-highlights`
- `/channels/highlights`
- `/brands/highlights`

산출물:
- 쿼리 프로파일 요약 (개선 전 기준)
- 인덱스 계획 (DDL 즉시 실행 가능 형태)
- 예상 효과 메모 (상/중/하)

결과물:
- `agents/archive/gemini_db/query_index_hardening_2026-02-27.md`

## 예상 소요 시간

- A) 크롤 완료 감사: `2.0시간`
- B) 혼재 데이터 분류 + SQL 초안: `1.5시간`
- C) 쿼리/인덱스 강화 보고서: `1.5시간`
- 합계: `약 5.0시간` (단일 연속 실행 기준)
- 재크롤 필요 시 추가: `4~12시간` (차단 채널 비율 및 재시도 정책에 따라 상이)

## 완료 기준 (DoD)

1. 모든 채널에 크롤 상태 및 실패 원인 정확히 1개씩 부여
2. 혼재 후보 레코드 전체가 3분류로 분리됨
3. 최소 5개 이상의 인덱스 DDL 문장과 엔드포인트 매핑 제시
4. 모든 결과물이 `agents/archive/gemini_db/` 하위에 저장됨
5. 작업 로그 최소 3회 기록:
   - 착수
   - 중간
   - 완료

## 실행 명령

```bash
.venv/bin/python scripts/agent_coord.py log --agent gemini-db --task-id T-20260227-002 --message "Sprint2 착수: 크롤 완료 감사 시작"
.venv/bin/python scripts/agent_coord.py log --agent gemini-db --task-id T-20260227-002 --message "Sprint2 중간: 혼재 데이터 분류 진행 중"
.venv/bin/python scripts/agent_coord.py complete-task --id T-20260227-002 --agent gemini-db --summary "Sprint2 완료: 감사 + 혼재 정제 계획 + 인덱스 강화 보고서 제출"
```

## codex-dev 인수인계

- `safe_delete` SQL은 `codex-dev` 확인 후에만 실행
- 인덱스 DDL은 PM 승인 후 Alembic 마이그레이션 브랜치에 반영
