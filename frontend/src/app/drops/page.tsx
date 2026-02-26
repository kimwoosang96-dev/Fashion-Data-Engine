"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getDrops, getUpcomingDrops, searchProducts } from "@/lib/api";
import type { Drop, Product } from "@/lib/types";
import { Input } from "@/components/ui/input";
import Image from "next/image";

const STATUS_COLORS: Record<string, string> = {
  upcoming: "bg-blue-100 text-blue-700",
  released: "bg-green-100 text-green-700",
  sold_out: "bg-gray-100 text-gray-500",
};

const STATUS_LABELS: Record<string, string> = {
  upcoming: "예정",
  released: "발매",
  sold_out: "품절",
};

export default function DropsPage() {
  const [tab, setTab] = useState<"upcoming" | "all">("upcoming");
  const [drops, setDrops] = useState<Drop[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Product[]>([]);

  useEffect(() => {
    setLoading(true);
    const fetch = tab === "upcoming" ? getUpcomingDrops() : getDrops();
    fetch.then(setDrops).finally(() => setLoading(false));
  }, [tab]);

  const handleSearch = async (q: string) => {
    setSearchQuery(q);
    if (!q.trim()) { setSearchResults([]); return; }
    const results = await searchProducts(q);
    setSearchResults(results);
  };

  const fmt = (n: number) => n.toLocaleString("ko-KR") + "원";

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">드롭</h1>
        <p className="text-sm text-gray-500 mt-1">신제품 발매 및 예정 드롭</p>
      </div>

      {/* Search */}
      <div className="max-w-md relative">
        <Input
          placeholder="제품 검색 → 가격 비교..."
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          className="bg-white"
        />
        {searchResults.length > 0 && (
          <ul className="absolute z-10 top-full mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg divide-y divide-gray-100 overflow-hidden">
            {searchResults.slice(0, 6).map((p) => (
              <li key={p.id}>
                <Link
                  href={p.product_key ? `/compare/${encodeURIComponent(p.product_key)}` : p.url}
                  target={p.product_key ? undefined : "_blank"}
                  className="block px-4 py-2.5 hover:bg-gray-50 text-sm"
                  onClick={() => { setSearchQuery(""); setSearchResults([]); }}
                >
                  {p.name}
                  {p.product_key && <span className="text-xs text-gray-400 ml-2">→ 가격비교</span>}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {(["upcoming", "all"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              tab === t ? "bg-white shadow-sm text-gray-900" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "upcoming" ? "예정" : "전체"}
          </button>
        ))}
      </div>

      {/* Drops grid */}
      {loading ? (
        <p className="text-sm text-gray-400">로딩 중...</p>
      ) : drops.length === 0 ? (
        <p className="text-sm text-gray-400">드롭 데이터가 없습니다.</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {drops.map((drop) => (
            <DropCard key={drop.id} drop={drop} fmt={fmt} />
          ))}
        </div>
      )}
    </div>
  );
}

function DropCard({ drop, fmt }: { drop: Drop; fmt: (n: number) => string }) {
  const content = (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
      {drop.image_url ? (
        <div className="relative aspect-square bg-gray-100">
          <Image src={drop.image_url} alt={drop.product_name} fill className="object-cover" sizes="200px" />
        </div>
      ) : (
        <div className="aspect-square bg-gray-100 flex items-center justify-center text-3xl">🚀</div>
      )}
      <div className="p-3 space-y-1">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[drop.status] ?? "bg-gray-100 text-gray-500"}`}>
          {STATUS_LABELS[drop.status] ?? drop.status}
        </span>
        <p className="text-sm font-medium leading-tight line-clamp-2">{drop.product_name}</p>
        {drop.price_krw !== null && (
          <p className="text-sm font-bold text-gray-900">{fmt(drop.price_krw)}</p>
        )}
        {drop.release_date && (
          <p className="text-xs text-gray-400">{drop.release_date.slice(0, 10)}</p>
        )}
      </div>
    </div>
  );

  if (drop.product_key) {
    return (
      <Link href={`/compare/${encodeURIComponent(drop.product_key)}`}>{content}</Link>
    );
  }
  return (
    <a href={drop.source_url} target="_blank" rel="noopener noreferrer">{content}</a>
  );
}
