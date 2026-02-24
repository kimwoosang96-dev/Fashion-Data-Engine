"""
채널 전처리 스크립트

입력:  data/channels_input.csv
         컬럼: url (필수), page_title (선택)
출력:  data/channels_cleaned.csv   — 정상 채널
       data/channels_flagged.csv   — 검토 필요 항목 (비패션, 비공개 페이지 등)

처리 내용:
  - URL → 홈페이지 URL 정규화
  - 중복 제거 (도메인 기준)
  - 채널명: page_title → 자동 추론 순서
  - 채널 타입 1차 분류
  - 비패션 / 특수 도메인 플래깅
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
from rich.console import Console
from rich.table import Table

from fashion_engine.crawler.url_normalizer import (
    normalize_to_homepage,
    extract_domain,
    guess_channel_name,
    classify_channel_type,
)

console = Console()

INPUT_FILE = Path("data/channels_input.csv")
OUTPUT_FILE = Path("data/channels_cleaned.csv")
FLAGGED_FILE = Path("data/channels_flagged.csv")

# 패션과 무관하거나 편집샵이 아닌 도메인
SKIP_DOMAINS = {
    "wishket.com",          # IT 블로그
    "yozm.wishket.com",
}

# 검토 필요 플래그 도메인 (리스트에는 포함하되 타입 표시)
FLAG_DOMAINS = {
    "mercari.com":       "secondhand-marketplace",  # 중고 마켓 (개별 상품)
    "jp.mercari.com":    "secondhand-marketplace",
    "harrods.com":       "department-store",
    "baycrews.jp":       "department-store",
    "spigen.co.kr":      "non-fashion",
}

# 비공개/로그인 필요 URL 패턴
PRIVATE_PATH_PATTERNS = [
    r"/password$",
    r"/account/",
    r"/login",
    r"/signin",
]


def load_input(path: Path) -> pd.DataFrame:
    if not path.exists():
        console.print(f"[red]입력 파일 없음: {path}[/red]")
        sys.exit(1)

    df = pd.read_csv(path)
    # 헤더 소문자 정규화
    df.columns = [c.strip().lower() for c in df.columns]

    if "url" not in df.columns:
        console.print("[red]CSV에 'url' 컬럼이 없습니다.[/red]")
        sys.exit(1)

    return df


def extract_name_from_title(page_title: str) -> str | None:
    """페이지 제목에서 채널명 추출 — 파이프 구분자 뒤의 마지막 토큰 우선"""
    if not page_title or str(page_title) == "nan":
        return None
    parts = [p.strip() for p in str(page_title).split("|") if p.strip()]
    if parts:
        # 마지막 파트가 짧으면 (브랜드/스토어명) 그것을 사용
        if len(parts[-1]) <= 40:
            return parts[-1]
        if len(parts[0]) <= 40:
            return parts[0]
    return None


def is_private_url(url: str) -> bool:
    for pattern in PRIVATE_PATH_PATTERNS:
        if re.search(pattern, url, re.I):
            return True
    return False


def preprocess(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    rows = []
    flagged = []
    seen_domains = set()

    for _, row in df.iterrows():
        raw_url = str(row["url"]).strip()
        page_title = row.get("page_title", "")

        # 완전히 건너뛸 도메인
        domain_check = extract_domain(raw_url) if raw_url.startswith("http") else ""
        if any(skip in raw_url for skip in SKIP_DOMAINS):
            console.print(f"[dim]스킵 (비패션 도메인):[/dim] {raw_url}")
            continue

        # 비공개 URL → flagged
        if is_private_url(raw_url):
            flagged.append({
                "url": raw_url,
                "reason": "private-page",
                "page_title": page_title,
            })
            console.print(f"[yellow]플래그 (비공개):[/yellow] {raw_url}")
            continue

        homepage = normalize_to_homepage(raw_url)
        if not homepage:
            continue

        domain = extract_domain(homepage)

        # 도메인 중복 제거
        if domain in seen_domains:
            console.print(f"[dim]중복 제거:[/dim] {raw_url} → {domain}")
            continue
        seen_domains.add(domain)

        # 채널명 결정: page_title → URL 추론
        name = extract_name_from_title(page_title) or guess_channel_name(homepage)

        # 플래그 도메인 처리
        flag_type = next(
            (v for k, v in FLAG_DOMAINS.items() if k in homepage),
            None,
        )
        channel_type = flag_type or classify_channel_type(homepage)

        entry = {
            "name": name,
            "url": homepage,
            "original_url": raw_url if raw_url != homepage else "",
            "channel_type": channel_type,
            "country": guess_country(homepage),
            "is_active": True,
            "note": "검토 필요" if flag_type else "",
        }
        rows.append(entry)

    return rows, flagged


def guess_country(url: str) -> str:
    """URL 패턴으로 국가 추정"""
    if any(x in url for x in [".co.kr", ".kr/", "//kr."]):
        return "KR"
    if any(x in url for x in [".co.jp", ".jp/", "//jp."]):
        return "JP"
    if any(x in url for x in [".co.uk", ".uk/", "//uk."]):
        return "UK"
    if ".eu/" in url or ".eu" == url[-3:]:
        return "EU"
    if any(x in url for x in [".com.mx", "//mx."]):
        return "MX"
    return ""


def save_outputs(rows: list[dict], flagged: list[dict]) -> None:
    Path("data").mkdir(exist_ok=True)

    # 정상 채널
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_FILE, index=False)
    console.print(f"\n[green]저장:[/green] {OUTPUT_FILE} ({len(rows)}개 채널)")

    # 검토 필요
    if flagged:
        pd.DataFrame(flagged).to_csv(FLAGGED_FILE, index=False)
        console.print(f"[yellow]플래그:[/yellow] {FLAGGED_FILE} ({len(flagged)}개 — 수동 검토 권장)")


def print_summary(rows: list[dict]) -> None:
    table = Table(title=f"전처리 결과 ({len(rows)}개 채널)", show_lines=True)
    table.add_column("채널명", style="cyan", max_width=20)
    table.add_column("홈페이지 URL", style="green", max_width=35)
    table.add_column("타입", style="yellow")
    table.add_column("국가")
    table.add_column("비고", style="dim")

    for row in rows:
        table.add_row(
            row["name"],
            row["url"],
            row["channel_type"],
            row["country"] or "-",
            row.get("note", ""),
        )

    console.print(table)


def print_stats(rows: list[dict]) -> None:
    types = {}
    countries = {}
    for r in rows:
        types[r["channel_type"]] = types.get(r["channel_type"], 0) + 1
        countries[r["country"] or "unknown"] = countries.get(r["country"] or "unknown", 0) + 1

    console.print("\n[bold]타입별 분포:[/bold]")
    for k, v in sorted(types.items(), key=lambda x: -x[1]):
        console.print(f"  {k}: {v}개")

    console.print("\n[bold]국가별 분포:[/bold]")
    for k, v in sorted(countries.items(), key=lambda x: -x[1]):
        console.print(f"  {k or 'unknown'}: {v}개")


def main():
    console.print("[bold blue]Fashion Data Engine — 채널 전처리[/bold blue]\n")

    df = load_input(INPUT_FILE)
    console.print(f"입력: {len(df)}개 항목 로드\n")

    rows, flagged = preprocess(df)
    print_summary(rows)
    print_stats(rows)
    save_outputs(rows, flagged)


if __name__ == "__main__":
    main()
