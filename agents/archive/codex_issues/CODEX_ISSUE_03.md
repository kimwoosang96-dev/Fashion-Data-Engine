# [Codex] Issue #03 — 협업 추적 + 하입 분석

> **Context**: `AGENTS.md` 참조. 현재 브랜치 `main`.
> 이 이슈의 목표: `brand_collaborations` 테이블에 초기 데이터 입력 + hype_score 자동 계산.

---

## 배경

`brand_collaborations` 테이블이 추가되었음 (Alembic 마이그레이션 적용 완료).

### hype_score 계산 공식
```
hype_score = 두 브랜드를 모두 취급하는 채널 수 × 10
상한: 100점
```

예: brand_a=Palace, brand_b=Arc'teryx를 모두 취급하는 채널이 3개이면
→ `hype_score = 30`

---

## 해야 할 작업

### Task 1: 협업 시드 CSV 작성

**파일**: `data/brand_collabs.csv`

```csv
brand_a_slug,brand_b_slug,collab_name,collab_category,release_year,source_url,notes
palace,adidas,Palace x Adidas SS24,footwear,2024,https://...,
wales-bonner,adidas,Wales Bonner x Adidas,footwear,2023,,
...
```

- 최근 3년(2022-2024) 주요 협업 30개 이상 수집
- 카테고리: `footwear` | `apparel` | `accessories` | `lifestyle`

### Task 2: 시드 임포트 스크립트

**파일**: `scripts/seed_collabs.py`

```python
# uv run python scripts/seed_collabs.py data/brand_collabs.csv
```

로직:
1. CSV 파싱
2. slug → brand_id 조회 (없으면 건너뜀 + 경고)
3. `BrandCollaboration` 생성 (중복 시 skip)
4. `hype_score` 계산:
   ```sql
   SELECT COUNT(*) FROM channel_brands
   WHERE brand_id IN (brand_a_id, brand_b_id)
   GROUP BY channel_id
   HAVING COUNT(DISTINCT brand_id) = 2
   ```
   → 결과 행 수 × 10 (상한 100)
5. 결과 출력

### Task 3: hype_score 재계산 커맨드

**파일**: `scripts/recalculate_hype.py`

```bash
# 크롤 데이터 업데이트 후 전체 재계산
uv run python scripts/recalculate_hype.py
```

### Task 4: API 검증

```bash
curl http://localhost:8000/collabs/ | python -m json.tool
curl http://localhost:8000/collabs/hype-by-category | python -m json.tool
```

---

## 주의사항

- `brand_a_id < brand_b_id` 순서로 저장하여 중복 방지
- slug 조회 실패 시 해당 행 건너뜀 (오류로 중단하지 말 것)
- 브랜드 크롤이 완료되어야 hype_score가 의미 있음 (Issue #01 선행)
