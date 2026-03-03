# Intel Hub Phase 2 — 실시간 피드 고도화 계획

> 작성일: 2026-03-03
> 현황: Intel Hub Phase 1 완료 (T-072~T-076). 이벤트 38건(mirror 34 + spike 4)이 전부.
> 핵심 문제: **새 이벤트가 하루 1회 07:30 배치 외에 들어오지 않음 → 실시간성 0**

---

## 현재 구조 (As-Is)

```
[외부 소스]           [수집]              [intel_events]      [프론트]
RSS 4개 피드  ──→  crawl_news.py      ─┐
drops (DB 시드)          (07:00)       ├→ ingest_intel   →  /intel
collabs (DB 시드) ──→ ingest_intel.py ─┘  (07:30, 1회/일)
crawl_products ──→ upsert_derived (크롤 시에만, 현재 비활성)
```

**병목점**
1. `crawl_news.py` RSS 4개 → `fashion_news` 테이블 → `ingest_intel mirror` 순서
   - 하루 1회 → 뉴스가 24시간 묵어서 들어옴
2. drops/collabs 미러링 = DB 시드 데이터 복사에 불과 → 신규 드롭 정보 자동 감지 없음
3. `crawl_products.py` 완료 후 intel ingest 자동 트리거 없음 → sale_start/sold_out/restock이 크롤 전까지 미반영
4. RSS 소스: 영문 4개(Hypebeast·Highsnobiety·SneakerNews·Complex) → 한국 패션 매체 없음

---

## 목표 (To-Be)

```
[외부 소스]                  [수집 주기]       [intel_events]
RSS: 영문 4 + 한국 4 ──→  4회/일(6h)   ──→
브랜드 드롭 Shopify tag ──→ 크롤 완료 후  ──→  실시간 피드
sale_start/sold_out ───→ 크롤 완료 후  ──→
sales_spike ────────────→  6회/일(4h)   ──→
```

---

## Phase 2 과업 목록

---

### T-077 | 뉴스 수집 주기 4회/일 + 한국 매체 RSS 추가

**배경**: 현재 07:00 하루 1회. 패션 뉴스는 낮 시간대에도 계속 올라옴.

**구현**

**`scripts/crawl_news.py`** — RSS_FEEDS에 한국 패션 매체 추가:
```python
RSS_FEEDS = [
    # 영문 (기존)
    "https://hypebeast.com/feed",
    "https://www.highsnobiety.com/feed/",
    "https://sneakernews.com/feed/",
    "https://www.complex.com/style/rss",
    # 한국 추가
    "https://hypebeast.kr/feed",
    "https://www.vogue.co.kr/feed/",
    "https://www.wkorea.com/rss/",
    "https://magazine.boon.so/rss",   # Boon (스트리트 패션)
]
```

**`scripts/scheduler.py`** — 뉴스 크롤 + ingest를 6시간 주기로:
```python
# 기존 07:00 단건 → 00:00 / 06:00 / 12:00 / 18:00 4회
scheduler.add_job(run_news_job, CronTrigger(hour="0,6,12,18", minute=0), id="news_0_6_12_18")
scheduler.add_job(run_intel_mirror_job, CronTrigger(hour="0,6,12,18", minute=10), id="intel_mirror_0_6_12_18")
```

`run_intel_mirror_job`은 `mirror` 잡만 실행 (derived_spike는 별도).

**DoD**
- [ ] RSS_FEEDS에 한국 매체 4개 추가
- [ ] 스케줄러 뉴스 크롤 4회/일 변경
- [ ] 스케줄러 intel mirror 4회/일 변경 (크롤 완료 10분 후)
- [ ] 로컬 테스트: `uv run python scripts/crawl_news.py` → 한국 매체 기사 수집 확인

---

### T-078 | 크롤 완료 후 intel ingest 자동 트리거

**배경**: `crawl_products.py` 실행 시 sale_start/sold_out/restock 파생 이벤트가 `upsert_derived_product_event()`로 생성되지만, `derived_spike` 잡은 별도 스케줄로만 돈다.

**구현**

**`scripts/crawl_products.py`** — 크롤 완료 직후 derived_spike 자동 실행:
```python
# crawl_products.py 맨 마지막 (main() 완료 후)
if total_products > 0 and not args.no_intel:
    logger.info("[INTEL] 크롤 완료 → derived_spike 자동 실행")
    import ingest_intel_events
    await ingest_intel_events.run(job="derived_spike", window_hours=48)
```

`--no-intel` 플래그로 비활성화 가능하게.

**`scripts/scheduler.py`** — derived_spike 독립 주기 강화:
```python
# 기존: intel_ingest_0730 1회 (mirror + spike 같이)
# 변경: mirror는 4회/일, spike는 4회/일 별도
scheduler.add_job(run_intel_spike_job, CronTrigger(hour="3,9,15,21", minute=0), id="intel_spike_4x")
```

**DoD**
- [ ] `crawl_products.py`에 `--no-intel` 플래그 추가
- [ ] 크롤 완료 후 `ingest_intel_events.run(job="derived_spike")` 자동 호출
- [ ] 스케줄러 derived_spike 4회/일 별도 잡으로 분리
- [ ] 기존 `intel_ingest_0730` 잡 제거 (mirror + spike 통합 잡 → 분리)

---

### T-079 | 브랜드 드롭 자동 감지 → intel drops 이벤트

**배경**: 현재 drops는 `Drop` 모델(수동 시드)을 미러링. 새 드롭 공지가 Shopify 브랜드 스토어에 올라와도 자동 감지 없음.

**구현**

**`scripts/ingest_intel_events.py`** — Shopify `coming-soon` 태그 감지 함수 추가:
```python
async def _ingest_shopify_drops(db: AsyncSession, run: IntelIngestRun) -> None:
    """brand-store 채널에서 coming-soon 태그 상품 → drops 이벤트 생성."""
    brand_store_channels = (
        await db.execute(
            select(Channel).where(
                Channel.channel_type == "brand-store",
                Channel.is_active == True,
                Channel.platform == "shopify",
            )
        )
    ).scalars().all()

    for channel in brand_store_channels:
        # product_crawler의 coming-soon 태그 상품 조회
        products = (
            await db.execute(
                select(Product).where(
                    Product.channel_id == channel.id,
                    Product.tags.like("%coming-soon%"),
                    Product.is_active == True,
                    Product.updated_at >= utcnow() - timedelta(days=3),
                )
            )
        ).scalars().all()

        for product in products:
            await _upsert_event(
                db, run=run,
                source_table="products",
                source_pk=product.id,
                event_type="drop",
                layer="drops",
                title=f"{channel.name} 드롭 예고: {product.name[:60]}",
                summary=f"coming-soon 태그 감지 — {channel.name}",
                event_time=product.updated_at,
                brand_id=product.brand_id,
                channel_id=channel.id,
                source_url=product.url,
                source_type="crawler",
                severity="high",
                confidence="medium",
                details={"product_key": product.product_key, "tags": product.tags},
                published_at=product.updated_at,
            )
```

`run()` 함수에 `shopify_drops` 잡 추가:
```python
if job in {"mirror", "drops_collabs_news", "shopify_drops"}:
    await _ingest_shopify_drops(db, run_row)
```

스케줄러에도 추가 (크롤 완료 20분 후):
```python
scheduler.add_job(run_shopify_drops_job, CronTrigger(hour="3,9,15,21", minute=20), id="intel_shopify_drops")
```

**DoD**
- [ ] `_ingest_shopify_drops()` 구현
- [ ] `--job shopify_drops` 옵션 추가
- [ ] 스케줄러 등록
- [ ] 테스트: coming-soon 태그 보유 브랜드 스토어에서 이벤트 생성 확인

---

### T-080 | intel 이벤트 Discord 실시간 알림

**배경**: critical/high severity 이벤트가 생성돼도 사용자가 /intel 페이지를 직접 열어봐야만 알 수 있음.

**구현**

**`src/fashion_engine/services/intel_service.py`** — `notify_discord_if_warranted()` 추가:
```python
async def notify_discord_if_warranted(event: IntelEvent) -> None:
    """severity=critical/high 이벤트를 Discord webhook으로 즉시 발송."""
    if event.severity not in {"critical", "high"}:
        return
    if not settings.discord_webhook_url:
        return

    LAYER_EMOJI = {
        "drops": "🚀", "collabs": "🤝", "news": "📰",
        "sale_start": "🔥", "sold_out": "⚫", "restock": "🟢",
        "sales_spike": "📈",
    }
    emoji = LAYER_EMOJI.get(event.layer, "📌")
    color = 0xFF4444 if event.severity == "critical" else 0xFF8800

    payload = {
        "embeds": [{
            "color": color,
            "title": f"{emoji} {event.title[:200]}",
            "description": event.summary or "",
            "fields": [
                {"name": "Layer", "value": event.layer, "inline": True},
                {"name": "Severity", "value": event.severity, "inline": True},
                {"name": "Brand", "value": event.brand_name or "-", "inline": True},
            ],
            "url": f"https://fashion-data-engine.vercel.app/intel?event_id={event.id}",
            "timestamp": event.event_time.isoformat() if event.event_time else None,
        }]
    }
    async with httpx.AsyncClient(timeout=5) as client:
        await client.post(settings.discord_webhook_url, json=payload)
```

`upsert_derived_product_event()` 및 `_upsert_event()` 완료 후 호출.

환경변수 추가 (`.env.example`):
```
INTEL_DISCORD_WEBHOOK_URL=  # intel 전용 (기존 DISCORD_WEBHOOK_URL과 분리)
```

**DoD**
- [ ] `notify_discord_if_warranted()` 구현
- [ ] `upsert_derived_product_event()` 완료 후 자동 호출
- [ ] `_upsert_event()` 완료 후 자동 호출 (severity 필터 내부 처리)
- [ ] `.env.example`에 `INTEL_DISCORD_WEBHOOK_URL` 추가
- [ ] Railway Variables에 `INTEL_DISCORD_WEBHOOK_URL` 설정 필요 (수동)
- [ ] 테스트: sale_start 이벤트 수동 생성 → Discord 메시지 수신 확인

---

### T-081 | 이벤트 만료 + 중복 정리 자동화

**배경**: 30일 이상 된 low-severity 이벤트가 쌓이면 피드 품질 저하.

**구현**

**`scripts/ingest_intel_events.py`** — `expire_old_events()` 추가:
```python
async def _expire_old_events(db: AsyncSession) -> int:
    """30일 이상 된 low/medium 이벤트 is_active=False 처리."""
    cutoff = utcnow() - timedelta(days=30)
    result = await db.execute(
        update(IntelEvent)
        .where(
            IntelEvent.detected_at < cutoff,
            IntelEvent.severity.in_(["low", "medium"]),
            IntelEvent.is_active == True,
        )
        .values(is_active=False)
    )
    return result.rowcount
```

스케줄러: 매주 일요일 새벽 2시 실행.

**DoD**
- [ ] `_expire_old_events()` 구현
- [ ] 스케줄러 주간 만료 잡 등록
- [ ] `GET /admin/intel-status`에 `expired_total` 카운트 추가

---

## 우선순위 및 일정

| 과업 | 난이도 | 효과 | 담당 | 우선순위 |
|------|--------|------|------|----------|
| T-077 뉴스 4회/일 + 한국 매체 | 낮 | 즉각적 최신화 | Codex | **P1** |
| T-078 크롤 → intel 자동 트리거 | 낮 | 파생 이벤트 실시간화 | Codex | **P1** |
| T-079 Shopify 드롭 감지 | 중 | 드롭 자동 수집 | Codex | P2 |
| T-080 Discord 실시간 알림 | 낮 | UX 개선 | Codex | P2 |
| T-081 이벤트 만료 자동화 | 낮 | 품질 유지 | Codex | P3 |

**P1 즉시 실행** → T-077 + T-078은 스케줄러 수정 + 코드 추가만으로 가능, Railway 재배포 1회로 반영.

---

## 기대 효과

| 항목 | 현재 | Phase 2 후 |
|------|------|------------|
| 뉴스 갱신 주기 | 24시간 | 6시간 |
| 파생 이벤트 지연 | 최대 24시간 | 크롤 완료 즉시 |
| 커버 소스 | 영문 4 | 영문 4 + 한국 4 |
| 드롭 감지 | 수동 시딩만 | Shopify coming-soon 자동 감지 |
| 알림 | 없음 | Discord 즉시 알림 (critical/high) |
| 일 이벤트 생성량 | ~38건 (초기 1회) | ~50~200건/일 (추정) |
