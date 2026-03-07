"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  getSaleHighlights,
  getChannels,
  getBrands,
  getProductRanking,
  searchProducts,
  getSearchSuggestions,
  getRelatedSearches,
} from "@/lib/api";
import type { Product, Channel, Brand, SaleHighlight, ProductRankingItem, SearchSuggestion } from "@/lib/types";
import { ProductCard } from "@/components/ProductCard";
import { Input } from "@/components/ui/input";
import Link from "next/link";
import { SearchDropdown } from "@/components/SearchDropdown";

function formatSaleStart(hours: number | null) {
  if (hours == null) return null;
  if (hours < 1) return "1시간 이내 세일 시작";
  if (hours < 24) return `${Math.floor(hours)}시간 전 세일 시작`;
  return `${Math.floor(hours / 24)}일 전 세일 시작`;
}

export default function DashboardPage() {
  const router = useRouter();
  const [saleProducts, setSaleProducts] = useState<SaleHighlight[]>([]);
  const [baseSaleProducts, setBaseSaleProducts] = useState<SaleHighlight[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [hotRanking, setHotRanking] = useState<ProductRankingItem[]>([]);
  const [searchResults, setSearchResults] = useState<Product[] | null>(null);
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [relatedSearches, setRelatedSearches] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const searchBoxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    Promise.all([getSaleHighlights(60, 0), getChannels(), getBrands(), getProductRanking("sale_hot", 10)])
      .then(([products, ch, br, ranking]) => {
        setSaleProducts(products);
        setBaseSaleProducts(products);
        setChannels(ch);
        setBrands(br);
        setHotRanking(ranking);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const onClickOutside = (event: MouseEvent) => {
      if (!searchBoxRef.current?.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const executeSearch = useCallback(async (term: string) => {
    const filtered = await searchProducts(term);
    setSearchResults(filtered);
    setSuggestions([]);
    setRelatedSearches([]);
    setQuery(term);
    setDropdownOpen(false);
  }, []);

  const handleSearchChange = useCallback((q: string) => {
    setQuery(q);
    if (!q.trim()) {
      setSearchResults(null);
      setSuggestions([]);
      setRelatedSearches([]);
      setSaleProducts(baseSaleProducts);
      setDropdownOpen(false);
      setActiveSuggestionIndex(0);
      return;
    }
    setDropdownOpen(true);
  }, [baseSaleProducts]);

  useEffect(() => {
    const trimmed = query.trim();
    if (!trimmed) return;
    const timer = window.setTimeout(() => {
      void Promise.all([
        getSearchSuggestions(trimmed, 8),
        getRelatedSearches(trimmed, 8),
      ]).then(([nextSuggestions, related]) => {
        setSuggestions(nextSuggestions);
        setRelatedSearches(related);
        setActiveSuggestionIndex(0);
        setDropdownOpen(nextSuggestions.length > 0);
      }).catch(() => {
        setSuggestions([]);
      });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [query]);

  const handleSuggestionSelect = useCallback((item: SearchSuggestion) => {
    if (item.type === "brand" && item.slug) {
      setDropdownOpen(false);
      router.push(`/brands/${encodeURIComponent(item.slug)}`);
      return;
    }
    void executeSearch(item.label);
  }, [executeSearch, router]);

  const handleSearchSubmit = useCallback(() => {
    if (!query.trim()) return;
    const activeItem = suggestions[activeSuggestionIndex];
    if (dropdownOpen && activeItem) {
      handleSuggestionSelect(activeItem);
      return;
    }
    void executeSearch(query.trim());
  }, [activeSuggestionIndex, dropdownOpen, executeSearch, handleSuggestionSelect, query, suggestions]);

  const handleProductClick = useCallback((product: Product) => {
    setSearchResults([product]);
    setSuggestions([]);
    setDropdownOpen(false);
    setQuery(product.name);
  }, []);

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
      <div className="max-w-md relative" ref={searchBoxRef}>
        <Input
          placeholder="제품 검색..."
          value={query}
          onChange={(e) => handleSearchChange(e.target.value)}
          onFocus={() => setDropdownOpen(suggestions.length > 0)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              if (!suggestions.length) return;
              setDropdownOpen(true);
              setActiveSuggestionIndex((prev) => (prev + 1) % suggestions.length);
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              if (!suggestions.length) return;
              setDropdownOpen(true);
              setActiveSuggestionIndex((prev) => (prev - 1 + suggestions.length) % suggestions.length);
            } else if (e.key === "Enter") {
              e.preventDefault();
              handleSearchSubmit();
            } else if (e.key === "Escape") {
              setDropdownOpen(false);
            }
          }}
          className="bg-white"
        />
        {dropdownOpen && query.trim() && (
          <SearchDropdown
            suggestions={suggestions}
            activeIndex={activeSuggestionIndex}
            onHover={setActiveSuggestionIndex}
            onSelect={handleSuggestionSelect}
          />
        )}
        {query.trim() && relatedSearches.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {relatedSearches.map((term) => (
              <button
                key={term}
                type="button"
                onClick={() => {
                  setQuery(term);
                  void executeSearch(term);
                }}
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
      ) : searchResults ? (
        searchResults.length === 0 ? (
          <div className="text-sm text-gray-400">검색 결과 없음</div>
        ) : (
          <div>
            <p className="text-xs text-gray-400 mb-3">검색 결과 {searchResults.length}개</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {searchResults.map((p) => (
                <ProductCard key={p.id} product={p} />
              ))}
            </div>
          </div>
        )
      ) : saleProducts.length === 0 ? (
        <div className="text-sm text-gray-400">
          세일 제품 없음
        </div>
      ) : (
        <div>
          <p className="text-xs text-gray-400 mb-3">세일 {saleProducts.length}개</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {saleProducts.map((p) => (
              <ProductCard
                key={p.product_id}
                product={{
                  id: p.product_id,
                  channel_id: 0,
                  brand_id: null,
                  name: p.product_name,
                  product_key: p.product_key,
                  gender: null,
                  subcategory: null,
                  url: p.product_url,
                  image_url: p.image_url,
                  is_sale: true,
                  is_active: p.is_active,
                }}
                channelName={p.channel_name}
                priceKrw={p.price_krw}
                originalPriceKrw={p.original_price_krw ?? undefined}
                discountRate={p.discount_rate ?? undefined}
              />
            ))}
          </div>
        </div>
      )}

      {!loading && hotRanking.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-gray-900">오늘의 HOT 세일 TOP 10</h2>
              <p className="text-sm text-gray-500">방금 시작한 세일과 지금의 정보 가치를 우선 반영한 랭킹</p>
            </div>
            <Link href="/ranking" className="text-sm font-medium text-blue-600 hover:underline">
              전체 랭킹 보기
            </Link>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {hotRanking.map((item, index) => (
              <article key={`${item.product_key}-${item.channel_name}`} className="rounded-xl border border-gray-200 bg-white p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="text-2xl font-black text-gray-200">{String(index + 1).padStart(2, "0")}</div>
                  <div className="rounded-full bg-red-100 px-2 py-1 text-[11px] font-semibold text-red-700">
                    {item.discount_rate ? `-${item.discount_rate}%` : "세일"}
                  </div>
                </div>
                <p className="mt-3 line-clamp-2 text-sm font-semibold text-gray-900">{item.product_name}</p>
                <p className="mt-1 text-xs text-gray-500">
                  {item.brand_name ? `${item.brand_name} · ` : ""}
                  {item.channel_name}
                </p>
                <div className="mt-3 flex items-end gap-2">
                  <span className="text-lg font-bold text-gray-900">₩{item.price_krw.toLocaleString("ko-KR")}</span>
                  {item.original_price_krw && (
                    <span className="text-xs text-gray-400 line-through">₩{item.original_price_krw.toLocaleString("ko-KR")}</span>
                  )}
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                  {item.badges.map((badge) => (
                    <span key={badge} className="rounded-full bg-red-600 px-2 py-1 font-semibold text-white">
                      {badge}
                    </span>
                  ))}
                </div>
                {item.hours_since_sale_start != null && (
                  <p className="mt-3 text-xs font-medium text-red-600">
                    {formatSaleStart(item.hours_since_sale_start)}
                  </p>
                )}
                <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
                  <span>{item.total_channels}개 채널</span>
                  {item.product_key ? (
                    <Link href={`/compare/${encodeURIComponent(item.product_key)}`} className="font-medium text-blue-600 hover:underline">
                      비교 보기
                    </Link>
                  ) : (
                    <a href={item.product_url} target="_blank" rel="noreferrer" className="font-medium text-blue-600 hover:underline">
                      상품 보기
                    </a>
                  )}
                </div>
              </article>
            ))}
          </div>
        </section>
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
