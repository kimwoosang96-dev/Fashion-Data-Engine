# Gemini DB Sprint 1 — 실행 과업지시서

대상 에이전트: `gemini-db`  
연결 태스크: `T-20260227-001`  
우선순위: `P1`  
목표: DB 품질 안정화 + 크롤 완료율 향상 의사결정 자료 확보

## 배경
- 현재 edit-shop 크롤 커버리지가 낮고(0결과 채널 다수), 브랜드/판매채널 혼재 이슈가 존재.
- 운영상 필요한 것은 "자동화 가능한 정제"와 "수동 검토 대상의 명확한 분리"임.

## Sprint 목표 (이번 라운드)
1. `0결과 채널` 원인 분류표 작성
2. `브랜드-채널 혼재` 레코드 3분류(`safe-delete / manual-review / keep`)
3. API 체감 성능 개선을 위한 인덱스/쿼리 개선안 제시

## 실행 단계

### 1) 크롤 커버리지 감사
- 산출:
  - `edit-shop 총 개수`
  - `브랜드 1개 이상 추출 채널`
  - `0결과 채널 목록`
  - 채널별 브랜드 수 분포(0, 1~2, 3~20, 20+)
- 원인 분류 라벨:
  - `ssl_error`
  - `blocked_or_bot`
  - `selector_mismatch`
  - `empty_or_low_inventory`
  - `unknown`
- 결과 형식:
  - CSV 1개: `agents/archive/gemini_db/channel_zero_result_diagnosis_YYYYMMDD.csv`

### 2) 혼재 데이터 정제 정책
- 기준:
  - 브랜드명/slug 정규화 값이 채널명/채널 도메인 정규화 값과 충돌하면 후보군
- 후보군 분류:
  - `safe-delete`: `products.brand_id` 참조 0건 + `channel_brands` 링크 <= 1
  - `manual-review`: 참조 존재 또는 다중 링크
  - `keep`: 실제 브랜드로 취급하는 근거가 명확
- 결과 형식:
  - Markdown 리포트: `agents/archive/gemini_db/mixed_brand_channel_classification_YYYYMMDD.md`
  - SQL 실행안(선택): safe-delete 대상 정리 SQL 초안

### 3) 인덱스/쿼리 개선안
- 우선 API:
  - `/products/search`
  - `/products/sales-highlights`
  - `/channels/highlights`
  - `/brands/highlights`
- 요구 산출:
  - 병목 후보 쿼리 + 이유
  - 제안 인덱스 목록(테이블/컬럼/복합인덱스 순서)
  - 예상 효과(정성 기준 가능)
- 결과 형식:
  - 리포트: `agents/archive/gemini_db/query_index_recommendations_YYYYMMDD.md`

## 완료 기준 (DoD)
- 0결과 채널 100%에 라벨 부여
- 혼재 후보 100%를 3분류로 분리
- 인덱스 제안 최소 5개 이상 + 적용 우선순위 제시
- `WORK_LOG.md`에 최소 3회 로그 남김
  - 착수
  - 중간 결과
  - 최종 완료

## 로그 규칙
- 착수:
  - `python scripts/agent_coord.py log --agent gemini-db --task-id T-20260227-001 --message "Sprint1 착수: 커버리지 감사 시작"`
- 중간:
  - `python scripts/agent_coord.py log --agent gemini-db --task-id T-20260227-001 --message "중간: 0결과 원인 분류 60% 완료"`
- 완료:
  - `python scripts/agent_coord.py complete-task --id T-20260227-001 --agent gemini-db --summary "DB 감사/분류/인덱스 제안 완료"`

