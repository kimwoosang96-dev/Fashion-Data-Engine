"""
제품 0개 채널(또는 전체 채널) 플랫폼 탐지/HTTP 상태 진단 스크립트.

기능:
- 메인 URL HTTP 상태 코드 확인
- Shopify 추정: /products.json?limit=1
- Cafe24 추정: /product/list.html?cate_no=1
- CSV 저장
- --apply 시 channels.platform 업데이트
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import httpx
from rich.console import Console
from rich.table import Table
from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fashion_engine.database import AsyncSessionLocal, init_db  # noqa: E402
from fashion_engine.models.channel import Channel  # noqa: E402
from fashion_engine.models.product import Product  # noqa: E402
from fashion_engine.services.channel_service import update_platform  # noqa: E402

console = Console()
GENERAL_PROBE_SEM = asyncio.Semaphore(10)
SHOPIFY_PROBE_SEM = asyncio.Semaphore(2)

_URL_PLATFORM_MAP: dict[str, str] = {
    "shop-pro.jp": "makeshop",
    "buyshop.jp": "stores-jp",
    "theshop.jp": "stores-jp",
    "stores.jp": "stores-jp",
    "ocnk.net": "ochanoko",
    "cafe24.com": "cafe24",
    "echosting.com": "cafe24",
    "base.shop": "base-jp",
    "thebase.in": "base-jp",
}


@dataclass
class ProbeTarget:
    channel_id: int
    name: str
    url: str
    platform: str | None


@dataclass
class ProbeResult:
    channel_id: int
    name: str
    url: str
    http_status: int | None
    shopify: bool
    cafe24: bool
    makeshop: bool
    stores_jp: bool
    ochanoko: bool
    blocked: bool
    platform_detected: str | None
    note: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="제품 0개 채널 플랫폼 진단")
    p.add_argument("--all", action="store_true", help="전체 활성 채널 대상 (기본: 제품 0개 채널)")
    p.add_argument(
        "--force-retag",
        action="store_true",
        help="이미 platform이 설정된 채널도 강제 재탐지 (rate-limit 위험)",
    )
    p.add_argument("--apply", action="store_true", help="감지된 platform를 DB에 반영")
    p.add_argument(
        "--output",
        default=f"reports/channel_probe_{datetime.now().strftime('%Y-%m-%d')}.csv",
        help="CSV 출력 경로",
    )
    return p.parse_args()


def _detect_platform_from_url(url: str) -> str | None:
    host = urlparse(url).netloc.lower()
    for pattern, platform in _URL_PLATFORM_MAP.items():
        if pattern in host:
            return platform
    return None


def _detect_platform_from_response(resp: httpx.Response) -> str | None:
    powered_by = resp.headers.get("x-powered-by", "").lower()
    cookies = " ".join(resp.headers.get_list("set-cookie")).lower()
    html_lower = (resp.text or "")[:10000].lower()
    if "makeshop" in powered_by:
        return "makeshop"
    if "cafe24" in powered_by or "echosting" in cookies:
        return "cafe24"
    if "stores.js" in html_lower or "buyshop.jp/js" in html_lower:
        return "stores-jp"
    if "ocnk" in html_lower or "ochanoko" in html_lower:
        return "ochanoko"
    if "cafe24" in html_lower or "xans-layout" in html_lower:
        return "cafe24"
    return None


async def _check_home(client: httpx.AsyncClient, base_url: str) -> tuple[int | None, str, httpx.Response | None]:
    try:
        resp = await client.get(base_url, timeout=8)
        return resp.status_code, "", resp
    except Exception as exc:
        return None, str(exc)[:180], None


async def _check_shopify(client: httpx.AsyncClient, base_url: str) -> bool:
    url = f"{base_url.rstrip('/')}/products.json?limit=1"
    try:
        resp = await client.get(url, timeout=8)
        if resp.status_code != 200:
            return False
        data = resp.json()
        return isinstance(data, dict) and "products" in data
    except Exception:
        return False


def _need_shopify_probe(target: ProbeTarget, url_platform: str | None) -> bool:
    if (target.platform or "").lower() == "shopify":
        return True
    # URL 신호로 다른 플랫폼이 명확하면 Shopify 확인 생략
    if url_platform in {"cafe24", "stores-jp", "makeshop", "ochanoko", "base-jp"}:
        return False
    return True


async def _check_cafe24(client: httpx.AsyncClient, base_url: str) -> bool:
    url = f"{base_url.rstrip('/')}/product/list.html?cate_no=1"
    try:
        resp = await client.get(url, timeout=8)
        if resp.status_code != 200:
            return False
        body = resp.text.lower()
        return "cafe24" in body or "xans-product" in body
    except Exception:
        return False


def _detect_platform(
    *,
    url_platform: str | None,
    resp_platform: str | None,
    shopify: bool,
    cafe24: bool,
    makeshop: bool,
    stores_jp: bool,
    ochanoko: bool,
) -> str | None:
    if shopify:
        return "shopify"
    if cafe24:
        return "cafe24"
    if makeshop:
        return "makeshop"
    if stores_jp:
        return "stores-jp"
    if ochanoko:
        return "ochanoko"
    if resp_platform:
        return resp_platform
    if url_platform:
        return url_platform
    return None


async def _probe_one(client: httpx.AsyncClient, target: ProbeTarget) -> ProbeResult:
    async with GENERAL_PROBE_SEM:
        url_platform = _detect_platform_from_url(target.url)
        http_status, note, resp = await _check_home(client, target.url)
        resp_platform = _detect_platform_from_response(resp) if resp is not None else None
        makeshop = (url_platform == "makeshop") or (resp_platform == "makeshop")
        stores_jp = (url_platform == "stores-jp") or (resp_platform == "stores-jp")
        ochanoko = (url_platform == "ochanoko") or (resp_platform == "ochanoko")
        shopify = False
        if _need_shopify_probe(target, url_platform):
            async with SHOPIFY_PROBE_SEM:
                shopify = await _check_shopify(client, target.url)
        cafe24 = await _check_cafe24(client, target.url)
        blocked = http_status in {403, 429, 503}
        detected = _detect_platform(
            url_platform=url_platform,
            resp_platform=resp_platform,
            shopify=shopify,
            cafe24=cafe24,
            makeshop=makeshop,
            stores_jp=stores_jp,
            ochanoko=ochanoko,
        )
        if not detected and not note:
            note = "custom platform suspected"
        if blocked and not note:
            note = f"bot protection suspected (HTTP {http_status})"
        return ProbeResult(
            channel_id=target.channel_id,
            name=target.name,
            url=target.url,
            http_status=http_status,
            shopify=shopify,
            cafe24=cafe24,
            makeshop=makeshop,
            stores_jp=stores_jp,
            ochanoko=ochanoko,
            blocked=blocked,
            platform_detected=detected,
            note=note,
        )


async def probe_channel(url: str, name: str | None = None) -> ProbeResult:
    """단일 URL 접근성/플랫폼 프로브."""
    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 channel-probe"},
    ) as client:
        return await _probe_one(
            client,
            ProbeTarget(
                channel_id=0,
                name=name or url,
                url=url,
                platform=None,
            ),
        )


async def _load_targets(*, include_all: bool, force_retag: bool) -> tuple[list[ProbeTarget], int]:
    async with AsyncSessionLocal() as db:
        stmt = (
            select(
                Channel.id,
                Channel.name,
                Channel.url,
                Channel.platform,
                func.count(Product.id).label("product_count"),
            )
            .outerjoin(Product, Product.channel_id == Channel.id)
            .where(Channel.is_active == True)  # noqa: E712
            .group_by(Channel.id)
            .order_by(Channel.name.asc())
        )
        if not include_all:
            # 기본 모드: 제품 0개 + NULL/unknown platform 채널만 감사
            stmt = (
                stmt.having(func.count(Product.id) == 0)
                .having((Channel.platform.is_(None)) | (Channel.platform == "unknown"))
            )
        rows = (await db.execute(stmt)).all()
    targets = [
        ProbeTarget(
            channel_id=int(r.id),
            name=str(r.name),
            url=str(r.url),
            platform=str(r.platform) if r.platform else None,
        )
        for r in rows
    ]
    if force_retag and include_all:
        return targets, 0
    filtered = [t for t in targets if not t.platform or t.platform == "unknown"]
    skipped = len(targets) - len(filtered)
    return filtered, skipped


def _print_table(results: Iterable[ProbeResult]) -> None:
    table = Table(title="채널 플랫폼 진단 결과", show_lines=True)
    table.add_column("ID", justify="right")
    table.add_column("채널")
    table.add_column("HTTP", justify="right")
    table.add_column("Shopify", justify="center")
    table.add_column("Cafe24", justify="center")
    table.add_column("MakeShop", justify="center")
    table.add_column("STORES", justify="center")
    table.add_column("OCNK", justify="center")
    table.add_column("Blocked", justify="center")
    table.add_column("Detected")
    table.add_column("Note")
    for r in results:
        table.add_row(
            str(r.channel_id),
            r.name,
            str(r.http_status) if r.http_status is not None else "-",
            "Y" if r.shopify else "-",
            "Y" if r.cafe24 else "-",
            "Y" if r.makeshop else "-",
            "Y" if r.stores_jp else "-",
            "Y" if r.ochanoko else "-",
            "Y" if r.blocked else "-",
            r.platform_detected or "-",
            r.note or "",
        )
    console.print(table)


def _write_csv(results: list[ProbeResult], output_path: str) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "channel_id",
                "name",
                "url",
                "http_status",
                "shopify",
                "cafe24",
                "makeshop",
                "stores_jp",
                "ochanoko",
                "blocked",
                "platform_detected",
                "note",
            ]
        )
        for r in results:
            w.writerow(
                [
                    r.channel_id,
                    r.name,
                    r.url,
                    r.http_status if r.http_status is not None else "",
                    r.shopify,
                    r.cafe24,
                    r.makeshop,
                    r.stores_jp,
                    r.ochanoko,
                    r.blocked,
                    r.platform_detected or "",
                    r.note,
                ]
            )
    return out


async def _apply_platform(results: list[ProbeResult]) -> int:
    updated = 0
    async with AsyncSessionLocal() as db:
        for r in results:
            if not r.platform_detected:
                continue
            changed = await update_platform(db, r.channel_id, r.platform_detected)
            if changed:
                updated += 1
        if updated:
            await db.commit()
    return updated


async def run(*, include_all: bool, force_retag: bool, apply: bool, output: str) -> int:
    await init_db()
    targets, skipped = await _load_targets(include_all=include_all, force_retag=force_retag)
    console.print(f"[cyan]진단 대상 채널[/cyan]: {len(targets)}개")
    if skipped:
        console.print(
            f"[yellow]스킵[/yellow]: {skipped}개 (platform 이미 설정됨, --force-retag으로 재탐지 가능)"
        )
    if force_retag:
        console.print("[bold yellow]경고[/bold yellow]: --force-retag는 rate-limit 위험이 있습니다.")
        if not include_all:
            console.print("[dim]안내[/dim]: --all 없이 실행 시 NULL/unknown 플랫폼 대상만 재탐지합니다.")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [_probe_one(client, t) for t in targets]
        results = await asyncio.gather(*tasks)

    results = sorted(results, key=lambda r: (r.platform_detected is None, r.name.lower()))
    _print_table(results)
    platform_counts: dict[str, int] = {}
    for r in results:
        key = r.platform_detected or "unknown"
        platform_counts[key] = platform_counts.get(key, 0) + 1
    summary = ", ".join(f"{k}={v}" for k, v in sorted(platform_counts.items()))
    console.print(f"[cyan]플랫폼 분류 요약[/cyan]: {summary}")
    csv_path = _write_csv(results, output)
    console.print(f"[green]CSV 저장 완료[/green]: {csv_path}")

    if apply:
        updated = await _apply_platform(results)
        console.print(f"[bold green]DB 업데이트[/bold green]: {updated}개")
    else:
        console.print("[yellow]dry-run: --apply로 platform 반영 가능[/yellow]")
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(
        asyncio.run(
            run(
                include_all=bool(args.all),
                force_retag=bool(args.force_retag),
                apply=bool(args.apply),
                output=str(args.output),
            )
        )
    )
