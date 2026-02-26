# [Codex] Issue #04 — 시각화 데이터 검증 + 전체 크롤 완료

> **Context**: `AGENTS.md` 참조. 현재 브랜치 `main`.
> 선행 조건: Issue #01 (전체 크롤), Issue #02 (티어 분류), Issue #03 (협업 데이터) 완료 후 진행.

---

## 해야 할 작업

### Task 1: 전체 크롤 결과 검증

Issue #01 크롤 완료 후 landscape API 응답 검증:

```bash
curl http://localhost:8000/brands/landscape | python -c "
import json, sys
data = json.load(sys.stdin)
print('총 브랜드:', data['stats']['total_brands'])
print('티어별:', data['stats']['by_tier'])
print('연결 엣지:', len(data['edges']))
# 채널 수 Top 10 브랜드
nodes = sorted(data['nodes'], key=lambda n: n['channel_count'], reverse=True)
for n in nodes[:10]:
    print(f\"  {n['name']} ({n['tier']}) — {n['channel_count']}개 채널\")
"
```

### Task 2: channels/landscape 엔드포인트 구현

**파일**: `src/fashion_engine/api/channels.py` (기존 파일에 추가)

```python
# GET /channels/landscape
# 응답: 국가별 채널 + 각 채널의 브랜드 수
{
    "channels": [
        {
            "id": 1,
            "name": "ARKnets",
            "country": "JP",
            "channel_type": "edit-shop",
            "brand_count": 45,
            "top_tiers": ["high-end", "premium"]
        }
    ],
    "stats": {
        "by_country": {"JP": 61, "KR": 36, ...},
        "by_type": {"edit-shop": 75, "brand-store": 75}
    }
}
```

### Task 3: 0 결과 채널 커스텀 전략 추가

Issue #01에서 파악된 0 결과 채널에 대해 `CHANNEL_STRATEGIES` 추가.

우선순위 채널:
1. Kasina (`kasina.co.kr`)
2. THEXSHOP (`thexshop.co.kr`)
3. Unipair (`unipair.com`)
4. PARLOUR (`parlour.kr`)

각 채널별:
```bash
uv run python scripts/crawl_brands.py --limit 1  # 1개씩 테스트
```

### Task 4: 데이터 품질 리포트 생성

```bash
uv run python -c "
from fashion_engine.database import ...
# 출력: 채널별 브랜드 수 / 0 결과 채널 / 중복 의심 브랜드
"
```

---

## 완료 기준

- [ ] 전체 edit-shop 75개 중 60개 이상 브랜드 추출 성공 (0 결과 15개 이하)
- [ ] `/brands/landscape` 반환 브랜드 수 200개 이상
- [ ] `/channels/landscape` 정상 응답
- [ ] `/collabs/hype-by-category` 카테고리별 데이터 반환
