# 채널 조사 결과

> 조사일: 2026-03-14
> 조사 방법: Playwright 실제 방문 + 공개 HTML/JSON 엔드포인트 확인
> 참고: 지시서에는 "31개 채널"로 적혀 있으나 실제 표에는 32개 채널이 기재되어 있어 32개 모두 조사함

## ETC Seoul

- URL: https://etcseoul.com
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [And Wander, Arc'teryx, Goldwin, Mont-Bell, ROA, Salomon, SATISFY]
- 전체 상품 cate_no: 24
- 세일 상품 cate_no: 1519
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | Arc'teryx | 1088 |
  | Goldwin | 1668 |
  | Mont-Bell | 1967 |
  | ROA | 1527 |
  | Salomon | 917 |
- 특이사항: `https://etcseoul.com/brand.html`에서 브랜드 인덱스를 확인했다. 의뢰서의 Auralee / Engineered Garments는 현재 공개 브랜드 인덱스에서는 직접 노출되지 않았다.

---

## 옵스큐라

- URL: https://obscura-store.com
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [Stein, Montbell, And Wander, Guidi, Tekla, Helinox]
- 전체 상품 cate_no: 28
- 세일 상품 cate_no: 401
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | 공개 브랜드 index | 미확인 |
- 특이사항: 공개 HTML에서는 SHOP / MEN / WOMEN / SHOES / ACC / SALE 구조만 확인됐다. 브랜드별 `cate_no`는 추가 클릭 탐색 없이 바로 노출되지 않았다.

---

## 더엑스샵

- URL: https://thexshop.co.kr
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [Carhartt WIP, Stüssy, Gramicci, Arc'teryx, Salomon, Snow Peak]
- 전체 상품 cate_no: 24
- 세일 상품 cate_no: 26
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | Carhartt WIP | 375 |
  | Stüssy | 571 |
  | Gramicci | 745 |
  | Arc'teryx | 1544 |
  | Salomon | 1062 |
  | Snow Peak | 1515 |
- 특이사항: 같은 브랜드가 남성/여성/협업 라인으로 중복 노출되어 `cate_no`가 여러 개 보였다. 표에는 기본 브랜드 카테고리 1개만 적었다.

---

## 에크루

- URL: https://ecru.co.kr
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [A.PRESSE, STANDALONE, PERVERZE, ANCELLM, NEIGHBORHOOD, BASKETCASE GALLERY]
- 전체 상품 cate_no: 1795
- 세일 상품 cate_no: 1817
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | A.PRESSE | 1531 |
  | STANDALONE | 1387 |
  | PERVERZE | 1901 |
  | ANCELLM | 1717 |
  | NEIGHBORHOOD | 1375 |
- 특이사항: `https://ecru.co.kr/product/maker.html`은 단순 카테고리형이지만, Playwright 기반 크롤러가 브랜드 링크를 추가 발견했다. 의뢰서의 Acne Studios / MSGM은 현재 공개 브랜드 인덱스에서 직접 확인되지 않았다.

---

## 아이디룩

- URL: https://idlook.co.kr
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [Sandro, Maje, A.P.C., Marimekko]
- 전체 상품 cate_no: 32
- 세일 상품 cate_no: 미확인
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | 공개 브랜드 index | 미확인 |
- 특이사항: 메인 공개 HTML에서는 `E-STORE` 링크(`/triple/common/estore.html?cate_no=32`)와 회사/매장 정보만 확인됐다. 브랜드별 `cate_no`는 현재 공개 네비게이션에서 노출되지 않는다.

---

## 슬로우스테디클럽

- URL: https://slowsteadyclub.com
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [Auralee, New Balance, Ciota, Graphpaper, MFPEN]
- 전체 상품 cate_no: 671
- 세일 상품 cate_no: 723
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | AURALEE | 259 |
  | NEW BALANCE | 275 |
  | CIOTA | 1763 |
  | GRAPHPAPER BASIC | 172 |
  | MFPEN | 406 |
- 특이사항: 브랜드 링크는 `/brand?cate_no=...` 패턴으로 노출된다. `GRAPHPAPER COLLECTION`은 별도 `cate_no=1778`로도 확인됐다.

---

## 아이앰샵

- URL: https://iamshop-online.com
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [AURALEE, TEATORA, Columbia, REMI RELIEF, REPRODUCTION OF FOUND, TAION]
- 전체 상품 cate_no: 5801
- 세일 상품 cate_no: 6746
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | AURALEE | 842 |
  | TEATORA | 947 |
  | Columbia | 7268 |
  | REMI RELIEF | 7274 |
  | REPRODUCTION OF FOUND | 5346 |
  | TAION | 967 |
- 특이사항: `https://iamshop-online.com/brands.html`에서 브랜드형 URL 패턴이 `/product/list-brand.html?cate_no=...`로 확인됐다. 의뢰서의 DANTON / MM6는 현재 브랜드 메뉴에는 직접 노출되지 않지만, 페이지 내부 공지/드롭 텍스트에는 반복 등장한다.

---

## 라이커샵

- URL: https://rhykershop.co.kr
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [Gimaguas, Diemme, Revéniomaker, Northworks]
- 전체 상품 cate_no: 493 / 494
- 세일 상품 cate_no: 495
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | Gimaguas | 565 |
  | Diemme | 500 |
  | Revéniomaker | 452 |
- 특이사항: 메인 네비게이션에는 Men / Women / New in / Brands만 노출된다. 일부 브랜드 `cate_no`는 에디토리얼 본문에 삽입된 실제 상품/카테고리 링크에서 확인했다. 의뢰서의 ROA / Carne Bollente는 현재 공개 브랜드 index에서 직접 찾지 못했다.

---

## 하이츠스토어

- URL: https://heights-store.com
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [Stüssy, Arc'teryx, Asics, Carne Bollente, Camper Lab, Bodega Rose]
- 전체 상품 cate_no: 1986
- 세일 상품 cate_no: 미확인
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | Stüssy | 206 |
  | Arc'teryx | 1760 |
  | Asics | 3753 |
  | Carne Bollente | 2635 |
  | Camper Lab | 2638 |
- 특이사항: Playwright 기반 브랜드 index에서 `/brand/detail.html?cate_no=...` 패턴이 대량 확인됐다. 의뢰서의 Have A Good Time은 현재 브랜드 index에서 직접 노출되지 않았다.

---

## 애딕티드 서울

- URL: https://addictedseoul.com
- 플랫폼: shopify
- 온라인 판매: 가능
- 취급 수입 브랜드: [Our Legacy, Acne Studios, Marni, Craig Green, J.W. Anderson, Wales Bonner]
- 전체 상품 cate_no: 해당 없음
- 세일 상품 cate_no: 해당 없음
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | Shopify vendor 기반 | 해당 없음 |
- 특이사항: `/products.json?limit=3` 접근이 200으로 확인됐다. Shopify 공개 API 기준으로 vendor 추출이 가능한 채널이다.

---

## 8DIVISION

- URL: https://www.8division.com
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [Gimaguas, KAMIYA, Gramicci, Arc'teryx, ASICS, GUIDI]
- 전체 상품 cate_no: 미확인
- 세일 상품 cate_no: 533
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | Gimaguas | 3227 |
  | KAMIYA | 3447 |
  | Gramicci | 273 |
  | Arc'teryx | 2646 |
- 특이사항: 공개 `cate_no` 링크가 800개 이상으로 매우 많고, 신상품/성별/카테고리/브랜드가 혼재돼 있다. `이번 주 입고된 신상품`은 `cate_no=2363`으로 확인됐다.

---

## Unipair

- URL: https://www.unipair.com
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [JOE'S GARAGE, Green Door 'Newman', UNIPAIR]
- 전체 상품 cate_no: 64
- 세일 상품 cate_no: 150
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | UNIPAIR | 232 |
  | &UNIPAIR | 264 |
  | JOE'S GARAGE | 257 |
  | Green Door 'Newman' | 42 |
- 특이사항: 해외 수입 브랜드보다는 슈즈 편집/자체 라인 비중이 커 보인다.

---

## GOOUTSTORE

- URL: https://gooutstore.cafe24.com
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [공개 브랜드 index 미노출]
- 전체 상품 cate_no: 미확인
- 세일 상품 cate_no: 미확인
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | 공개 브랜드 index | 미확인 |
- 특이사항: `brand.html`은 열리지만 브랜드별 `cate_no` 링크가 노출되지 않았다. 메인 구조는 Fashion `26`, Outdoor `27`, Goods `28` 섹션 중심이다.

---

## Alfred

- URL: https://www.thegreatalfred.com
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [공개 브랜드 index 미노출]
- 전체 상품 cate_no: 44
- 세일 상품 cate_no: 51
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | 공개 브랜드 index | 미확인 |
- 특이사항: 홈과 카테고리 페이지는 정상 동작하지만 브랜드별 공개 index는 찾지 못했다.

---

## Meclads

- URL: https://www.meclads.com
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [Adidas, Ancellm, Aton Tokyo, Batoner, Camiel Fortgens, Casey Casey, Ciota, F/CE, Goldwin, Guidi]
- 전체 상품 cate_no: 70
- 세일 상품 cate_no: 미확인
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | Adidas | 202 |
  | Ancellm | 188 |
  | Aton Tokyo | 119 |
  | Batoner | 53 |
  | Camiel Fortgens | 174 |
  | Casey Casey | 140 |
  | Ciota | 147 |
  | F/CE | 88 |
  | Goldwin | 156 |
  | Guidi | 99 |
- 특이사항: 모바일 리스트 뷰에서 브랜드별 카테고리(`/product/list_thumb.html?cate_no=...`)가 잘 노출된다.

---

## Openershop

- URL: https://www.openershop.co.kr
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [공개 브랜드 index 미노출]
- 전체 상품 cate_no: 828
- 세일 상품 cate_no: 1119
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | 공개 브랜드 index | 미확인 |
- 특이사항: 메타 설명상 "해외 디자이너 브랜드 편집샵"이지만, 공개 홈에서는 SHOP / NEWS / STYLING / Archive Sale만 바로 확인됐다.

---

## empty

- URL: https://www.empty.seoul.kr
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [MAD FRENZY, FLORENTINA LEITNER, LILLILLY, KARLAIDLAW]
- 전체 상품 cate_no: 미확인
- 세일 상품 cate_no: 868
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | MAD FRENZY | 750 |
  | FLORENTINA LEITNER | 783 |
  | LILLILLY | 749 |
  | KARLAIDLAW | 751 |
- 특이사항: 홈 공개 HTML에서 RAFFLE / SALE / 일부 브랜드 링크는 확인되지만, 전체 상품 카테고리는 명확히 노출되지 않았다.

---

## a.dresser

- URL: https://www.adressershop.com
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [NICENESS, AUBERGE, HERILL, HEUGN, LE YUCCA'S, MAATEE&SONS, OUTIL, PHIGVEL MAKERS Co., ANDERSON'S]
- 전체 상품 cate_no: 59
- 세일 상품 cate_no: 없음
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | NICENESS | 52 |
  | AUBERGE | 76 |
  | HERILL | 48 |
  | HEUGN | 47 |
  | LE YUCCA'S | 54 |
  | MAATEE&SONS | 49 |
  | OUTIL | 73 |
  | PHIGVEL MAKERS Co. | 50 |
  | ANDERSON'S | 81 |
- 특이사항: 모바일 페이지에서 브랜드 카테고리가 더 잘 노출된다. 브랜드 허브는 `Brand /product/list.html?cate_no=58`이다.

---

## MODE MAN

- URL: https://www.mode-man.com
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [Andersen-Andersen, Buzz Rickson's, Nigel Cabourn, orSlow, Pherrow's, Red Wing, Reproduction of Found, Sanders, Taion]
- 전체 상품 cate_no: 50
- 세일 상품 cate_no: 965
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | 공개 브랜드 index | 미확인 |
- 특이사항: 공개 페이지에서는 상품군 `cate_no`만 잘 보이고 브랜드 인덱스는 노출되지 않았다. 메타 키워드에서 데님/아메카지 수입 브랜드 구성이 강하게 확인된다.

---

## SCULP STORE

- URL: https://www.sculpstore.com
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [Arc'teryx, 424, AFIELD OUT, Anachronorm, ASKYURSELF, BAL, Clarks Originals, Cost Per Kilo, Crockett & Jones, DESCENTE ALLTERRAIN]
- 전체 상품 cate_no: 255
- 세일 상품 cate_no: 미확인
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | Arc'teryx | 811 |
  | 424 | 315 |
  | AFIELD OUT | 388 |
  | Anachronorm | 793 |
  | ASKYURSELF | 1153 |
  | BAL | 166 |
  | Clarks Originals | 306 |
  | Cost Per Kilo | 288 |
  | Crockett & Jones | 298 |
  | DESCENTE ALLTERRAIN | 1512 |
- 특이사항: 홈에서 `샵` 허브(`/category/샵/255/`)와 브랜드형 링크(`/product/brand.html?cate_no=...`)가 함께 노출된다.

---

## BIZZARE

- URL: https://www.bizzare.co.kr
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [AKIKOAOKI, ASKYURSELF, ALIVEFORM, DAIRIKU, FACCIES, JieDa, Levi's, Northwave, Oakley, Praying]
- 전체 상품 cate_no: 162
- 세일 상품 cate_no: 미확인
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | AKIKOAOKI | 424 |
  | ALIVEFORM | 405 |
  | ASKYURSELF | 457 |
  | DAIRIKU | 370 |
  | FACCIES | 371 |
  | JieDa | 367 |
  | Levi's | 417 |
  | Northwave | 418 |
  | Oakley | 437 |
  | Praying | 465 |
- 특이사항: 브랜드 허브는 `Brands.html?cate_no=318` 패턴이며, `product/maker.html`은 404였다.

---

## grds

- URL: https://www.grds.com
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [자체 슈즈 라인 중심]
- 전체 상품 cate_no: 103
- 세일 상품 cate_no: 없음
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | 공개 브랜드 index | 미확인 |
- 특이사항: 공개 구조는 blucher / boots / loafer / chelsea 등 자체 카테고리 중심이며 멀티브랜드 편집샵 신호는 약했다.

---

## Rino Store

- URL: https://www.rinostore.co.kr
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [Anatomica, Andersen-Andersen, Astorflex, Batoner, Camiel Fortgens, Ciota, Engineered Garments, FDMTL, Filson, Gramicci]
- 전체 상품 cate_no: 405
- 세일 상품 cate_no: 511
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | Anatomica | 401 |
  | Andersen-Andersen | 94 |
  | Astorflex | 361 |
  | Batoner | 369 |
  | Camiel Fortgens | 393 |
  | Ciota | 523 |
  | Engineered Garments | 544 |
  | FDMTL | 259 |
  | Filson | 546 |
  | Gramicci | 98 |
- 특이사항: 브랜드 허브 `https://www.rinostore.co.kr/rino/brand.html`에서 `/category/<brand>/<id>/` 패턴이 대량 확인됐다. `FINAL SALE`은 `cate_no=511`, 별도 `시즌오프`는 `cate_no=164`다.

---

## COEVO

- URL: https://www.coevo.com
- 플랫폼: custom
- 온라인 판매: 가능
- 취급 수입 브랜드: [Stone Island, C.P. Company, Acronym]
- 전체 상품 cate_no: 해당 없음
- 세일 상품 cate_no: 해당 없음
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | custom `brandCd` 패턴 | 예: `goods/goods_list.php?page=1&brandCd=149` |
- 특이사항: `/products.json`은 Shopify JSON이 아니라 홈페이지 HTML을 반환했다. URL 구조는 `goods_list.php?brandCd=`라서 Cafe24가 아닌 자체몰로 판단했다.

---

## ADEKUVER

- URL: https://www.adekuver.com
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [1017 ALYX 9SM, 3MAN, 44 LABEL GROUP, A-COLD-WALL, ANN DEMEULEMEESTER, HYKE, JEAN PAUL GAULTIER, JULIUS, KUSIKOHC]
- 전체 상품 cate_no: 59
- 세일 상품 cate_no: 1
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | 1017 ALYX 9SM | 78 |
  | 3MAN | 958 |
  | 44 LABEL GROUP | 1153 |
  | A-COLD-WALL | 384 |
  | ANN DEMEULEMEESTER | 83 |
  | HYKE | 277 |
  | JEAN PAUL GAULTIER | 1866 |
  | JULIUS | 1285 |
  | KUSIKOHC | 526 |
- 특이사항: 모바일 상품 상세 페이지에서 `ALL BRANDS /designers/list.html?cate_no=125`를 통해 브랜드 허브가 노출됐다.

---

## PARLOUR

- URL: https://www.parlour.kr
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [Alden, Crockett & Jones, J.M. Weston, La Botte Gardiane, Sanders, R.M. Williams, Berwick]
- 전체 상품 cate_no: 99
- 세일 상품 cate_no: 미확인
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | 공개 브랜드 index | 미확인 |
- 특이사항: 메타 설명에서 남성 구두 편집 구성은 명확하지만 공개 `maker.html`은 404였다. 현재는 SHOP 허브 위주 구조다.

---

## 블루스맨

- URL: https://www.bluesman.co.kr
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [Gramicci, Ordinary Fits, Paraboot, Resolute, Battenwear, orSlow, Champion, Warehouse, Post O'Alls, Deus]
- 전체 상품 cate_no: 25
- 세일 상품 cate_no: 75
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | 브랜드 허브 | 25 |
- 특이사항: 메타 키워드에서 아메리칸 캐주얼 수입 브랜드 구성이 확인됐다. 모바일 페이지 기준 `OUTLET`은 `266`, `USED PRODUCTS`는 `71`이다.

---

## EFFORTLESS

- URL: https://www.effortless-store.com
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [Engineered Garments, Engineered Garments Workaday, Footworks, Innat, John Mason Smith, Kanemasa Phil., MFPen, orSlow, kolor]
- 전체 상품 cate_no: 미확인
- 세일 상품 cate_no: 134
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | Engineered Garments | 334 |
  | Engineered Garments Workaday | 243 |
  | Footworks | 393 |
  | Innat | 386 |
  | John Mason Smith | 54 |
  | Kanemasa Phil. | 379 |
  | MFPen | 177 |
  | orSlow | 394 |
  | kolor | 246 |
- 특이사항: 브랜드 카테고리는 다수 확인됐지만 "전체 상품" 허브는 공개 페이지에서 바로 노출되지 않았다.

---

## NOCLAIM

- URL: https://www.noclaim.co.kr
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [New Balance, Veja, Aape, After Math, Engineered Garments, Nanamica, Needles, Danton, Ciota, Brain Dead]
- 전체 상품 cate_no: 52
- 세일 상품 cate_no: 544
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | New Balance | 1733 |
  | Veja | 1932 |
  | Aape | 1812 |
  | After Math | 1316 |
  | Engineered Garments | 845 |
  | Nanamica | 867 |
  | Needles | 868 |
  | Danton | 840 |
  | Ciota | 1158 |
  | Brain Dead | 1929 |
- 특이사항: 홈에서는 프로모션성 이름이 많아 혼입이 심했다. `product/sale.html?cate_no=544`에서 브랜드형 카테고리를 더 안정적으로 확인했다.

---

## Casestudy

- URL: https://www.casestudystore.co.kr
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [Adidas, Asics, Auralee, Aries, Carhartt WIP, Casablanca, C.P. Company, Brain Dead]
- 전체 상품 cate_no: 125
- 세일 상품 cate_no: 미확인
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | Adidas | 142 |
  | Asics | 52 |
  | Auralee | 216 |
  | Aries | 55 |
  | Carhartt WIP | 145 |
  | Casablanca | 56 |
  | C.P. Company | 211 |
  | Brain Dead | 432 |
- 특이사항: Playwright로 `https://casestudystore.co.kr/brands.html`을 직접 확인했고, 알파벳순 브랜드 인덱스가 안정적으로 노출됐다.

---

## APPLIXY

- URL: https://www.applixy.com
- 플랫폼: cafe24
- 온라인 판매: 가능
- 취급 수입 브랜드: [세컨핸드 플랫폼 특성상 고정 브랜드 리스트 미노출]
- 전체 상품 cate_no: 334
- 세일 상품 cate_no: 없음
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | 공개 브랜드 index | 미확인 |
- 특이사항: 메타 설명상 "지속가능한 패션을 추구하는 세컨핸드 플랫폼"으로 확인됐다. 고정 바잉 브랜드를 모아 보여주는 편집샵 구조와는 다소 다르다.

---

## TUNE.KR

- URL: https://tune.kr
- 플랫폼: shopify
- 온라인 판매: 가능
- 취급 수입 브랜드: [공개 브랜드 index 미노출]
- 전체 상품 cate_no: 해당 없음
- 세일 상품 cate_no: 해당 없음
- 브랜드별 cate_no:
  | 브랜드 | cate_no |
  |--------|---------|
  | Shopify collection 구조 | `/collections/...` |
- 특이사항: Playwright로 `https://tune.kr/collections/new-arrivals`를 직접 확인했고, `/collections/all`, `/launches`, `/membership-program` 등 Shopify형 컬렉션 구조가 보였다. `/products.json?limit=5`는 403 XML `AccessDenied`를 반환해 공개 JSON export는 막혀 있다.

---
