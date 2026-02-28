"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { getSaleCount, getSaleHighlights } from "@/lib/api";
import type { SaleFilters, SaleHighlight } from "@/lib/types";
import { Input } from "@/components/ui/input";

const fmt = (n: number) => `₩${n.toLocaleString("ko-KR")}`;
const LIMIT = 60;
const GENDERS = [
  { label: "전체", value: "" },
  { label: "남성", value: "men" },
  { label: "여성", value: "women" },
  { label: "유니섹스", value: "unisex" },
  { label: "키즈", value: "kids" },
];
const CATEGORIES = [
  { label: "전체 카테고리", value: "" },
  { label: "신발", value: "shoes" },
  { label: "아우터", value: "outer" },
  { label: "상의", value: "top" },
  { label: "하의", value: "bottom" },
  { label: "가방", value: "bag" },
  { label: "모자", value: "cap" },
  { label: "액세서리", value: "accessory" },
];

export default function SalesPage() {
  const [items, setItems] = useState<SaleHighlight[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [gender, setGender] = useState("");
  const [category, setCategory] = useState("");
  const [minPriceInput, setMinPriceInput] = useState("");
  const [maxPriceInput, setMaxPriceInput] = useState("");
  const [filters, setFilters] = useState<SaleFilters>({});

  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    const next = await getSaleHighlights(LIMIT, offset, filters);
    setItems((prev) => [...prev, ...next]);
    setOffset((prev) => prev + LIMIT);
    if (next.length < LIMIT) setHasMore(false);
    setLoadingMore(false);
  }, [filters, hasMore, loadingMore, offset]);

  useEffect(() => {
    Promise.all([getSaleHighlights(LIMIT, 0, filters), getSaleCount(filters)])
      .then(([firstBatch, countRes]) => {
        setItems(firstBatch);
        setOffset(LIMIT);
        setHasMore(firstBatch.length === LIMIT);
        setTotal(countRes.total);
      })
      .finally(() => setLoading(false));
  }, [filters]);

  const applyFilters = () => {
    setLoading(true);
    setItems([]);
    setOffset(0);
    setHasMore(true);
    const min = minPriceInput.trim() ? Number(minPriceInput.replace(/,/g, "")) : undefined;
    const max = maxPriceInput.trim() ? Number(maxPriceInput.replace(/,/g, "")) : undefined;
    setFilters({
      gender: gender || undefined,
      category: category || undefined,
      min_price: Number.isFinite(min) ? min : undefined,
      max_price: Number.isFinite(max) ? max : undefined,
    });
  };

  const resetFilters = () => {
    setGender("");
    setCategory("");
    setMinPriceInput("");
    setMaxPriceInput("");
    setLoading(true);
    setItems([]);
    setOffset(0);
    setHasMore(true);
    setFilters({});
  };

  useEffect(() => {
    const target = sentinelRef.current;
    if (!target) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) void loadMore();
      },
      { threshold: 0.1 }
    );
    observer.observe(target);
    return () => observer.disconnect();
  }, [loadMore]);

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold">세일 제품</h1>
        <p className="text-sm text-gray-500 mt-1">
          세일율이 높은 순으로 정렬{total != null ? ` · 세일 제품 ${total.toLocaleString("ko-KR")}개` : ""}
        </p>
      </div>
      <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
        <div className="flex flex-wrap gap-2">
          {GENDERS.map((g) => (
            <button
              key={g.value || "all"}
              type="button"
              onClick={() => setGender(g.value)}
              className={`text-xs px-3 py-1.5 rounded-full border ${
                gender === g.value
                  ? "bg-gray-900 text-white border-gray-900"
                  : "bg-white text-gray-600 border-gray-200"
              }`}
            >
              {g.label}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="h-10 px-3 rounded-md border border-gray-200 bg-white text-sm"
          >
            {CATEGORIES.map((c) => (
              <option key={c.value || "all"} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
          <Input
            placeholder="최소가 (KRW)"
            value={minPriceInput}
            onChange={(e) => setMinPriceInput(e.target.value)}
          />
          <Input
            placeholder="최대가 (KRW)"
            value={maxPriceInput}
            onChange={(e) => setMaxPriceInput(e.target.value)}
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={applyFilters}
              className="h-10 px-4 rounded-md bg-gray-900 text-white text-sm font-medium"
            >
              필터 적용
            </button>
            <button
              type="button"
              onClick={resetFilters}
              className="h-10 px-4 rounded-md border border-gray-200 bg-white text-sm text-gray-600"
            >
              초기화
            </button>
          </div>
        </div>
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
                    <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium">
                      {item.total_channels > 1
                        ? `${item.total_channels}개 채널 최저가`
                        : "단일 채널 최저가"}
                    </span>
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
      {!loading && (
        <div className="pt-2">
          <div ref={sentinelRef} className="h-6" />
          {loadingMore && <p className="text-center text-sm text-gray-400">추가 로딩 중...</p>}
          {!hasMore && <p className="text-center text-sm text-gray-400">모두 불러왔습니다.</p>}
        </div>
      )}
    </div>
  );
}
