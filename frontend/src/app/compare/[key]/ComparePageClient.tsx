"use client";

import { useRouter } from "next/navigation";
import Image from "next/image";
import type { PriceComparison, PriceComparisonItem } from "@/lib/types";

function fmt(n: number) {
  return `₩${n.toLocaleString("ko-KR")}`;
}

export function ComparePageClient({
  initialData,
}: {
  initialData: PriceComparison;
}) {
  const router = useRouter();

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div>
        <button
          type="button"
          onClick={() => router.back()}
          className="text-xs text-gray-400 hover:text-gray-600"
        >
          ← 뒤로가기
        </button>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-400">Price Compare</p>
            <h1 className="mt-1 text-2xl font-bold text-gray-900">{initialData.product_name}</h1>
            <p className="mt-1 text-sm text-gray-500">
              {initialData.brand_name ? `${initialData.brand_name} · ` : ""}
              {initialData.total_listings}개 채널 실시간 비교
            </p>
            <p className="mt-1 font-mono text-xs text-gray-400">{initialData.product_key}</p>
          </div>
        </div>
      </div>

      <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-2xl border border-gray-200 bg-white p-5">
          <div className="flex gap-5">
            {initialData.image_url && (
              <div className="relative h-36 w-36 shrink-0 overflow-hidden rounded-xl bg-gray-100">
                <Image
                  src={initialData.image_url}
                  alt={initialData.product_name}
                  fill
                  className="object-cover"
                  sizes="144px"
                />
              </div>
            )}
            <div className="flex-1 space-y-4">
              <div>
                <p className="text-xs text-gray-400">최저가</p>
                <p className="text-3xl font-bold text-emerald-600">
                  {initialData.cheapest_price_krw != null ? fmt(initialData.cheapest_price_krw) : "—"}
                </p>
                {initialData.cheapest_channel && (
                  <p className="mt-1 text-sm text-gray-500">{initialData.cheapest_channel}</p>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <div className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                  판매 채널 {initialData.total_listings}곳
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-gray-200 bg-white p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-400">Live Table</p>
          <div className="mt-4 space-y-3">
            {[...initialData.listings]
              .sort((a, b) => a.price_krw - b.price_krw)
              .slice(0, 4)
              .map((listing, index) => (
                <div
                  key={`${listing.channel_name}-${listing.product_url}`}
                  className="flex items-center justify-between rounded-xl border border-gray-100 bg-gray-50 px-4 py-3"
                >
                  <div>
                    <p className="text-sm font-semibold text-gray-900">
                      {index === 0 ? "최저가 " : ""}
                      {listing.channel_name}
                    </p>
                    <p className="text-xs text-gray-500">{listing.channel_country ?? "국가 미상"}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-gray-900">{fmt(listing.price_krw)}</p>
                    {listing.discount_rate != null && (
                      <p className="text-xs text-red-500">-{listing.discount_rate}%</p>
                    )}
                  </div>
                </div>
              ))}
          </div>
        </div>
      </section>

      <section className="overflow-hidden rounded-2xl border border-gray-200 bg-white">
        <table className="w-full text-sm">
          <thead className="border-b border-gray-100 bg-gray-50 text-gray-500">
            <tr>
              <th className="px-4 py-3 text-left font-medium">채널</th>
              <th className="px-4 py-3 text-left font-medium">국가</th>
              <th className="px-4 py-3 text-right font-medium">가격</th>
              <th className="px-4 py-3 text-right font-medium">정가</th>
              <th className="px-4 py-3 text-center font-medium">상태</th>
              <th className="px-4 py-3 text-right font-medium">링크</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {[...initialData.listings].sort((a, b) => a.price_krw - b.price_krw).map((listing) => (
              <ListingRow
                key={`${listing.channel_name}-${listing.product_url}`}
                listing={listing}
                isCheapest={listing.price_krw === initialData.cheapest_price_krw}
              />
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function ListingRow({
  listing,
  isCheapest,
}: {
  listing: PriceComparisonItem;
  isCheapest: boolean;
}) {
  return (
    <tr className={isCheapest ? "bg-emerald-50/70" : "hover:bg-gray-50"}>
      <td className="px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-gray-900">{listing.channel_name}</span>
          {listing.is_official && (
            <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[11px] font-medium text-blue-700">
              공식
            </span>
          )}
          {isCheapest && (
            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
              최저가
            </span>
          )}
        </div>
        {listing.channel_type && <p className="mt-1 text-xs text-gray-400">{listing.channel_type}</p>}
      </td>
      <td className="px-4 py-3 text-xs text-gray-500">{listing.channel_country ?? "—"}</td>
      <td className="px-4 py-3 text-right font-semibold text-gray-900">{fmt(listing.price_krw)}</td>
      <td className="px-4 py-3 text-right text-gray-400">
        {listing.original_price_krw ? fmt(listing.original_price_krw) : "—"}
      </td>
      <td className="px-4 py-3 text-center">
        {listing.is_sale ? (
          <span className="rounded-full bg-red-100 px-2 py-1 text-xs font-medium text-red-600">
            {listing.discount_rate ? `-${listing.discount_rate}%` : "세일"}
          </span>
        ) : (
          <span className="text-gray-300">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-right">
        <a
          href={listing.product_url}
          target="_blank"
          rel="noreferrer"
          className="text-xs font-medium text-blue-600 hover:underline"
        >
          상품 보기
        </a>
      </td>
    </tr>
  );
}
