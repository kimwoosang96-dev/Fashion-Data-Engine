"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { getBrandHighlights } from "@/lib/api";
import type { BrandHighlight } from "@/lib/types";
import { Input } from "@/components/ui/input";

export default function BrandsPage() {
  const router = useRouter();
  const [items, setItems] = useState<BrandHighlight[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [tierFilter, setTierFilter] = useState("all");

  useEffect(() => {
    getBrandHighlights(400)
      .then(setItems)
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((brand) => {
      const matchQuery = !q ||
        brand.brand_name.toLowerCase().includes(q) ||
        brand.brand_slug.toLowerCase().includes(q);
      const matchTier = tierFilter === "all" || brand.tier === tierFilter;
      return matchQuery && matchTier;
    });
  }, [items, query, tierFilter]);

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold">브랜드</h1>
        <p className="text-sm text-gray-500 mt-1">신상품 판매 여부 강조</p>
      </div>
      <div className="flex flex-col md:flex-row gap-3">
        <Input
          placeholder="브랜드 검색..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="max-w-md bg-white"
        />
        <select
          value={tierFilter}
          onChange={(e) => setTierFilter(e.target.value)}
          className="h-10 rounded-md border border-gray-200 bg-white px-3 text-sm"
        >
          <option value="all">전체</option>
          <option value="high-end">high-end</option>
          <option value="premium">premium</option>
          <option value="street">street</option>
          <option value="sports">sports</option>
        </select>
      </div>
      {!loading && (
        <p className="text-sm text-gray-500">{filtered.length}개 브랜드</p>
      )}

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
              {filtered.map((brand) => (
                <tr
                  key={brand.brand_id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => router.push(`/brands/${encodeURIComponent(brand.brand_slug)}`)}
                >
                  <td className="px-4 py-3">
                    <p className="font-medium">
                      <Link href={`/brands/${encodeURIComponent(brand.brand_slug)}`} className="hover:underline">
                        {brand.brand_name}
                      </Link>
                    </p>
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
