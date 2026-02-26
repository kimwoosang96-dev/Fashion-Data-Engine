"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getBrandHighlights } from "@/lib/api";
import type { BrandHighlight } from "@/lib/types";

export default function BrandsPage() {
  const [items, setItems] = useState<BrandHighlight[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBrandHighlights(400)
      .then(setItems)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold">브랜드</h1>
        <p className="text-sm text-gray-500 mt-1">신상품 판매 여부 강조</p>
      </div>

      {loading ? (
        <p className="text-sm text-gray-400">로딩 중...</p>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3">브랜드</th>
                <th className="text-left px-4 py-3">티어</th>
                <th className="text-left px-4 py-3">포인트</th>
                <th className="text-right px-4 py-3">신상품</th>
                <th className="text-right px-4 py-3">총 제품</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {items.map((brand) => (
                <tr key={brand.brand_id}>
                  <td className="px-4 py-3">
                    <p className="font-medium">{brand.brand_name}</p>
                    <p className="text-xs text-gray-400">{brand.brand_slug}</p>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{brand.tier ?? "-"}</td>
                  <td className="px-4 py-3">
                    {brand.is_selling_new_products ? (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-medium">신상품 판매</span>
                    ) : (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">신상품 없음</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold">{brand.new_product_count}</td>
                  <td className="px-4 py-3 text-right text-gray-600">{brand.total_product_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="text-xs text-gray-500">
        가격 비교는 제품 단위에서 제공합니다. <Link href="/sales" className="underline">세일 제품</Link>에서 상품을 선택해 확인할 수 있습니다.
      </div>
    </div>
  );
}
