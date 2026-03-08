"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  addWatchlistItem,
  getBrand,
  getBrandChannels,
  getBrandCollabs,
  getBrandDirectors,
  getBrandNews,
  getBrandProducts,
  getBrandSaleIntel,
} from "@/lib/api";
import type { Brand, BrandDirector, BrandSaleIntel, Channel, CollabItem, FashionNews, Product } from "@/lib/types";
import { ProductCard } from "@/components/ProductCard";

const TIER_COLORS: Record<string, string> = {
  "high-end": "bg-amber-100 text-amber-800",
  premium: "bg-fuchsia-100 text-fuchsia-800",
  street: "bg-zinc-900 text-white",
  sports: "bg-blue-100 text-blue-800",
  spa: "bg-emerald-100 text-emerald-800",
};

export function BrandDetailClient({ slug }: { slug: string }) {
  const [brand, setBrand] = useState<Brand | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [news, setNews] = useState<FashionNews[]>([]);
  const [directors, setDirectors] = useState<BrandDirector[]>([]);
  const [collabs, setCollabs] = useState<CollabItem[]>([]);
  const [saleIntel, setSaleIntel] = useState<BrandSaleIntel | null>(null);
  const [saleOnly, setSaleOnly] = useState(false);
  const [watchMessage, setWatchMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [brandRes, channelsRes, productsRes, directorsRes, collabsRes, intelRes] = await Promise.all([
          getBrand(slug),
          getBrandChannels(slug),
          getBrandProducts(slug, false, 500),
          getBrandDirectors(slug),
          getBrandCollabs(slug),
          getBrandSaleIntel(slug).catch(() => null),
        ]);
        setBrand(brandRes);
        setChannels(channelsRes);
        setProducts(productsRes);
        setDirectors(directorsRes);
        setCollabs(collabsRes);
        setSaleIntel(intelRes);
        const newsRes = await getBrandNews(slug, 20);
        setNews(newsRes);
      } catch (e) {
        setError(e instanceof Error ? e.message : "브랜드 데이터를 불러오지 못했습니다.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [slug]);

  useEffect(() => {
    if (!brand) return;
    const loadProducts = async () => {
      try {
        const result = await getBrandProducts(brand.slug, saleOnly, 500);
        setProducts(result);
      } catch (e) {
        setError(e instanceof Error ? e.message : "제품 목록을 불러오지 못했습니다.");
      }
    };
    void loadProducts();
  }, [saleOnly, brand]);

  const saleCount = useMemo(() => products.filter((p) => p.is_sale).length, [products]);
  const seasonalityMax = Math.max(...(saleIntel?.monthly_sale_history.map((row) => row.product_count) ?? [1]));

  if (loading) return <div className="p-6 text-sm text-gray-400">로딩 중...</div>;
  if (error || !brand) return <div className="p-6 text-sm text-red-500">{error ?? "브랜드를 찾을 수 없습니다."}</div>;
  const tierTone = TIER_COLORS[brand.tier ?? ""] ?? "bg-zinc-100 text-zinc-700";

  return (
    <div className="space-y-6 p-6">
      <div>
        <Link href="/brands" className="text-xs text-gray-400 hover:text-gray-600">← 브랜드 목록</Link>
        <h1 className="mt-1 text-2xl font-bold">{brand.name}</h1>
        <div className="mt-2 flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-gray-700">{brand.slug}</span>
          <span className={`rounded-full px-2 py-0.5 ${tierTone}`}>{brand.tier ?? "tier 미분류"}</span>
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-gray-700">{brand.origin_country ?? "국가 미상"}</span>
          {brand.instagram_url && (
            <a
              href={brand.instagram_url}
              target="_blank"
              rel="noreferrer"
              className="rounded-full bg-pink-100 px-2 py-0.5 text-pink-700 hover:underline"
            >
              Instagram
            </a>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <StatCard label="총 제품 수" value={products.length} />
        <StatCard label="세일 제품 수" value={saleCount} />
        <StatCard label="취급 채널 수" value={channels.length} />
      </div>

      {saleIntel && (
        <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
          <div className="space-y-4 rounded-[24px] border border-black/10 bg-white p-5 shadow-[0_12px_36px_rgba(0,0,0,0.04)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-gray-400">Sale Intel</p>
                <h2 className="mt-2 text-xl font-bold text-zinc-950">세일 패턴 요약</h2>
              </div>
              <button
                type="button"
                onClick={() => {
                  void addWatchlistItem({ watch_type: "brand", watch_value: brand.slug, notes: "brand sale alert" })
                    .then(() => setWatchMessage("관심 브랜드에 추가했습니다."))
                    .catch((err) => setWatchMessage(err instanceof Error ? err.message : "추가 실패"));
                }}
                className="rounded-full bg-zinc-950 px-4 py-2 text-xs font-semibold text-white"
              >
                세일 시작 알림 받기
              </button>
            </div>
            {watchMessage && <p className="text-xs text-zinc-500">{watchMessage}</p>}
            <div className="grid gap-3 md:grid-cols-3">
              <IntelMetric label="현재 세일 수" value={`${saleIntel.current_sale_products}`} />
              <IntelMetric
                label="최대 할인율"
                value={saleIntel.current_max_discount_rate != null ? `${saleIntel.current_max_discount_rate}%` : "—"}
              />
              <IntelMetric
                label="시즌성 피크"
                value={saleIntel.typical_sale_months.length ? saleIntel.typical_sale_months.map((row) => `${row}월`).join(", ") : "데이터 부족"}
              />
            </div>
            <div className="rounded-2xl bg-zinc-50 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-zinc-400">현재 세일 채널</p>
              <div className="mt-3 space-y-2">
                {saleIntel.sale_channels.length === 0 ? (
                  <p className="text-sm text-zinc-400">현재 세일 중인 채널이 없습니다.</p>
                ) : saleIntel.sale_channels.map((item) => (
                  <a
                    key={`${item.channel_name}-${item.url}`}
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white px-3 py-3 text-sm hover:bg-zinc-100"
                  >
                    <span className="font-medium text-zinc-900">{item.channel_name}</span>
                    <span className="text-zinc-500">{item.products_on_sale}개 세일</span>
                  </a>
                ))}
              </div>
            </div>
          </div>

          <div className="rounded-[24px] border border-black/10 bg-white p-5 shadow-[0_12px_36px_rgba(0,0,0,0.04)]">
            <div className="flex items-end justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-gray-400">Seasonality</p>
                <h2 className="mt-2 text-xl font-bold text-zinc-950">월별 세일 빈도</h2>
              </div>
              <p className="text-xs text-zinc-500">
                마지막 세일 시작 {saleIntel.last_sale_started_at ? saleIntel.last_sale_started_at.slice(0, 10) : "기록 없음"}
              </p>
            </div>
            <div className="mt-6 grid gap-3">
              {saleIntel.monthly_sale_history.length === 0 ? (
                <p className="text-sm text-zinc-400">세일 히스토리 데이터가 부족합니다.</p>
              ) : saleIntel.monthly_sale_history.map((item) => (
                <div key={item.month} className="grid grid-cols-[72px_1fr_96px] items-center gap-3">
                  <span className="text-sm font-medium text-zinc-700">{item.month}</span>
                  <div className="h-3 overflow-hidden rounded-full bg-zinc-100">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-zinc-950 to-lime-400"
                      style={{ width: `${Math.max((item.product_count / seasonalityMax) * 100, 8)}%` }}
                    />
                  </div>
                  <span className="text-right text-xs text-zinc-500">
                    {item.product_count}개 · {item.avg_discount != null ? `${item.avg_discount}%` : "—"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      <div className="flex items-center gap-2">
        <label className="inline-flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={saleOnly}
            onChange={(e) => setSaleOnly(e.target.checked)}
          />
          세일 제품만 보기
        </label>
      </div>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-3 rounded-xl border border-gray-200 bg-white p-4 lg:col-span-1">
          <h2 className="text-base font-semibold">크리에이티브 디렉터</h2>
          {directors.length === 0 ? (
            <p className="text-sm text-gray-400">등록된 디렉터 정보가 없습니다.</p>
          ) : (
            <div className="space-y-2">
              {directors.slice(0, 8).map((d) => (
                <div key={d.id} className="rounded-md border border-gray-100 p-2">
                  <p className="text-sm font-medium">{d.name}</p>
                  <p className="text-xs text-gray-500">{d.role}</p>
                  <p className="mt-1 text-xs text-gray-400">
                    {d.start_year ?? "?"} ~ {d.end_year ?? "현재"}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-3 rounded-xl border border-gray-200 bg-white p-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">협업 이력</h2>
            <Link href="/collabs" className="text-xs text-gray-500 hover:underline">
              전체 협업 보기
            </Link>
          </div>
          {collabs.length === 0 ? (
            <p className="text-sm text-gray-400">협업 데이터가 없습니다.</p>
          ) : (
            <div className="space-y-2">
              {collabs.slice(0, 8).map((c) => (
                <article key={c.id} className="rounded-md border border-gray-100 p-2">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium">{c.collab_name}</p>
                    <span className="rounded-full bg-red-100 px-2 py-0.5 text-[11px] text-red-700">
                      HYPE {c.hype_score}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-gray-500">
                    {c.release_year ?? "연도 미상"} · {c.collab_category ?? "카테고리 미분류"}
                  </p>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">브랜드 소식</h2>
          <Link href="/collabs" className="text-xs text-gray-500 hover:underline">
            협업 타임라인 보기
          </Link>
        </div>
        {news.length === 0 ? (
          <p className="text-sm text-gray-400">등록된 브랜드 소식이 없습니다.</p>
        ) : (
          <div className="space-y-2">
            {news.slice(0, 8).map((item) => (
              <a
                key={item.id}
                href={item.url}
                target="_blank"
                rel="noreferrer"
                className="block rounded-lg border border-gray-200 bg-white p-3 hover:bg-gray-50"
              >
                <p className="text-sm font-medium">{item.title}</p>
                <p className="mt-1 text-xs text-gray-500">
                  {item.source}
                  {item.published_at ? ` · ${item.published_at.slice(0, 10)}` : ""}
                </p>
              </a>
            ))}
          </div>
        )}
      </section>

      {products.length === 0 ? (
        <p className="text-sm text-gray-400">표시할 제품이 없습니다.</p>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {products.map((p) => (
            <ProductCard
              key={p.id}
              product={p}
              priceKrw={p.price_krw ?? undefined}
              originalPriceKrw={p.original_price_krw ?? undefined}
              discountRate={p.discount_rate ?? undefined}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900">{value.toLocaleString("ko-KR")}</p>
    </div>
  );
}

function IntelMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-zinc-400">{label}</p>
      <p className="mt-2 text-lg font-bold text-zinc-950">{value}</p>
    </div>
  );
}
