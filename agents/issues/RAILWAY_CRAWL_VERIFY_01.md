# T-070 | RAILWAY_CRAWL_VERIFY_01

> **목적**: Railway 환경에서 전체 크롤 실행해 KR DNS 채널 수집 검증 및 최초 완전 크롤 달성

---

## 배경

### 왜 Railway인가

로컬 macOS에서 해결 불가한 3가지 이슈:

| 이슈 | 영향 채널 | 원인 |
|------|---------|------|
| Korean .co.kr DNS 미해석 | CAYL, and wander, NOCLAIM, 블루스맨, BIZZARE, Casestudy, ECRU, Rino 등 KR Cafe24 편집숍 포함 최소 10개 | 로컬 DNS 서버가 .co.kr 국내 전용 도메인 해석 불가 |
| Shopify IP rate-limit | T-068 수정 후에도 반복 위험 | 동일 IP에서 반복 hit |
| 일본 SaaS 실수집 검증 | stores-jp(3), makeshop(1), ochanoko(4) | 현재 구현 완료, 실환경 미검증 |

**Railway 환경 장점**:
- KR DNS 정상 해석 (AWS ap-northeast-1 기반 DNS)
- 로컬과 다른 IP → Shopify rate-limit 분리
- 현재 운영 DB (PostgreSQL) 직접 연동

### 현재 미검증 채널 목록

**KR Cafe24 (DNS 이슈, 로컬 실패)**:
```
CAYL           https://www.cayl.co.kr
and wander     https://www.andwander.co.kr
브레슈          https://www.breche-online.com
NOCLAIM        https://www.noclaim.co.kr
블루스맨        https://www.bluesman.co.kr
BIZZARE        https://www.bizzare.co.kr
Casestudy      https://www.casestudystore.co.kr
ECRU Online    https://www.ecru.co.kr
Rino Store     https://www.rinostore.co.kr
+ 기타 .co.kr edit-shop 채널들
```

**일본 SaaS (구현 완료, 미검증)**:
```
elephant TRIBAL fabrics  → stores-jp (buyshop.jp)
UNDERCOVER Kanazawa      → stores-jp (theshop.jp)
SOMEIT                   → stores-jp (403 이슈)
Laid back               → makeshop (shop-pro.jp)
TITY                    → ochanoko (ocnk.net)
```

---

## 요구사항

### Step 1: T-068, T-069 적용 확인 후 Railway 배포

전제 조건:
- [ ] T-068 (channel_probe.py 수정) 머지됨
- [ ] T-069 (Cafe24 단일 브랜드 전략) 머지됨

### Step 2: Railway에서 전체 크롤 실행

Railway 대시보드 또는 CLI로 실행:

```bash
# Railway CLI (로컬에서 실행)
railway run python scripts/crawl_products.py --no-alerts --concurrency 2

# 또는 Railway 환경 변수 설정 후 로컬 실행
DATABASE_URL=$RAILWAY_DATABASE_URL \
uv run python scripts/crawl_products.py --no-alerts --concurrency 2 \
  > logs/crawl_railway_$(date +%Y%m%d_%H%M).log 2>&1
```

**크롤 순서 최적화** (Railway 실행 시):
1. `--channel-type brand-store` 우선 실행 (결과 빠른 확인)
2. `--channel-type edit-shop` (Cafe24 편집숍 포함)
3. 전체 실행

### Step 3: 결과 분석

```bash
# 플랫폼별 수집 결과
sqlite3 data/fashion.db "  # 또는 Railway PostgreSQL
SELECT c.platform, c.channel_type, COUNT(DISTINCT c.id) as channels,
       SUM(cl.products_found) as total_found,
       SUM(CASE WHEN cl.status='success' THEN 1 ELSE 0 END) as success
FROM crawl_channel_logs cl
JOIN channels c ON c.id = cl.channel_id
WHERE cl.run_id = (SELECT MAX(id) FROM crawl_runs)
GROUP BY c.platform, c.channel_type
ORDER BY c.platform, c.channel_type;
"

# 여전히 실패하는 KR Cafe24 채널
SELECT c.name, c.url, cl.status, cl.error_msg
FROM crawl_channel_logs cl
JOIN channels c ON c.id = cl.channel_id
WHERE cl.run_id = (SELECT MAX(id) FROM crawl_runs)
AND c.platform='cafe24' AND cl.status != 'success';
```

### Step 4: 잔류 실패 채널 분류 + 후속 과업 등록

| 실패 유형 | 대응 |
|---------|------|
| 여전히 KR DNS 실패 | Railway DNS 설정 확인 후 비활성화 검토 |
| 일본 SaaS 수집 실패 | 크롤러 로직 버그 조사 (새 과업) |
| Cafe24 edit-shop 지속 실패 | THEXSHOP 단독 크롤 비교 후 판단 |
| Shopify 채널 일부 0개 | 비공개 스토어 여부 확인 → 비활성화 |

---

## 성공 기준

- [ ] KR Cafe24 DNS 채널 최소 5개 수집 성공 (0→ 제품 있음)
- [ ] 일본 SaaS 최소 2개 플랫폼 수집 성공
- [ ] 전체 크롤 완료 (CrawlRun 1개 `status='done'`)
- [ ] 이전 대비 신규 제품 ≥ 5,000개 추가
- [ ] 실패 채널 원인별 분류 보고서 출력

---

## 실행 명령 (참고)

```bash
# Railway 환경 확인
railway status

# Worker 서비스에서 실행
railway run --service worker python scripts/crawl_products.py --no-alerts

# 결과 모니터링 (로컬)
railway logs --service worker --tail
```
