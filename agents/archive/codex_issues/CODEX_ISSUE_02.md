# [Codex] Issue #02 — 브랜드 티어 분류 + CSV 임포트

> **Context**: `AGENTS.md` 참조. 현재 브랜치 `main`.
> 이 이슈의 목표: DB의 브랜드에 `tier` 값을 부여하는 분류 파이프라인 구축.

---

## 배경

`brands` 테이블에 `tier` 컬럼이 추가되었음 (Alembic 마이그레이션 적용 완료).
티어 허용값: `high-end` | `premium` | `street` | `sports` | `spa`

### 분류 기준
| 티어 | 기준 | 예시 |
|------|------|------|
| high-end | 풀컬렉션 런웨이 3년 이상 | UNDERCOVER, Maison Margiela, Yohji Yamamoto, Rick Owens |
| premium | 디자이너 브랜드, 럭셔리 스트릿 | OAMC, KAPITAL, Story mfg., WTAPS, Engineered Garments |
| street | 스트릿웨어 | Palace, thisisneverthat, BlackEyePatch, NEIGHBORHOOD |
| sports | 스포츠 + 아웃도어 (기능성) | Goldwin, Arc'teryx, Salomon, CAYL, Snow Peak |
| spa | 패스트패션 / 매스마켓 | (현재 DB에 거의 없음) |

---

## 해야 할 작업

### Task 1: 티어 분류 CSV 준비

**파일**: `data/brand_tiers.csv`

```csv
slug,tier
undercover,high-end
maison-margiela,high-end
rick-owens,high-end
...
palace,street
thisisneverthat,street
...
```

- 크롤러로 수집된 브랜드 slug 목록 조회:
  ```bash
  uv run python -m fashion_engine.cli brands | head -50
  ```
- 상위 100개 브랜드를 우선 분류하여 CSV 작성

### Task 2: 임포트 스크립트 작성

**파일**: `scripts/classify_brands.py`

```python
# CSV 읽어서 Brand.tier 일괄 업데이트
# uv run python scripts/classify_brands.py data/brand_tiers.csv
```

로직:
1. CSV 파싱 (`slug`, `tier`)
2. `SELECT * FROM brands WHERE slug = ?` → 존재하면 tier UPDATE
3. 결과 요약 출력 (업데이트 수, 없는 슬러그 목록)

### Task 3: 분류 결과 검증

```bash
# 티어별 브랜드 수 확인
uv run uvicorn fashion_engine.api.main:app --reload &
curl http://localhost:8000/brands/?tier=high-end | python -m json.tool
curl http://localhost:8000/brands/landscape | python -m json.tool | head -30
```

---

## 주의사항

- `description_ko`는 수동 큐레이션 → 이 이슈에서는 **다루지 않음**
- slug 없는 브랜드는 건너뛰고 경고 로그만 출력
- `uv run alembic upgrade head` 먼저 실행 (마이그레이션 적용 확인)
