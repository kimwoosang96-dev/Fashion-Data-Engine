"use client";

import { useEffect, useMemo, useState } from "react";
import { getChannelHighlights } from "@/lib/api";
import type { ChannelHighlight } from "@/lib/types";
import { Input } from "@/components/ui/input";

export default function ChannelsPage() {
  const [items, setItems] = useState<ChannelHighlight[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [saleOnly, setSaleOnly] = useState(false);

  useEffect(() => {
    getChannelHighlights(250)
      .then(setItems)
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((channel) => {
      const matchQuery = !q ||
        channel.channel_name.toLowerCase().includes(q) ||
        channel.channel_url.toLowerCase().includes(q);
      const matchSale = !saleOnly || channel.is_running_sales;
      return matchQuery && matchSale;
    });
  }, [items, query, saleOnly]);

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold">판매채널</h1>
        <p className="text-sm text-gray-500 mt-1">세일 진행 여부 / 신상품 판매 여부 강조</p>
      </div>
      <div className="space-y-2">
        <Input
          placeholder="채널 검색..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="max-w-md bg-white"
        />
        <label className="inline-flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={saleOnly}
            onChange={(e) => setSaleOnly(e.target.checked)}
          />
          세일 진행 중만 보기
        </label>
      </div>
      {!loading && <p className="text-sm text-gray-500">{filtered.length}개 채널</p>}

      {loading ? (
        <p className="text-sm text-gray-400">로딩 중...</p>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3">채널</th>
                <th className="text-left px-4 py-3">국가</th>
                <th className="text-left px-4 py-3">포인트</th>
                <th className="text-right px-4 py-3">세일 제품</th>
                <th className="text-right px-4 py-3">신상품</th>
                <th className="text-right px-4 py-3">총 제품</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map((ch) => (
                <tr key={ch.channel_id}>
                  <td className="px-4 py-3">
                    <a href={ch.channel_url} target="_blank" rel="noreferrer" className="font-medium hover:underline">
                      {ch.channel_name}
                    </a>
                    <p className="text-xs text-gray-400">{ch.channel_type ?? "-"}</p>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{ch.country ?? "-"}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1.5">
                      {ch.is_running_sales ? (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-medium">세일 진행</span>
                      ) : (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">세일 없음</span>
                      )}
                      {ch.is_selling_new_products ? (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-medium">신상품 판매</span>
                      ) : (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">신상품 없음</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-semibold">{ch.sale_product_count}</td>
                  <td className="px-4 py-3 text-right font-semibold">{ch.new_product_count}</td>
                  <td className="px-4 py-3 text-right text-gray-600">{ch.total_product_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
