# PRICE_HISTORY_PARTITION_01: PostgreSQL price_history RANGE 파티셔닝

**Task ID**: T-20260302-057
**Owner**: codex-dev
**Priority**: P1
**Labels**: backend, database, performance

---

## 배경

`price_history` 테이블은 현재 80k+ rows이며 전체 크롤 완료 시 수백만 rows로 급증 예정입니다.
PostgreSQL의 RANGE 파티셔닝을 적용해 월별 파티션으로 쿼리 성능과 아카이빙을 개선합니다.

**SQLite 환경에서는 이 마이그레이션을 완전히 건너뜁니다.**

**참고 파일**: `AGENTS.md`, `src/fashion_engine/models/price_history.py`, `alembic/versions/`

---

## 요구사항

### 전략 개요

1. 기존 `price_history` → `price_history_unpartitioned` 임시 이름 변경
2. RANGE 파티션 부모 테이블 `price_history` 신규 생성
3. 월별 파티션 미리 생성 (2026-01 ~ 2027-12, 총 24개)
4. 데이터 마이그레이션: `INSERT INTO price_history SELECT * FROM price_history_unpartitioned`
5. `price_history_unpartitioned` 삭제
6. 필요한 인덱스 재생성

### 파티션 파티셔닝 기준

```sql
PARTITION BY RANGE (crawled_at)
```

월별 파티션 명명 규칙: `price_history_{YYYY}_{MM:02d}`

---

### Alembic 마이그레이션

**파일**: `alembic/versions/xxxx_partition_price_history.py`

#### `upgrade()` 함수

```python
def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite 및 기타 환경 건너뜀
        return

    # 1. 기존 테이블 이름 변경
    op.rename_table("price_history", "price_history_unpartitioned")

    # 2. FK 및 인덱스 제거
    op.drop_constraint("price_history_product_id_fkey", "price_history_unpartitioned", type_="foreignkey")
    # ... 기타 제약 제거

    # 3. 파티션 부모 테이블 생성
    op.execute("""
        CREATE TABLE price_history (
            id          SERIAL,
            product_id  INTEGER NOT NULL,
            price       FLOAT NOT NULL,
            price_krw   FLOAT,
            currency    VARCHAR(10),
            is_sale     BOOLEAN NOT NULL DEFAULT FALSE,
            discount_rate FLOAT,
            crawled_at  TIMESTAMP NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, crawled_at)
        ) PARTITION BY RANGE (crawled_at)
    """)

    # 4. 월별 파티션 생성 (2026-01 ~ 2027-12)
    for year in [2026, 2027]:
        for month in range(1, 13):
            start = f"{year}-{month:02d}-01"
            if month == 12:
                end = f"{year+1}-01-01"
            else:
                end = f"{year}-{month+1:02d}-01"
            partition_name = f"price_history_{year}_{month:02d}"
            op.execute(f"""
                CREATE TABLE {partition_name}
                PARTITION OF price_history
                FOR VALUES FROM ('{start}') TO ('{end}')
            """)

    # 5. 인덱스 재생성
    op.execute("""
        CREATE INDEX idx_price_history_product_crawled
        ON price_history (product_id, crawled_at DESC)
    """)

    # 6. 데이터 마이그레이션
    op.execute("""
        INSERT INTO price_history
        SELECT id, product_id, price, price_krw, currency, is_sale, discount_rate, crawled_at
        FROM price_history_unpartitioned
    """)

    # 7. 임시 테이블 삭제
    op.execute("DROP TABLE price_history_unpartitioned")
```

#### `downgrade()` 함수

```python
def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # 파티션 테이블 → 일반 테이블로 복원
    op.execute("ALTER TABLE price_history RENAME TO price_history_partitioned_bak")
    op.execute("""
        CREATE TABLE price_history AS
        SELECT * FROM price_history_partitioned_bak
    """)
    op.execute("DROP TABLE price_history_partitioned_bak CASCADE")
    # 인덱스/FK 재생성 (원래 상태로)
```

---

### 주의사항

1. **SQLite bypass**: `bind.dialect.name != "postgresql"` 체크 필수 — 로컬 개발 환경 보호
2. **FK 재생성**: `product_id → products.id` FK를 파티션 부모에 재등록
   - PostgreSQL 파티션 테이블은 FK 참조 가능하나, 부모 테이블에 선언해야 함
3. **Railway 운영 중 마이그레이션**: 테이블 이름 변경 전에 크롤 스케줄러 일시 중지 권장
4. **기본 파티션**: `price_history_default` 파티션 추가 (범위 초과 데이터 수용):
   ```sql
   CREATE TABLE price_history_default
   PARTITION OF price_history DEFAULT
   ```

---

## DoD (완료 기준)

- [ ] Alembic 마이그레이션 파일 존재
- [ ] SQLite 환경에서 `alembic upgrade head` — 마이그레이션 skip (에러 없음)
- [ ] PostgreSQL 환경에서 `alembic upgrade head` — 파티션 테이블 생성 + 데이터 이전
- [ ] `EXPLAIN ANALYZE SELECT * FROM price_history WHERE crawled_at > NOW() - INTERVAL '7 days'` — 파티션 pruning 확인 (`Rows Removed by Filter` 대폭 감소)

## 검증

```bash
# SQLite: 건너뜀 확인
uv run alembic upgrade head
# → 에러 없이 완료

# PostgreSQL (Railway):
DATABASE_URL=postgresql+asyncpg://... uv run alembic upgrade head

# 파티션 확인
psql $DATABASE_URL -c "
SELECT tablename FROM pg_tables
WHERE tablename LIKE 'price_history_%'
ORDER BY tablename;
"

# 데이터 이전 확인
psql $DATABASE_URL -c "SELECT COUNT(*) FROM price_history"
```
