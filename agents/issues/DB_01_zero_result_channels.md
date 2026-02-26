# DB_01: 0결과 채널 원인 분류 + 재크롤 전략 실행

**Task ID**: T-20260227-001 (기존 gemini-db 태스크 → codex-dev 재배정)
**Owner**: codex-dev
**Priority**: P1
**Labels**: backend, crawler, data-quality

---

## 배경

현재 75개 편집샵(edit-shop) 중 약 32개가 브랜드 크롤 결과 0건임.
원인을 분류하고 개선 가능한 채널에 대해 크롤러 전략을 추가하거나 재크롤해야 함.

> 참고: `AGENTS.md` → Database Schema, scripts/crawl_brands.py

---

## 요구사항

### 1) 크롤 커버리지 감사 (Sprint 1)

- [ ] edit-shop 채널 전체 목록과 각 채널의 channel_brand 수 조회
- [ ] 0결과 채널을 다음 라벨로 분류:
  - `ssl_error` — SSL 인증서 오류
  - `blocked_or_bot` — bot 감지 또는 403
  - `selector_mismatch` — 크롤러 전략이 페이지 구조와 불일치
  - `empty_or_low_inventory` — 실제로 취급 브랜드가 적음
  - `unknown` — 원인 불명
- [ ] 결과 저장: `agents/archive/crawl_audit/channel_zero_result_YYYYMMDD.md`

### 2) 혼재 데이터 정제 (Sprint 1 + cleanup_mixed_brand_channel.py 활용)

- [ ] `scripts/cleanup_mixed_brand_channel.py` 실행 또는 검토
- [ ] `safe-delete` 대상 brand 레코드 삭제 (products.brand_id 참조 0건 + channel_brands <= 1)
- [ ] `manual-review` 대상 목록 정리

### 3) 인덱스 최적화 제안 (Sprint 2)

다음 API의 쿼리 병목 후보 분석 및 인덱스 제안:
- `/products/search`
- `/products/sales-highlights`
- `/channels/highlights`
- `/brands/highlights`

최소 5개 인덱스 제안 + 우선순위

---

## 기술 스펙

**관련 파일**:
- `scripts/crawl_brands.py` — 크롤러 전략 (CHANNEL_STRATEGIES dict)
- `scripts/cleanup_mixed_brand_channel.py` — 혼재 데이터 정제
- `src/fashion_engine/crawler/brand_crawler.py` — 실제 크롤러 로직
- `agents/TASK_BRIEF_GEMINI_DB_SPRINT1.md` — 세부 스프린트 지시서
- `agents/TASK_BRIEF_GEMINI_DB_SPRINT2.md` — 세부 스프린트 지시서

**DB 조회 예시**:
```python
# 0결과 채널 확인
SELECT c.name, c.url, COUNT(cb.brand_id) as brand_count
FROM channels c
LEFT JOIN channel_brands cb ON c.id = cb.channel_id
WHERE c.channel_type = 'edit-shop'
GROUP BY c.id
HAVING brand_count = 0;
```

---

## 완료 조건

- [ ] 0결과 채널 100%에 라벨 부여
- [ ] `safe-delete` 대상 혼재 레코드 정리 완료
- [ ] 인덱스 제안 최소 5개 + 우선순위 제시
- [ ] `agents/WORK_LOG.md`에 착수/중간/완료 3회 로그
- [ ] 결과 파일: `agents/archive/crawl_audit/channel_zero_result_YYYYMMDD.md`

---

## 참고

- `agents/TASK_BRIEF_GEMINI_DB_SPRINT1.md` — 상세 실행 지시서
- `agents/TASK_BRIEF_GEMINI_DB_SPRINT2.md` — 상세 실행 지시서
- `AGENTS.md` → Current Status (32개 0결과 채널 현황)
