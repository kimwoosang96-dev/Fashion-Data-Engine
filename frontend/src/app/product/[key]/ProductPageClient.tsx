"use client";

import Image from "next/image";
import Link from "next/link";
import type { CrossChannelPriceHistory, Product, ProductAvailability } from "@/lib/types";
import { ProductCard } from "@/components/ProductCard";

function formatKrw(value: number | null) {
  return value == null ? "—" : `₩${value.toLocaleString("ko-KR")}`;
}

function formatFreshness(hours?: number | null) {
  if (hours == null) return "업데이트 기록 없음";
  if (hours < 24) return `${Math.max(1, Math.round(hours))}시간 전 업데이트`;
  return `${Math.round(hours / 24)}일 전 업데이트`;
}

function buildChartPoints(history: CrossChannelPriceHistory["history"]) {
  if (!history.length) return [];
  const grouped = new Map<string, number>();
  history.forEach((item) => {
    const existing = grouped.get(item.date);
    if (existing == null || item.price_krw < existing) {
      grouped.set(item.date, item.price_krw);
    }
  });
  const entries = [...grouped.entries()];
  const prices = entries.map(([, price]) => price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const width = 680;
  const height = 180;
  return entries.map(([date, price], index) => {
    const x = entries.length === 1 ? width / 2 : (index / (entries.length - 1)) * width;
    const y = max === min ? height / 2 : height - ((price - min) / (max - min)) * height;
    return { date, price, x, y };
  });
}

export function ProductPageClient({
  availability,
  priceHistory,
  relatedProducts,
}: {
  availability: ProductAvailability;
  priceHistory: CrossChannelPriceHistory | null;
  relatedProducts: Product[];
}) {
  const points = buildChartPoints(priceHistory?.history ?? []);
  const polyline = points.map((point) => `${point.x},${point.y}`).join(" ");

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-6 py-8 md:px-10">
      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-[28px] border border-black/10 bg-white p-5 shadow-[0_16px_48px_rgba(0,0,0,0.06)]">
          <div className="relative aspect-square overflow-hidden rounded-[22px] bg-zinc-100">
            {availability.image_url ? (
              <Image
                src={availability.image_url}
                alt={availability.product_name}
                fill
                className="object-cover"
                sizes="(max-width: 1024px) 100vw, 520px"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-6xl text-zinc-300">◎</div>
            )}
          </div>
        </section>

        <section className="space-y-5">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-zinc-400">Product Detail</p>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-zinc-950 md:text-5xl">
              {availability.product_name}
            </h1>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-zinc-500">
              {availability.brand_name && (
                <Link
                  href={availability.brand_slug ? `/brands/${availability.brand_slug}` : "#"}
                  className="rounded-full bg-zinc-100 px-3 py-1.5 font-medium text-zinc-700"
                >
                  {availability.brand_name}
                </Link>
              )}
              <span className="rounded-full bg-emerald-100 px-3 py-1.5 font-medium text-emerald-700">
                {availability.in_stock_anywhere ? "재고 있음" : "재고 없음"}
              </span>
              {priceHistory?.price_trend && (
                <span className="rounded-full bg-amber-100 px-3 py-1.5 font-medium text-amber-700">
                  가격 추이 {priceHistory.price_trend}
                </span>
              )}
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <MetricCard
              label="현재 최저가"
              value={formatKrw(availability.lowest_price?.price_krw ?? null)}
              sub={availability.lowest_price?.channel_name ?? "채널 미상"}
            />
            <MetricCard
              label="판매 채널"
              value={`${availability.channels.length}`}
              sub="실시간 가격 비교"
            />
            <MetricCard
              label="역대 최저"
              value={formatKrw(priceHistory?.all_time_low?.price_krw ?? null)}
              sub={priceHistory?.all_time_low ? `${priceHistory.all_time_low.channel_name} · ${priceHistory.all_time_low.date}` : "기록 없음"}
            />
          </div>

          <div className="flex flex-wrap gap-3">
            <Link href="/feed" className="rounded-full bg-zinc-950 px-5 py-2.5 text-sm font-semibold text-white">
              알림 설정
            </Link>
            {availability.lowest_price?.product_url && (
              <a
                href={availability.lowest_price.product_url}
                target="_blank"
                rel="noreferrer"
                className="rounded-full border border-zinc-300 px-5 py-2.5 text-sm font-semibold text-zinc-700"
              >
                최저가 채널 바로가기
              </a>
            )}
          </div>
        </section>
      </div>

      <section className="overflow-hidden rounded-[28px] border border-black/10 bg-white shadow-[0_16px_48px_rgba(0,0,0,0.05)]">
        <div className="border-b border-zinc-100 px-5 py-4">
          <h2 className="text-lg font-semibold text-zinc-950">채널별 가격 및 재고</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-zinc-50 text-zinc-500">
              <tr>
                <th className="px-4 py-3 text-left font-medium">채널</th>
                <th className="px-4 py-3 text-left font-medium">가격</th>
                <th className="px-4 py-3 text-left font-medium">할인</th>
                <th className="px-4 py-3 text-left font-medium">재고</th>
                <th className="px-4 py-3 text-left font-medium">사이즈</th>
                <th className="px-4 py-3 text-right font-medium">구매</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {availability.channels.map((item) => (
                <tr key={`${item.channel_name}-${item.product_url}`} className="align-top hover:bg-zinc-50/70">
                  <td className="px-4 py-4">
                    <div className="font-semibold text-zinc-950">{item.channel_name}</div>
                    <div className="text-xs text-zinc-400">{item.channel_country ?? "국가 미상"}</div>
                    <div className="text-xs text-zinc-400">{formatFreshness(item.data_freshness_hours)}</div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="font-semibold text-zinc-950">{formatKrw(item.price_krw)}</div>
                    {item.original_price_krw != null && (
                      <div className="text-xs text-zinc-400 line-through">{formatKrw(item.original_price_krw)}</div>
                    )}
                  </td>
                  <td className="px-4 py-4">
                    {item.discount_rate != null ? (
                      <span className="rounded-full bg-red-100 px-2 py-1 text-xs font-semibold text-red-700">
                        -{item.discount_rate}%
                      </span>
                    ) : (
                      <span className="text-zinc-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-4">
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-semibold ${
                        item.stock_status === "sold_out"
                          ? "bg-zinc-200 text-zinc-600"
                          : item.stock_status === "low_stock"
                            ? "bg-amber-100 text-amber-700"
                            : "bg-emerald-100 text-emerald-700"
                      }`}
                    >
                      {item.stock_status === "sold_out"
                        ? "품절"
                        : item.stock_status === "low_stock"
                          ? "재고 적음"
                          : "재고 있음"}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex max-w-xs flex-wrap gap-1">
                      {item.size_availability?.length ? item.size_availability.map((size) => (
                        <span
                          key={`${item.channel_name}-${String(size.size)}`}
                          className={`rounded-full px-2 py-1 text-[11px] ${
                            size.in_stock ? "bg-zinc-100 text-zinc-700" : "bg-zinc-50 text-zinc-300 line-through"
                          }`}
                        >
                          {String(size.size)}
                        </span>
                      )) : <span className="text-zinc-300">사이즈 정보 없음</span>}
                    </div>
                  </td>
                  <td className="px-4 py-4 text-right">
                    <a
                      href={item.product_url}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded-full border border-zinc-300 px-3 py-1.5 text-xs font-semibold text-zinc-700"
                    >
                      바로 구매
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[28px] border border-black/10 bg-white p-5 shadow-[0_16px_48px_rgba(0,0,0,0.05)]">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-zinc-950">교차채널 가격 추이</h2>
            {priceHistory?.all_time_low && (
              <p className="text-sm text-zinc-500">
                역대 최저 {formatKrw(priceHistory.all_time_low.price_krw)} · {priceHistory.all_time_low.channel_name}
              </p>
            )}
          </div>
          {points.length >= 2 ? (
            <div className="mt-6">
              <svg viewBox="0 0 680 220" className="w-full">
                <polyline
                  fill="none"
                  stroke="#18181b"
                  strokeWidth="3"
                  points={polyline}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
                {points.map((point) => (
                  <g key={`${point.date}-${point.price}`}>
                    <circle cx={point.x} cy={point.y} r="4" fill="#84cc16" />
                  </g>
                ))}
              </svg>
              <div className="mt-3 flex justify-between text-xs text-zinc-400">
                <span>{points[0]?.date}</span>
                <span>{points[points.length - 1]?.date}</span>
              </div>
            </div>
          ) : (
            <p className="mt-4 text-sm text-zinc-400">표시할 가격 히스토리가 충분하지 않습니다.</p>
          )}
        </div>

        <div className="rounded-[28px] border border-black/10 bg-white p-5 shadow-[0_16px_48px_rgba(0,0,0,0.05)]">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-zinc-950">같은 브랜드 추천</h2>
            {availability.brand_slug && (
              <Link href={`/brands/${availability.brand_slug}`} className="text-sm text-zinc-500 hover:text-zinc-900">
                브랜드 보기
              </Link>
            )}
          </div>
          {relatedProducts.length === 0 ? (
            <p className="mt-4 text-sm text-zinc-400">연관 제품이 없습니다.</p>
          ) : (
            <div className="mt-4 grid grid-cols-2 gap-3">
              {relatedProducts.slice(0, 4).map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  priceKrw={product.price_krw ?? undefined}
                  originalPriceKrw={product.original_price_krw ?? undefined}
                  discountRate={product.discount_rate ?? undefined}
                />
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function MetricCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="rounded-[22px] border border-black/10 bg-white p-4 shadow-[0_12px_36px_rgba(0,0,0,0.04)]">
      <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">{label}</p>
      <p className="mt-3 text-2xl font-bold tracking-tight text-zinc-950">{value}</p>
      <p className="mt-2 text-sm text-zinc-500">{sub}</p>
    </div>
  );
}
