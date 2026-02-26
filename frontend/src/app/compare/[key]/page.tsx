"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getPriceComparison } from "@/lib/api";
import type { PriceComparison, PriceComparisonItem } from "@/lib/types";
import Image from "next/image";

export default function ComparePage() {
  const { key } = useParams<{ key: string }>();
  const [data, setData] = useState<PriceComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPriceComparison(decodeURIComponent(key))
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [key]);

  const fmt = (n: number) => n.toLocaleString("ko-KR") + "원";

  if (loading) return <div className="p-6 text-sm text-gray-400">로딩 중...</div>;
  if (error || !data) return <div className="p-6 text-sm text-red-500">{error ?? "데이터를 불러올 수 없습니다"}</div>;

  const cheapestPrice = data.cheapest_price_krw;
  const heroImage = data.listings.find((l) => l.image_url)?.image_url;

  return (
    <div className="p-6 max-w-3xl space-y-6">
      <div>
        <Link href="/" className="text-xs text-gray-400 hover:text-gray-600">← 대시보드</Link>
        <h1 className="text-xl font-bold mt-1">{data.product_name}</h1>
        <p className="text-xs text-gray-400 font-mono mt-0.5">{data.product_key}</p>
      </div>

      {/* Hero + summary */}
      <div className="flex gap-6 bg-white rounded-xl border border-gray-200 p-5">
        {heroImage && (
          <div className="relative w-32 h-32 rounded-lg overflow-hidden shrink-0 bg-gray-100">
            <Image src={heroImage} alt={data.product_name} fill className="object-cover" sizes="128px" />
          </div>
        )}
        <div className="space-y-2">
          <div>
            <p className="text-xs text-gray-400">최저가</p>
            <p className="text-2xl font-bold text-emerald-600">
              {cheapestPrice !== null ? fmt(cheapestPrice) : "—"}
            </p>
            {data.cheapest_channel && (
              <p className="text-xs text-gray-500">{data.cheapest_channel}</p>
            )}
          </div>
          <p className="text-xs text-gray-400">{data.total_listings}개 채널에서 판매 중</p>
        </div>
      </div>

      {/* Channel table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-gray-100 bg-gray-50">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-500">채널</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">국가</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">가격 (KRW)</th>
              <th className="text-right px-4 py-3 font-medium text-gray-500">원가</th>
              <th className="text-center px-4 py-3 font-medium text-gray-500">세일</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {[...data.listings].sort((a, b) => a.price_krw - b.price_krw).map((listing, i) => (
              <ListingRow
                key={i}
                listing={listing}
                isCheapest={listing.price_krw === cheapestPrice}
                fmt={fmt}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ListingRow({
  listing, isCheapest, fmt,
}: {
  listing: PriceComparisonItem;
  isCheapest: boolean;
  fmt: (n: number) => string;
}) {
  return (
    <tr className={`hover:bg-gray-50 transition-colors ${isCheapest ? "bg-emerald-50" : ""}`}>
      <td className="px-4 py-3">
        <span className="font-medium">{listing.channel_name}</span>
        {isCheapest && (
          <span className="ml-2 text-xs text-emerald-600 font-semibold">최저가</span>
        )}
      </td>
      <td className="px-4 py-3 text-gray-500 text-xs">{listing.channel_country ?? "—"}</td>
      <td className="px-4 py-3 text-right font-semibold">
        <span className={isCheapest ? "text-emerald-600" : "text-gray-900"}>
          {fmt(listing.price_krw)}
        </span>
      </td>
      <td className="px-4 py-3 text-right text-gray-400">
        {listing.original_price_krw ? fmt(listing.original_price_krw) : "—"}
      </td>
      <td className="px-4 py-3 text-center">
        {listing.is_sale ? (
          <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full font-medium">
            {listing.discount_rate ? `-${listing.discount_rate}%` : "세일"}
          </span>
        ) : (
          <span className="text-gray-200">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-right">
        <a
          href={listing.product_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-blue-500 hover:underline"
        >
          보기 →
        </a>
      </td>
    </tr>
  );
}
