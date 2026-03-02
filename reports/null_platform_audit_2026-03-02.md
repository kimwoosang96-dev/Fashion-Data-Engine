# NULL Platform 채널 감사 보고서

- 작성일: 2026-03-02
- 과업: T-20260302-071

## 요약
- 조사 대상(초기): 32개 활성 채널 (`platform IS NULL`)
- 재탐지 실행: `channel_probe.py --force-retag` (NULL/unknown 대상)
- 재탐지 결과: `unknown=32` (추가 자동 식별 0)
- WooCommerce 수집 시도: 3개(ARKnets, COEVO, HBX) 모두 0개
- 비활성화 적용: 22개
- 최종 활성 NULL 플랫폼: 10개

## 실행 로그
1. `uv run python scripts/channel_probe.py --force-retag`
2. `uv run python scripts/crawl_products.py --channel-name ARKnets --no-alerts --skip-catalog --concurrency 1`
3. `uv run python scripts/crawl_products.py --channel-name COEVO --no-alerts --skip-catalog --concurrency 1`
4. `uv run python scripts/crawl_products.py --channel-name HBX --no-alerts --skip-catalog --concurrency 1`

## 비활성화 적용 채널 (22)
- ACRMTSM
- BAYCREW'S
- COEVO
- Camperlab
- F/CE
- Goldwin
- HBX
- Harrods
- KA-YO
- LTTT
- MaisonShunIshizawa store
- Mercari (메루카리)
- MusterWerk
- SEVENSTORE
- SHRED
- Stone Island
- TTTMSW
- The Trilogy Tapes
- VINAVAST
- browniegift
- wegenk
- 앤드헵 (Pheb)

## 잔류 활성 NULL 채널 (10)
- ARKnets
- AXEL ARIGATO
- HIP
- Kasina
- Rogues
- Séfr
- TIGHTBOOTH
- TINY OSAKA
- Warren Lotas
- thisisneverthat

## 판단 기준
- 최근 크롤 로그 `error_type='not_supported'` 반복
- 제품 0개 지속
- 마켓플레이스/대형 자체 CMS/강한 봇 차단 채널 우선 정리
- 후속 수동 리서치 필요 채널 10개는 활성 유지

## 남은 리스크
- 현재 실행 환경의 외부 DNS/접속 제약으로 일부 도메인 실수집 검증이 제한됨
- Railway 환경(T-070)에서 KR DNS 채널/일본 SaaS 실수집 재검증 필요
