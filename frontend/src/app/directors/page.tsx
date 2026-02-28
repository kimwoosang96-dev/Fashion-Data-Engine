"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getDirectorsByBrand } from "@/lib/api";
import type { BrandDirector, DirectorsByBrand } from "@/lib/types";
import { Input } from "@/components/ui/input";

export default function DirectorsPage() {
  const [items, setItems] = useState<DirectorsByBrand[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");

  useEffect(() => {
    getDirectorsByBrand()
      .then(setItems)
      .finally(() => setLoading(false));
  }, []);

  const includesQuery = (director: BrandDirector, q: string) =>
    `${director.name} ${director.role} ${director.brand_name ?? ""} ${director.brand_slug ?? ""}`
      .toLowerCase()
      .includes(q);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items
      .map((brand) => {
        const brandMatched = `${brand.brand_name} ${brand.brand_slug}`.toLowerCase().includes(q);
        if (brandMatched) return brand;
        const current_directors = brand.current_directors.filter((d) => includesQuery(d, q));
        const past_directors = brand.past_directors.filter((d) => includesQuery(d, q));
        return { ...brand, current_directors, past_directors };
      })
      .filter(
        (brand) =>
          brand.current_directors.length > 0 ||
          brand.past_directors.length > 0 ||
          `${brand.brand_name} ${brand.brand_slug}`.toLowerCase().includes(q)
      );
  }, [items, query]);

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold">크리에이티브 디렉터</h1>
        <p className="text-sm text-gray-500 mt-1">브랜드별 디렉터 이력</p>
      </div>
      <Input
        placeholder="디렉터/브랜드 검색"
        className="max-w-md bg-white"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {loading ? (
        <p className="text-sm text-gray-400">로딩 중...</p>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-gray-400">표시할 브랜드/디렉터가 없습니다.</p>
      ) : (
        <div className="space-y-4">
          {filtered.map((brand) => (
            <section key={brand.brand_slug} className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
              <Link
                href={`/brands/${encodeURIComponent(brand.brand_slug)}`}
                className="block text-base font-semibold hover:underline"
              >
                {brand.brand_name}
              </Link>

              {brand.current_directors.map((item) => (
                <article key={item.id} className="rounded-lg border border-green-200 bg-green-50/40 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-gray-900">{item.name}</p>
                      <p className="text-xs text-gray-600 mt-1">{item.role}</p>
                    </div>
                    <span className="text-xs px-2 py-1 rounded-full bg-green-100 text-green-700">현재</span>
                  </div>
                  <p className="text-xs text-gray-600 mt-2">
                    {item.start_year ?? "?"} ~ 현재
                  </p>
                  {item.note && <p className="text-xs text-gray-600 mt-1">{item.note}</p>}
                </article>
              ))}

              {brand.past_directors.map((item) => (
                <article key={item.id} className="rounded-lg border border-gray-200 bg-gray-50/30 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-gray-700">{item.name}</p>
                      <p className="text-xs text-gray-500 mt-1">{item.role}</p>
                    </div>
                    <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-600">
                      {item.start_year ?? "?"} ~ {item.end_year ?? "?"}
                    </span>
                  </div>
                  {item.note && <p className="text-xs text-gray-500 mt-2">{item.note}</p>}
                </article>
              ))}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
