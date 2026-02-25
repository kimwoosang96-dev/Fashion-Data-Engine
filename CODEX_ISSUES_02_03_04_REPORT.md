# CODEX 이슈 02/03/04 완료 보고서

작성일: 2026-02-25

## 1) Issue #02 — 브랜드 티어 분류 + CSV 임포트

### 구현 사항
- `data/brand_tiers.csv` 생성 (120개 slug 분류)
- `scripts/classify_brands.py` 추가
  - CSV(`slug,tier`) 파싱
  - 유효 티어 검증: `high-end | premium | street | sports | spa`
  - 존재 브랜드만 `Brand.tier` 업데이트
  - 결과 요약 출력(업데이트/유효성 오류/미존재 slug)

### 실행 결과
- 1차 실행: 업데이트 120, 미존재 slug 0
- 재실행(멱등성): 업데이트 0
- API 검증:
  - `GET /brands/?tier=high-end` → 200, 3개
  - `GET /brands/landscape` → 200, `by_tier` 반영 확인

---

## 2) Issue #03 — 협업 추적 + 하입 분석

### 구현 사항
- `data/brand_collabs.csv` 생성 (34개 협업 시드)
- `scripts/seed_collabs.py` 추가
  - slug → brand_id 조회
  - `brand_a_id < brand_b_id` 정규화 저장
  - 중복 체크(pair + collab_name)
  - `hype_score = 공통 채널 수 × 10`, 최대 100
- `scripts/recalculate_hype.py` 추가
  - 전체 협업 row hype_score 재계산

### 실행 결과
- 1차 시드 실행: 생성 34, 스킵 0
- 재실행(중복 방지): 생성 0, 중복 스킵 34
- 재계산 실행: 업데이트 0, 변경 없음 34
- API 검증:
  - `GET /collabs/` → 200, 34개
  - `GET /collabs/hype-by-category` → 200, 카테고리 집계 반환

---

## 3) Issue #04 — 시각화 검증 + 크롤 완료 보조 작업

### 구현 사항
- `GET /channels/landscape` 구현
  - 파일: `src/fashion_engine/api/channels.py`
  - 응답: 채널별 `brand_count`, `top_tiers`, 통계(`by_country`, `by_type`)
- 스키마 추가
  - 파일: `src/fashion_engine/api/schemas.py`
  - `ChannelLandscapeItem`, `ChannelLandscape`
- 0결과 우선 채널 전략 추가
  - 파일: `src/fashion_engine/crawler/brand_crawler.py`
  - 대상: `kasina.co.kr`, `thexshop.co.kr`, `unipair.com`, `parlour.kr`
  - 전략 필터 추가: `href_must_contain`, `href_must_not_contain`
  - Cafe24 감지 로직 개선(`/brand` 실패 시 즉시 종료하지 않고 다음 경로 시도)
- 데이터 품질 리포트 스크립트 추가
  - 파일: `scripts/data_quality_report.py`
  - 출력: 채널별 브랜드 수, 0결과 채널, 중복 의심 브랜드 그룹

### 실행 결과
- `GET /channels/landscape` → 200, 154 채널 반환
- `GET /brands/landscape` → 200, `total_brands=957`
- `scripts/data_quality_report.py`:
  - 활성 edit-shop: 75
  - edit-shop 0결과: 69
- 우선 채널 4개 Playwright 테스트:
  - Kasina: 0
  - THEXSHOP: 0
  - Unipair: 5(노이즈 포함)
  - PARLOUR: 0

### 완료 기준 충족 여부
- `[ ]` edit-shop 75개 중 60개 이상 추출 성공 (현 상태 미충족)
- `[x]` `/brands/landscape` 브랜드 수 200개 이상
- `[x]` `/channels/landscape` 정상 응답
- `[x]` `/collabs/hype-by-category` 데이터 반환

---

## 변경 파일 목록
- `data/brand_tiers.csv`
- `data/brand_collabs.csv`
- `scripts/classify_brands.py`
- `scripts/seed_collabs.py`
- `scripts/recalculate_hype.py`
- `scripts/data_quality_report.py`
- `src/fashion_engine/api/channels.py`
- `src/fashion_engine/api/schemas.py`
- `src/fashion_engine/crawler/brand_crawler.py`
