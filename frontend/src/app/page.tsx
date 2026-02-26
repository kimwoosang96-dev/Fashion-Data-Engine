"use client";
import { useEffect, useState, useCallback } from "react";
import { getSaleProducts, getChannels, getBrands, searchProducts, getRelatedSearches } from "@/lib/api";
import type { Product, Channel, Brand } from "@/lib/types";
import { ProductCard } from "@/components/ProductCard";
import { Input } from "@/components/ui/input";
import Link from "next/link";

export default function DashboardPage() {
  const [saleProducts, setSaleProducts] = useState<Product[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [searchResults, setSearchResults] = useState<Product[] | null>(null);
  const [relatedSearches, setRelatedSearches] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getSaleProducts(60), getChannels(), getBrands()])
      .then(([products, ch, br]) => {
        setSaleProducts(products);
        setChannels(ch);
        setBrands(br);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSearch = useCallback(async (q: string) => {
    setQuery(q);
    if (!q.trim()) {
      setSearchResults(null);
      setRelatedSearches([]);
      return;
    }
    const [results, related] = await Promise.all([
      searchProducts(q),
      getRelatedSearches(q, 8),
    ]);
    setSearchResults(results);
    setRelatedSearches(related);
  }, []);

  const displayed = searchResults ?? saleProducts;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">대시보드</h1>
        <p className="text-sm text-gray-500 mt-1">세일 중인 제품과 채널 현황</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard
          label="세일 제품"
          value={loading ? "—" : `${saleProducts.length}개`}
          icon="🔥"
          href="/sales"
        />
        <StatCard
          label="판매채널"
          value={loading ? "—" : `${channels.length}개`}
          icon="🏪"
          href="/channels"
        />
        <StatCard
          label="브랜드"
          value={loading ? "—" : `${brands.length}개`}
          icon="🏷️"
          href="/brands"
        />
      </div>

      {/* Search */}
      <div className="max-w-md">
        <Input
          placeholder="제품 검색..."
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          className="bg-white"
        />
        {query.trim() && relatedSearches.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {relatedSearches.map((term) => (
              <button
                key={term}
                type="button"
                onClick={() => handleSearch(term)}
                className="text-xs rounded-full border border-gray-200 bg-white px-2.5 py-1 text-gray-600 hover:border-gray-300 hover:text-gray-900"
              >
                {term}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Products grid */}
      {loading ? (
        <div className="text-sm text-gray-400">로딩 중...</div>
      ) : displayed.length === 0 ? (
        <div className="text-sm text-gray-400">
          {query ? "검색 결과 없음" : "세일 제품 없음"}
        </div>
      ) : (
        <div>
          <p className="text-xs text-gray-400 mb-3">
            {searchResults ? `검색 결과 ${searchResults.length}개` : `세일 ${saleProducts.length}개`}
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {displayed.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  href,
}: {
  label: string;
  value: string;
  icon: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3 hover:border-gray-400 hover:shadow-sm transition-all"
    >
      <span className="text-2xl">{icon}</span>
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-xl font-bold text-gray-900">{value}</p>
      </div>
    </Link>
  );
}
