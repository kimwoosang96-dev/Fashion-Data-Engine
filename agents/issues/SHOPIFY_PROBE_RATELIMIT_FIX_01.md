# T-068 | SHOPIFY_PROBE_RATELIMIT_FIX_01

> **목적**: channel_probe.py가 크롤 직전 Shopify 채널을 재탐지하지 않도록 수정해 IP rate-limit 유발 방지

---

## 배경 (실측 사건)

**2026-03-02 사건**: Phase 25 크롤 준비 중 `channel_probe.py --all --apply` 실행 →
전체 151개 채널 동시 탐지(세마포어 10) → Shopify 83개 스토어를 짧은 시간에 동시 히트 →
Shopify CDN **IP 단위 429 블록** 발동 → 이후 `crawl_products.py` 실행 시 **전체 Shopify 채널 100% 실패**.

**핵심 증거**:
- CrawlRun #9 (37채널 처리): Patta, ALIVEFORM, BoTT, 032c, Cole Buxton 등 **기존 수집 성공 채널** 모두 `not_supported` 반환
- Run #9 이전 개별 테스트: Patta `products.json` → 200 OK (정상)
- Run #9 도중: 동일 URL → 429 연속 응답

**IP 블록 지속 시간**: ~15분 (ALIVEFORM/BoTT 15분 후 회복, Patta 30분 후 회복)

---

## 근본 원인 분석

```
channel_probe.py --all
  ├── 151개 채널 로드 (is_active=1 전체)
  ├── asyncio.Semaphore(10)으로 동시 처리
  ├── 이미 platform='shopify'인 81개 채널도 재탐지
  │   ├── _probe_shopify() → GET /shop.json (각 스토어)
  │   └── 동시 10개 × 수 초 = 81개 스토어 빠르게 순환
  └── Shopify CDN: 단일 IP에서 다수 스토어 동시 접근 → IP 429 블록
```

**channel_probe.py가 탐지를 스킵해야 할 조건**:
- `channel.platform IS NOT NULL` → 이미 식별됨 (재탐지 불필요)
- 단, `--force-retag` 플래그로 강제 재탐지 허용

---

## 요구사항

### Step 1: `scripts/channel_probe.py` — 이미 태깅된 채널 스킵

**파일**: `scripts/channel_probe.py`

```python
# 현재 (BUG): --all 시 모든 채널 탐지
if args.all:
    channels = await get_all_active_channels(db)
else:
    channels = await get_zero_product_channels(db)

# 수정: 이미 platform이 있는 채널은 기본적으로 스킵
if args.all:
    all_channels = await get_all_active_channels(db)
    if args.force_retag:
        channels = all_channels
    else:
        # platform=None 또는 'unknown'만 탐지
        channels = [c for c in all_channels if not c.platform or c.platform == 'unknown']
        skipped = len(all_channels) - len(channels)
        print(f"[probe] {skipped}개 채널 스킵 (platform 이미 설정됨). --force-retag으로 재탐지 가능")
else:
    channels = await get_zero_product_channels(db)
    # zero-product 채널도 platform이 있으면 기본 스킵
    if not args.force_retag:
        channels = [c for c in channels if not c.platform or c.platform == 'unknown']
```

**CLI 인자 추가**:
```python
parser.add_argument('--force-retag', action='store_true',
    help='이미 platform이 설정된 채널도 강제 재탐지 (rate-limit 위험)')
```

### Step 2: Shopify 탐지 속도 제한 강화

현재 세마포어 10 → Shopify 스토어는 2개로 별도 제한:

```python
# channel_probe.py 내 탐지 로직
SHOPIFY_PROBE_SEMAPHORE = asyncio.Semaphore(2)  # Shopify만 별도 제한
GENERAL_PROBE_SEMAPHORE = asyncio.Semaphore(10)

async def probe_with_throttle(channel):
    if channel.platform == 'shopify' or _looks_like_shopify(channel.url):
        async with SHOPIFY_PROBE_SEMAPHORE:
            return await probe_channel(channel)
    else:
        async with GENERAL_PROBE_SEMAPHORE:
            return await probe_channel(channel)
```

또는 단순화: 전체 세마포어를 5로 낮추고 Shopify 스토어간 stagger delay 추가.

### Step 3: 크롤 스크립트에 probe 동시 실행 방지 가이드라인 문서화

`scripts/crawl_products.py` 상단 docstring/주석:
```python
"""
주의: 크롤 실행 직전 channel_probe.py --all을 실행하지 마십시오.
      Shopify CDN IP rate-limit이 발동해 전체 크롤이 실패할 수 있습니다.
      probe는 크롤 30분 이상 전에 실행하거나 별도 스케줄로 분리하십시오.
"""
```

### Step 4: `deactivate_dead_channels.py` — 연속 실패 기준 개선

현재 `consecutive_failures` 기준이 IP rate-limit으로 인한 일시 실패를 포함함.
→ `error_type='not_supported'` 외 `error_type IN ('http_429', 'timeout')`은 연속 실패 카운트에서 제외:

```python
# deactivate_dead_channels.py 내 consecutive_failures 쿼리
WHERE error_type = 'not_supported'  -- 429/timeout은 일시적 실패로 카운트 제외
```

---

## DoD

- [ ] `channel_probe.py --all` → 기본적으로 `platform IS NULL or platform = 'unknown'` 채널만 탐지
- [ ] `--force-retag` 플래그 추가 (강제 재탐지, 경고 메시지 포함)
- [ ] Shopify 탐지 세마포어 ≤ 2 또는 전체 세마포어 5로 제한
- [ ] `crawl_products.py` 상단 주의 주석 추가
- [ ] `deactivate_dead_channels.py` consecutive_failures 기준: `error_type='not_supported'`만 카운트
- [ ] 검증: `channel_probe.py --all` 실행 후 즉시 `crawl_products.py` 실행 → Shopify 채널 정상 수집

---

## 검증

```bash
# 1. probe 실행 (이미 태깅된 Shopify 81개 스킵 확인)
uv run python scripts/channel_probe.py --all
# 예상: "81개 채널 스킵 (platform 이미 설정됨)"
# NULL platform 채널만 탐지 (32개 대상)

# 2. 즉시 크롤 실행 (Shopify rate-limit 없어야 함)
uv run python scripts/crawl_products.py --channel-type brand-store --concurrency 2

# 3. 성공 확인
sqlite3 data/fashion.db "
SELECT c.platform, COUNT(*) as n, SUM(cl.products_found) as found
FROM crawl_channel_logs cl JOIN channels c ON c.id = cl.channel_id
WHERE cl.run_id = (SELECT MAX(id) FROM crawl_runs)
GROUP BY c.platform;
"
# 예상: shopify 채널 products_found > 0
```
