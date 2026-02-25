# CODEX Issue #01 완료 보고서

작성일: 2026-02-25

## 목표
- Cafe24/커스텀 전략 개선
- 브랜드 중복 정규화 보강
- edit-shop 75개 전체 크롤 실행
- 0 결과 채널 목록 정리 및 전략 추가

## 1) 코드 변경

### A. Cafe24 및 커스텀 전략 개선
- 파일: `src/fashion_engine/crawler/brand_crawler.py`
- 반영 내용:
  - `8division.com` 전용 전략 추가 및 셀렉터 정교화:
    - `ul.sub-menu.sub-menu-brands > li > a[href*='cate_no=']`
  - 0결과 우선/연관 Cafe24 채널 전략 추가:
    - `kasina.co.kr`, `thexshop.co.kr`, `unipair.com`, `parlour.kr`
    - `obscura-store.com`, `bizzare.co.kr`, `ecru.co.kr`, `rinostore.co.kr`, `coevo.com`, `gooutstore.cafe24.com`, `effortless-store.com`
  - Cafe24 탐색 보강:
    - `ul.menuCategory > li` 포함
    - nav 루트가 없을 때도 `cate_no` 링크만 제한적으로 탐색
  - 콜라보 서브카테고리 필터 임계치 조정:
    - `len(name) > 40` + `by/x/×` 패턴

### B. 브랜드 upsert 중복 보정
- 파일: `src/fashion_engine/services/brand_service.py`
- 반영 내용:
  - `slug` 정확 일치 외에, 숫자 토큰 2개 이상인 slug에 대해
    - 동일 숫자 토큰을 모두 포함하는 기존 slug 후보 1건일 때 재사용
  - 의도:
    - 한글/영문 표기 차이로 생기는 숫자 기반 변형 slug를 보정

### C. 전체 재크롤 시 stale 링크 제거
- 파일: `scripts/crawl_brands.py`
- 반영 내용:
  - 채널 크롤 시작 시 해당 채널의 기존 `channel_brands` 연결 삭제 후 재삽입
  - 효과:
    - 과거 잘못 수집된 링크가 누적되지 않고 최신 크롤 결과로 갱신

## 2) 실행 로그 요약

### 사전 검증 (`--limit 3`)
- 실행: `.venv/bin/python scripts/crawl_brands.py --limit 3`
- 결과:
  - `+81`: 61 (shopify)
  - `8DIVISION`: **48** (custom)
  - `ADDICTED`: 77 (shopify)
- 판단:
  - 이슈 문서의 8DIVISION 과다 추출(기존 600+ 수준) 문제는 개선됨

### 전체 실행 (75 edit-shop)
- 실행: `.venv/bin/python scripts/crawl_brands.py`
- 주요 결과:
  - edit-shop 총 75개 중 브랜드 1개 이상 추출: **43개**
  - 0 결과: **32개**
  - `channel_brands` 총 건수: **2557**
  - 브랜드 총 수: **2508**

### 실행 중 오류(채널 접근/SSL)
- `Kerouac` (`https://www.kerouac.okinawa`)
  - `net::ERR_SSL_VERSION_OR_CIPHER_MISMATCH`
- `TUNE.KR` (`https://www.tune.kr`)
  - `net::ERR_SSL_VERSION_OR_CIPHER_MISMATCH`

## 3) 0 결과 채널 목록 (10개 이상 조건 충족으로 전체 기재)

1. Alfred — `https://www.thegreatalfred.com`
2. BIZZARE — `https://www.bizzare.co.kr`
3. COEVO — `https://www.coevo.com`
4. Casestudy — `https://www.casestudystore.co.kr`
5. ECRU Online — `https://www.ecru.co.kr`
6. EFFORTLESS — `https://www.effortless-store.com`
7. GOOUTSTORE — `https://gooutstore.cafe24.com`
8. Kasina — `https://www.kasina.co.kr`
9. Kerouac — `https://www.kerouac.okinawa`
10. Laid back — `https://laidback0918.shop-pro.jp`
11. MODE MAN — `https://www.mode-man.com`
12. Meclads — `https://www.meclads.com`
13. MusterWerk — `https://www.musterwerk-sud.com`
14. Openershop — `https://www.openershop.co.kr`
15. PARLOUR — `https://www.parlour.kr`
16. ROOM ONLINE STORE — `https://www.room-onlinestore.jp`
17. Rino Store — `https://www.rinostore.co.kr`
18. Rogues — `https://www.rogues.co.jp`
19. SEVENSTORE — `https://www.sevenstore.com`
20. SHRED — `https://www.srd-osaka.com`
21. THEXSHOP — `https://www.thexshop.co.kr`
22. TINY OSAKA — `https://www.tinyworld.jp`
23. TITY — `https://tity.ocnk.net`
24. TUNE.KR — `https://www.tune.kr`
25. UNDERCOVER Kanazawa — `https://undercoverk.theshop.jp`
26. VINAVAST — `https://www.vinavast.co`
27. a.dresser — `https://www.adressershop.com`
28. browniegift — `https://www.brownieonline.jp`
29. grds — `https://www.grds.com`
30. wegenk — `https://www.wegenk.com`
31. 블루스맨 (Bluesman) — `https://www.bluesman.co.kr`
32. 앤드헵 (Pheb) — `https://shop.pheb.jp`

## 4) 결과 해석
- 8DIVISION 과다 추출 문제는 해결(661 → 48).
- 전체 edit-shop 커버리지는 개선됐지만(기존 6개 성공 → 43개 성공), 여전히 32개 0결과 채널이 남아 후속 전략 보강 필요.
- 특히 Cafe24라도 사이트별 DOM 차이가 커서 `maker.html` 단일 패턴만으로는 한계가 확인됨.

## 5) 변경 파일
- `src/fashion_engine/crawler/brand_crawler.py`
- `src/fashion_engine/services/brand_service.py`
- `scripts/crawl_brands.py`
- `CODEX_ISSUE_01_REPORT.md`
