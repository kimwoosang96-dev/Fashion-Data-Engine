"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getDirectors } from "@/lib/api";
import type { BrandDirector } from "@/lib/types";
import { Input } from "@/components/ui/input";

export default function DirectorsPage() {
  const [items, setItems] = useState<BrandDirector[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");

  useEffect(() => {
    getDirectors(400, 0)
      .then(setItems)
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((d) =>
      `${d.name} ${d.brand_name ?? ""} ${d.brand_slug ?? ""} ${d.role}`.toLowerCase().includes(q)
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
        <p className="text-sm text-gray-400">표시할 디렉터가 없습니다.</p>
      ) : (
        <div className="space-y-2">
          {filtered.map((item) => (
            <article key={item.id} className="bg-white border border-gray-200 rounded-xl p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold">{item.name}</p>
                  <p className="text-xs text-gray-500 mt-1">{item.role}</p>
                </div>
                <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-700">
                  {item.start_year ?? "?"} ~ {item.end_year ?? "현재"}
                </span>
              </div>
              <p className="text-sm text-gray-700 mt-2">
                브랜드:{" "}
                {item.brand_slug ? (
                  <Link href={`/brands/${encodeURIComponent(item.brand_slug)}`} className="underline">
                    {item.brand_name ?? item.brand_slug}
                  </Link>
                ) : (
                  item.brand_name ?? "-"
                )}
              </p>
              {item.note && <p className="text-sm text-gray-600 mt-1">{item.note}</p>}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
