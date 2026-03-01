"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getMultiChannelProducts } from "@/lib/api";
import type { MultiChannelProduct } from "@/lib/types";

const fmt = (n: number) => `₩${n.toLocaleString("ko-KR")}`;

type SortKey = "spread" | "channels" | "min_price";

const SORT_LABELS: Record<SortKey, string> = {
  spread: "가격 차이↓",
  channels: "채널 수↓",
  min_price: "최저가↑",
};

function SpreadBadge({ pct }: { pct: number }) {
  const cls =
    pct >= 15
      ? "bg-red-100 text-red-700"
      : pct >= 5
      ? "bg-amber-100 text-amber-800"
      : "bg-gray-100 text-gray-600";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {pct.toFixed(1)}%
    </span>
  );
}

export default function CompetePage() {
  const [allItems, setAllItems] = useState<MultiChannelProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState<SortKey>("spread");

  useEffect(() => {
    setLoading(true);
    getMultiChannelProducts(200, 0, 2, sort)
      .then(setAllItems)
      .finally(() => setLoading(false));
  }, [sort]);

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold">경쟁 제품</h1>
        <p className="text-sm text-gray-500 mt-1">
          동일 제품이 여러 채널에서 판매 중인 항목 — 가격 격차가 클수록 채널 간 가격경쟁이 심화된 상태
        </p>
      </div>

      {/* 정렬 컨트롤 */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500">정렬:</span>
        {(Object.keys(SORT_LABELS) as SortKey[]).map((key) => (
          <button
            key={key}
            onClick={() => setSort(key)}
            className={`px-3 py-1 text-xs rounded-full border transition-colors ${
              sort === key
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
            }`}
          >
            {SORT_LABELS[key]}
          </button>
        ))}
        {!loading && allItems.length > 0 && (
          <span className="ml-auto text-xs text-gray-400">{allItems.length}개 제품</span>
        )}
      </div>

      {loading ? (
        <p className="text-sm text-gray-400">로딩 중...</p>
      ) : allItems.length === 0 ? (
        <p className="text-sm text-gray-400">멀티채널 제품이 없습니다.</p>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3">제품</th>
                <th className="text-right px-4 py-3">채널</th>
                <th className="text-right px-4 py-3">최저가</th>
                <th className="text-right px-4 py-3">최고가</th>
                <th className="text-right px-4 py-3">가격 차이</th>
                <th className="text-right px-4 py-3">격차율</th>
                <th className="text-right px-4 py-3">비교</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {allItems.map((item) => (
                <tr key={item.product_key} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-12 h-12 rounded-md overflow-hidden bg-gray-100 shrink-0">
                        {item.image_url ? (
                          <img
                            src={item.image_url}
                            alt={item.product_name}
                            className="w-full h-full object-cover"
                          />
                        ) : null}
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium line-clamp-1">{item.product_name}</p>
                        <p className="text-xs text-gray-400 line-clamp-1">{item.product_key}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-gray-700">
                    {item.channel_count}
                  </td>
                  <td className="px-4 py-3 text-right text-green-700 font-medium">
                    {fmt(item.min_price_krw)}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-500">
                    {fmt(item.max_price_krw)}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-red-600">
                    {fmt(item.price_spread_krw)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <SpreadBadge pct={item.spread_rate_pct} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/compare/${encodeURIComponent(item.product_key)}`}
                      className="text-blue-600 hover:underline text-xs"
                    >
                      보기
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
