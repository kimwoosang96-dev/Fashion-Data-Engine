"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getSaleHighlights } from "@/lib/api";
import type { SaleHighlight } from "@/lib/types";

const fmt = (n: number) => `₩${n.toLocaleString("ko-KR")}`;

export default function SalesPage() {
  const [items, setItems] = useState<SaleHighlight[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSaleHighlights(150)
      .then(setItems)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold">세일 제품</h1>
        <p className="text-sm text-gray-500 mt-1">세일율이 높은 순으로 정렬</p>
      </div>

      {loading ? (
        <p className="text-sm text-gray-400">로딩 중...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {items.map((item) => (
            <article key={item.product_id} className="bg-white border border-gray-200 rounded-xl p-4">
              <div className="flex gap-3">
                <div className="w-20 h-20 rounded-md overflow-hidden bg-gray-100 shrink-0">
                  {item.image_url ? (
                    <img src={item.image_url} alt={item.product_name} className="w-full h-full object-cover" />
                  ) : null}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold line-clamp-2">{item.product_name}</p>
                  <p className="text-xs text-gray-500 mt-1">{item.channel_name}</p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-medium">
                      {item.discount_rate ? `-${item.discount_rate}%` : "세일"}
                    </span>
                    {!item.is_active && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 font-medium">
                        품절
                      </span>
                    )}
                    {item.is_new && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-medium">
                        NEW
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="mt-3 flex items-end gap-2">
                <p className="text-lg font-bold">{fmt(item.price_krw)}</p>
                {item.original_price_krw && (
                  <p className="text-xs text-gray-400 line-through">{fmt(item.original_price_krw)}</p>
                )}
              </div>
              <div className="mt-3 flex gap-3 text-xs">
                {item.product_key ? (
                  <Link className="text-blue-600 hover:underline" href={`/compare/${encodeURIComponent(item.product_key)}`}>
                    가격 비교 보기
                  </Link>
                ) : null}
                <a className="text-gray-600 hover:underline" href={item.product_url} target="_blank" rel="noreferrer">
                  원본 상품
                </a>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
