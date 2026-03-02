# T-071 | NULL_PLATFORM_AUDIT_01

> **목적**: NULL platform 32개 채널의 플랫폼 분류 + 수집 가능 채널 식별 + 불가 채널 정리

---

## 배경

**현황**: 32개 활성 채널이 `platform IS NULL` 상태, 모두 제품 0개.

### 채널 목록 (국가별)

| 국가 | 채널 수 | 채널 목록 |
|------|---------|---------|
| JP (brand-store) | 7 | ACRMTSM, F/CE, Goldwin, LTTT, MaisonShunIshizawa, TIGHTBOOTH, TTTMSW |
| JP (edit-shop) | 8 | ARKnets, MusterWerk, Rogues, SHRED, TINY OSAKA, browniegift, wegenk, 앤드헵 |
| JP (dept/marketplace) | 2 | BAYCREW'S, Mercari |
| KR (brand-store) | 1 | thisisneverthat |
| KR (edit-shop) | 2 | COEVO, Kasina |
| HK (edit-shop) | 2 | HBX, VINAVAST |
| UK (brand-store) | 1 | The Trilogy Tapes |
| UK (edit-shop) | 2 | HIP, SEVENSTORE |
| US (brand-store) | 1 | Warren Lotas |
| SE (brand-store) | 2 | AXEL ARIGATO, Séfr |
| SE (edit-shop) | 1 | KA-YO |
| IT (brand-store) | 1 | Stone Island |
| ES (brand-store) | 1 | Camperlab |

---

## 채널별 플랫폼 추정 (사전 분석)

### Shopify 가능성 높음 (재확인 필요)

| 채널 | URL | 근거 |
|------|-----|------|
| thisisneverthat | thisisneverthat.com | 한국 브랜드, Shopify 스토어 사용 확인된 사례 많음 |
| Warren Lotas | warrenlotas.com | 미국 스트리트 브랜드, Shopify 일반적 |
| The Trilogy Tapes | thetrilogytapes.com | 영국 소규모 레이블, Shopify 가능 |
| AXEL ARIGATO | axelarigato.com | 스웨덴 프리미엄, 자체 플랫폼 가능 |
| Séfr | sefr-online.com | 스웨덴 소규모, Shopify 가능 |
| Camperlab | camperlab.com | Shopify 또는 자체 |
| KA-YO | ka-yo.com | 스웨덴 편집숍 |
| SEVENSTORE | sevenstore.com | UK 편집숍, Shopify 사용 많음 |
| HIP | thehipstore.co.uk | UK 편집숍 |

→ 이 채널들은 Shopify일 경우 channel_probe.py가 이미 탐지했어야 함.
   실패 이유: 비공개 스토어 (password-protected) OR 봇 차단 OR 헤더 신호 부재

### Custom/Proprietary 플랫폼 가능성 높음

| 채널 | URL | 추정 플랫폼 |
|------|-----|----------|
| Stone Island | stoneisland.com | 자체 CMS (Salesforce Commerce Cloud 추정) |
| BAYCREW'S | baycrews.jp | 자체 CMS (일본 대형 패션그룹) |
| Harrods | harrods.com | 자체 CMS (이미 비활성화됨) |
| HBX | hbx.com | 자체 플랫폼 (HYPEBEAST 계열) |
| Kasina | kasina.co.kr | 한국 편집숍, 자체 또는 Cafe24 |
| ARKnets | arknets.co.jp | 일본 편집숍, 자체 또는 BASE |
| TIGHTBOOTH | shop.tightbooth.com | Shopify 추정 (shop. 서브도메인) |

### 특수 플랫폼

| 채널 | URL | 플랫폼 | 처리 방향 |
|------|-----|--------|---------|
| Mercari | jp.mercari.com | C2C 마켓플레이스 | 비활성화 (수집 불가) |
| BAYCREW'S | baycrews.jp | 자체 CMS 대형 | 비활성화 또는 Web scraping |
| MaisonShunIshizawa | maisonshunishizawa.online | 소규모, 자체 | 직접 탐색 필요 |

---

## 요구사항

### Step 1: 자동 플랫폼 재탐지 (channel_probe.py 활용)

T-068 수정 후 `--force-retag` 플래그로 NULL platform 32개 재탐지:

```bash
uv run python scripts/channel_probe.py --force-retag
# (--all 없이 기본 동작: NULL platform 채널만 대상)
```

예상 탐지 결과:
- Shopify: 5~10개 (비공개 스토어는 탐지되어도 수집 불가)
- WooCommerce: 1~3개 (ARKnets 등 일본 독립 편집숍)
- Custom/Unknown: 15~20개 잔류

### Step 2: Shopify 비공개 스토어 식별 + 비활성화

`channel_probe.py` 탐지 결과에서 Shopify로 확인되었으나 `/products.json` 401인 채널:

```bash
# 비공개 스토어 확인 스크립트
for url in $(sqlite3 data/fashion.db "SELECT url FROM channels WHERE platform='shopify' AND is_active=1"):
    curl -s -o /dev/null -w "%{http_code}" $url/products.json
done
```

비공개 스토어 → `channel_type='private'`으로 태깅 + `is_active=False` 처리.

### Step 3: 잠재 WooCommerce 채널 크롤 시도

NULL platform 채널 중 WooCommerce API 응답 채널 크롤:

```bash
# WooCommerce 탐지 + 크롤 (WooCommerce 크롤러는 T-062에서 구현됨)
uv run python scripts/crawl_products.py --channel-names 'ARKnets,COEVO,HBX'
```

### Step 4: 수집 불가 채널 비활성화

다음 채널은 구조적으로 수집 불가:

| 채널 | URL | 이유 |
|------|-----|------|
| Mercari (메루카리) | jp.mercari.com | C2C 마켓플레이스 (Shopify 아님) |
| BAYCREW'S | baycrews.jp | 대형 자체 CMS, 강한 봇 방어 |
| Stone Island | stoneisland.com | 자체 CMS + Cloudflare 방어 |
| HBX | hbx.com | 자체 플랫폼 (HYPEBEAST) |
| Harrods | harrods.com | 이미 비활성화 여부 확인 |

→ `deactivate_dead_channels.py` 또는 직접 비활성화 후 `deactivation_reason` JSON 기록.

### Step 5: 조사 보고서 출력

조사 완료 후 `reports/null_platform_audit_YYYYMMDD.md` 생성:

```markdown
# NULL Platform 채널 감사 보고서

## 요약
- 조사 대상: 32개
- 플랫폼 식별: N개 (Shopify N, WooCommerce N, Custom N)
- 수집 성공: N개
- 비활성화 권고: N개
- 잔류 미해결: N개

## 채널별 결과
...
```

---

## DoD

- [ ] NULL platform 32개 채널 `channel_probe.py --force-retag` 재탐지 완료
- [ ] Shopify 비공개 스토어 식별 → `channel_type='private'` 태깅 + 비활성화
- [ ] 수집 불가 확정 채널 (Mercari, BAYCREW'S 등) 비활성화
- [ ] WooCommerce 채널 최소 1개 수집 성공
- [ ] `reports/null_platform_audit_YYYYMMDD.md` 보고서 생성
- [ ] NULL platform 활성 채널 32개 → 10개 이하로 감소

---

## 검증

```bash
# 조사 후 NULL platform 잔류 수 확인
sqlite3 data/fashion.db "
SELECT is_active, COUNT(*) as n
FROM channels WHERE platform IS NULL
GROUP BY is_active;
"
# 목표: is_active=1이 10개 이하

# 신규 수집 채널 확인
sqlite3 data/fashion.db "
SELECT c.name, c.platform, COUNT(p.id) as products
FROM channels c
LEFT JOIN products p ON p.channel_id = c.id AND p.is_active=1
WHERE c.is_active=1
GROUP BY c.id
HAVING products > 0
ORDER BY products DESC;
"
```
