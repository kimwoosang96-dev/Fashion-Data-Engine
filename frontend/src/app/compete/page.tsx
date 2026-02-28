"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getMultiChannelProducts } from "@/lib/api";
import type { MultiChannelProduct } from "@/lib/types";

const fmt = (n: number) => `₩${n.toLocaleString("ko-KR")}`;

export default function CompetePage() {
  const [items, setItems] = useState<MultiChannelProduct[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMultiChannelProducts(200, 0, 2)
      .then(setItems)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold">경쟁 제품</h1>
        <p className="text-sm text-gray-500 mt-1">
          동일 제품이 여러 채널에서 판매되는 항목을 채널 수/가격 스프레드 기준으로 정렬
        </p>
      </div>

      {loading ? (
        <p className="text-sm text-gray-400">로딩 중...</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-gray-400">멀티채널 제품이 없습니다.</p>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3">제품</th>
                <th className="text-right px-4 py-3">채널 수</th>
                <th className="text-right px-4 py-3">최저가</th>
                <th className="text-right px-4 py-3">최고가</th>
                <th className="text-right px-4 py-3">가격 차이</th>
                <th className="text-right px-4 py-3">스프레드</th>
                <th className="text-right px-4 py-3">비교</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {items.map((item) => (
                <tr key={item.product_key}>
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
                  <td className="px-4 py-3 text-right font-semibold">{item.channel_count}</td>
                  <td className="px-4 py-3 text-right">{fmt(item.min_price_krw)}</td>
                  <td className="px-4 py-3 text-right">{fmt(item.max_price_krw)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-red-600">
                    {fmt(item.price_spread_krw)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="inline-flex items-center px-2 py-1 rounded-full bg-amber-100 text-amber-800 text-xs font-medium">
                      {item.spread_rate_pct}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/compare/${encodeURIComponent(item.product_key)}`}
                      className="text-blue-600 hover:underline"
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
