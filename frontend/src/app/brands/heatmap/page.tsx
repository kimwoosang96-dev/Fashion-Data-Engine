"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { getBrandsHeatmap } from "@/lib/api";
import type { BrandsHeatmapData } from "@/lib/types";

function cellTone(discountRate: number) {
  if (discountRate >= 60) return "bg-red-600 text-white";
  if (discountRate >= 45) return "bg-red-500 text-white";
  if (discountRate >= 30) return "bg-red-300 text-red-950";
  if (discountRate >= 15) return "bg-red-100 text-red-800";
  return "bg-white text-gray-300";
}

export default function BrandsHeatmapPage() {
  const [tier, setTier] = useState("");
  const [country, setCountry] = useState("");
  const [data, setData] = useState<BrandsHeatmapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [hoverKey, setHoverKey] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getBrandsHeatmap(tier || undefined, country || undefined)
      .then(setData)
      .finally(() => setLoading(false));
  }, [country, tier]);

  const countries = useMemo(() => {
    const set = new Set<string>();
    for (const channel of data?.channels ?? []) {
      if (channel.country) set.add(channel.country);
    }
    return Array.from(set).sort();
  }, [data]);

  const cellMap = useMemo(() => {
    const map = new Map<string, { discount_rate: number; product_count: number }>();
    for (const cell of data?.cells ?? []) {
      map.set(`${cell.brand_id}:${cell.channel_id}`, cell);
    }
    return map;
  }, [data]);

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">브랜드 세일 히트맵</h1>
          <p className="mt-1 text-sm text-gray-500">브랜드와 채널 조합별 평균 할인율과 세일 제품 수를 한 번에 봅니다.</p>
        </div>
        <Link href="/brands" className="text-sm font-medium text-blue-600 hover:underline">
          브랜드 리스트로 돌아가기
        </Link>
      </div>

      <div className="flex flex-wrap gap-3 rounded-2xl border border-gray-200 bg-white p-4">
        <select
          value={tier}
          onChange={(e) => setTier(e.target.value)}
          className="h-10 rounded-md border border-gray-200 bg-white px-3 text-sm"
        >
          <option value="">전체 티어</option>
          <option value="high-end">high-end</option>
          <option value="premium">premium</option>
          <option value="street">street</option>
          <option value="sports">sports</option>
          <option value="spa">spa</option>
        </select>
        <select
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          className="h-10 rounded-md border border-gray-200 bg-white px-3 text-sm"
        >
          <option value="">전체 국가</option>
          {countries.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <div className="ml-auto flex items-center gap-2 text-xs text-gray-500">
          <span className="rounded-full bg-white px-2 py-1 ring-1 ring-gray-200">0%</span>
          <span className="rounded-full bg-red-100 px-2 py-1">15%</span>
          <span className="rounded-full bg-red-300 px-2 py-1">30%</span>
          <span className="rounded-full bg-red-500 px-2 py-1 text-white">45%+</span>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-gray-400">히트맵 로딩 중...</p>
      ) : !data || data.brands.length === 0 || data.channels.length === 0 ? (
        <p className="text-sm text-gray-400">표시할 세일 데이터가 없습니다.</p>
      ) : (
        <div className="overflow-auto rounded-2xl border border-gray-200 bg-white">
          <div className="min-w-[960px]">
            <div
              className="grid"
              style={{ gridTemplateColumns: `220px repeat(${data.channels.length}, minmax(72px, 1fr))` }}
            >
              <div className="sticky left-0 z-10 border-b border-r border-gray-200 bg-white p-3 text-xs font-semibold text-gray-500">
                브랜드
              </div>
              {data.channels.map((channel) => (
                <div
                  key={channel.id}
                  className="border-b border-r border-gray-200 px-2 py-3 text-center text-[11px] font-semibold text-gray-500"
                >
                  <p className="line-clamp-2">{channel.name}</p>
                  <p className="mt-1 text-[10px] text-gray-400">{channel.country ?? "-"}</p>
                </div>
              ))}

              {data.brands.map((brand) => (
                <div key={brand.id} className="contents">
                  <div className="sticky left-0 z-10 border-b border-r border-gray-200 bg-white p-3">
                    <p className="text-sm font-medium text-gray-900">{brand.name}</p>
                    <p className="text-xs text-gray-400">{brand.tier ?? "-"}</p>
                  </div>
                  {data.channels.map((channel) => {
                    const cell = cellMap.get(`${brand.id}:${channel.id}`);
                    const key = `${brand.id}:${channel.id}`;
                    return (
                      <div
                        key={key}
                        onMouseEnter={() => setHoverKey(key)}
                        onMouseLeave={() => setHoverKey((prev) => (prev === key ? null : prev))}
                        className={`relative border-b border-r border-gray-200 px-2 py-3 text-center text-xs font-semibold ${cell ? cellTone(cell.discount_rate) : "bg-gray-50 text-gray-200"}`}
                      >
                        {cell ? `${Math.round(cell.discount_rate)}%` : "·"}
                        {cell && hoverKey === key && (
                          <div className="absolute left-1/2 top-full z-20 mt-2 w-48 -translate-x-1/2 rounded-xl border border-gray-200 bg-white p-3 text-left text-xs text-gray-700 shadow-lg">
                            <p className="font-semibold text-gray-900">{brand.name} × {channel.name}</p>
                            <p className="mt-1">세일 제품 {cell.product_count}개</p>
                            <p>평균 할인율 {cell.discount_rate.toFixed(1)}%</p>
                            <Link
                              href={`/brands/${encodeURIComponent(brand.slug)}`}
                              className="mt-2 inline-block font-medium text-blue-600 hover:underline"
                            >
                              보러가기
                            </Link>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
