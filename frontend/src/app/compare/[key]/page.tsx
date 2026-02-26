"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getPriceComparison, getPriceHistory } from "@/lib/api";
import type { PriceComparison, PriceComparisonItem, ChannelPriceHistory } from "@/lib/types";
import Image from "next/image";

export default function ComparePage() {
  const { key } = useParams<{ key: string }>();
  const [data, setData] = useState<PriceComparison | null>(null);
  const [history, setHistory] = useState<ChannelPriceHistory[]>([]);
  const [days, setDays] = useState<7 | 30 | 0>(30);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const decoded = decodeURIComponent(key);
    Promise.all([
      getPriceComparison(decoded),
      getPriceHistory(decoded, days),
    ])
      .then(([comparison, historyRes]) => {
        setData(comparison);
        setHistory(historyRes);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [key, days]);

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

      {history.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">가격 추이</h2>
            <div className="flex gap-1">
              <button
                type="button"
                className={`px-2 py-1 text-xs rounded ${days === 7 ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-600"}`}
                onClick={() => setDays(7)}
              >
                7일
              </button>
              <button
                type="button"
                className={`px-2 py-1 text-xs rounded ${days === 30 ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-600"}`}
                onClick={() => setDays(30)}
              >
                30일
              </button>
              <button
                type="button"
                className={`px-2 py-1 text-xs rounded ${days === 0 ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-600"}`}
                onClick={() => setDays(0)}
              >
                전체
              </button>
            </div>
          </div>
          <PriceHistoryChart data={history} />
        </div>
      )}
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

function PriceHistoryChart({ data }: { data: ChannelPriceHistory[] }) {
  const chartWidth = 900;
  const chartHeight = 260;
  const pad = 30;
  const palette = ["#2563eb", "#10b981", "#ef4444", "#f59e0b", "#8b5cf6", "#06b6d4"];

  const points = data.flatMap((channel) => channel.history.map((h) => h.price_krw));
  if (points.length === 0) return null;

  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = Math.max(1, max - min);
  const maxLen = Math.max(...data.map((channel) => channel.history.length));

  return (
    <div className="space-y-3">
      <div className="w-full overflow-x-auto">
        <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="min-w-[640px] w-full h-64">
          <line x1={pad} y1={pad} x2={pad} y2={chartHeight - pad} stroke="#e5e7eb" />
          <line x1={pad} y1={chartHeight - pad} x2={chartWidth - pad} y2={chartHeight - pad} stroke="#e5e7eb" />
          <text x={4} y={pad + 4} fontSize={11} fill="#6b7280">
            ₩{max.toLocaleString("ko-KR")}
          </text>
          <text x={4} y={chartHeight - pad} fontSize={11} fill="#6b7280">
            ₩{min.toLocaleString("ko-KR")}
          </text>
          {data.map((channel, idx) => {
            const color = palette[idx % palette.length];
            const path = channel.history
              .map((point, i) => {
                const x = pad + (i / Math.max(1, maxLen - 1)) * (chartWidth - pad * 2);
                const y = chartHeight - pad - ((point.price_krw - min) / range) * (chartHeight - pad * 2);
                return `${i === 0 ? "M" : "L"} ${x} ${y}`;
              })
              .join(" ");
            return (
              <g key={channel.channel_name}>
                <path d={path} fill="none" stroke={color} strokeWidth={2} />
                {channel.history.map((point, i) => {
                  const x = pad + (i / Math.max(1, maxLen - 1)) * (chartWidth - pad * 2);
                  const y = chartHeight - pad - ((point.price_krw - min) / range) * (chartHeight - pad * 2);
                  return (
                    <circle
                      key={`${channel.channel_name}-${point.date}-${i}`}
                      cx={x}
                      cy={y}
                      r={2.5}
                      fill={point.is_sale ? "#ef4444" : color}
                    />
                  );
                })}
              </g>
            );
          })}
        </svg>
      </div>
      <div className="flex flex-wrap gap-3">
        {data.map((channel, idx) => (
          <div key={channel.channel_name} className="flex items-center gap-1.5 text-xs text-gray-600">
            <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ backgroundColor: palette[idx % palette.length] }} />
            {channel.channel_name}
          </div>
        ))}
      </div>
      <p className="text-xs text-gray-500">가격 범위: ₩{min.toLocaleString("ko-KR")} ~ ₩{max.toLocaleString("ko-KR")}</p>
    </div>
  );
}
