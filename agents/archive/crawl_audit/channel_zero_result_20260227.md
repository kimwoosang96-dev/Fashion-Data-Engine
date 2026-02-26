# DB_01 Report — 0결과 채널 원인 분류 (2026-02-27)

기준 데이터:
- source: `data/fashion.db`
- 대상: `channels.channel_type='edit-shop' AND is_active=1`
- 측정 시점: 2026-02-27 전체 재크롤 직후

## 요약
- 전체 edit-shop: **80개**
- 브랜드 1개 이상 링크: **47개**
- 0결과 채널: **33개**

## 0결과 채널 라벨링 (100%)

| 채널 | URL | 라벨 | 근거 | 권장 액션 |
|---|---|---|---|---|
| Alfred | https://www.thegreatalfred.com | empty_or_low_inventory | navigation 기반에서도 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| BIZZARE | https://www.bizzare.co.kr | selector_mismatch | custom 전략 결과 0건 | custom selector 재정의 |
| Bodega | https://bdgastore.com | blocked_or_bot | navigation 기반 공개 브랜드 링크 제한 | 브랜드 페이지 전용 전략 추가 |
| COEVO | https://www.coevo.com | selector_mismatch | custom 전략 결과 0건 | custom selector 재정의 |
| Casestudy | https://www.casestudystore.co.kr | unknown | 브랜드 페이지/네비게이션 모두 무효 | 구조 점검 후 전략 분기 |
| ECRU Online | https://www.ecru.co.kr | selector_mismatch | custom 전략 결과 0건 | custom selector 재정의 |
| EFFORTLESS | https://www.effortless-store.com | selector_mismatch | custom 전략 결과 0건 | custom selector 재정의 |
| GOOUTSTORE | https://gooutstore.cafe24.com | selector_mismatch | custom 전략 결과 0건 | Cafe24 전용 selector 보강 |
| Kasina | https://www.kasina.co.kr | selector_mismatch | custom 전략 결과 0건 | custom selector 재정의 |
| Kerouac | https://www.kerouac.okinawa | ssl_error | HTTPS SSL 오류 이력, HTTP fallback에서도 0건 | SSL/도메인 상태 수동 확인 |
| Laid back | https://laidback0918.shop-pro.jp | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| MODE MAN | https://www.mode-man.com | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| Meclads | https://www.meclads.com | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| MusterWerk | https://www.musterwerk-sud.com | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| Openershop | https://www.openershop.co.kr | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| PARLOUR | https://www.parlour.kr | selector_mismatch | custom 전략 결과 0건 | custom selector 재정의 |
| ROOM ONLINE STORE | https://www.room-onlinestore.jp | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| Rino Store | https://www.rinostore.co.kr | selector_mismatch | custom 전략 결과 0건 | custom selector 재정의 |
| Rogues | https://www.rogues.co.jp | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| SEVENSTORE | https://www.sevenstore.com | blocked_or_bot | navigation만 노출, 브랜드 링크 제한 | brand 전용 경로 수집 |
| SHRED | https://www.srd-osaka.com | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| THEXSHOP | https://www.thexshop.co.kr | selector_mismatch | custom 전략 결과 0건 | custom selector 재정의 |
| TINY OSAKA | https://www.tinyworld.jp | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| TITY | https://tity.ocnk.net | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| TUNE.KR | https://www.tune.kr | ssl_error | HTTPS SSL 오류 이력, HTTP fallback에서도 0건 | SSL/도메인 상태 수동 확인 |
| UNDERCOVER Kanazawa | https://undercoverk.theshop.jp | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| VINAVAST | https://www.vinavast.co | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| a.dresser | https://www.adressershop.com | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| browniegift | https://www.brownieonline.jp | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| grds | https://www.grds.com | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| wegenk | https://www.wegenk.com | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| 블루스맨 (Bluesman) | https://www.bluesman.co.kr | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |
| 앤드헵 (Pheb) | https://shop.pheb.jp | empty_or_low_inventory | 공개 브랜드 링크 미검출 | 월 1회 샘플 확인 |

## 혼재 데이터 정제 결과
- 실행: `.venv/bin/python scripts/cleanup_mixed_brand_channel.py`
- 결과: `suspects=21, keep=0, safe_to_delete=0, manual_review=21`
- 결론: 자동 삭제 대상 없음 (삭제 미실행)

## 인덱스 제안 (우선순위)
1. `CREATE INDEX idx_products_sale_active ON products (is_sale, is_active, id);`
   - 대상: `/products/sales`, `/products/sales-highlights`
2. `CREATE INDEX idx_products_product_key ON products (product_key);`
   - 대상: `/products/compare/{product_key}`, `/products/price-history/{product_key}`
3. `CREATE INDEX idx_price_history_product_crawled ON price_history (product_id, crawled_at DESC);`
   - 대상: latest price subquery, 히스토리 조회
4. `CREATE INDEX idx_brands_slug ON brands (slug);`
   - 대상: `/brands/{slug}`, `/brands/{slug}/products`, `/brands/{slug}/channels`
5. `CREATE INDEX idx_products_brand_sale ON products (brand_id, is_sale, id);`
   - 대상: 브랜드 상세 세일 필터
6. `CREATE INDEX idx_channel_brands_channel_brand ON channel_brands (channel_id, brand_id);`
   - 대상: 채널-브랜드 조인

## 후속 실행 우선순위
1. `selector_mismatch` 채널 9개 custom selector 재정의
2. `ssl_error` 채널 2개 도메인/SSL 상태 수동 확인 후 canonical URL 갱신
3. `blocked_or_bot` 채널 2개 브랜드 전용 진입경로(브랜드 디렉터리 URL) 추가
