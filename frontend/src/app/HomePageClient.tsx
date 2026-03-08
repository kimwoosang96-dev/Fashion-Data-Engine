"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { getSearchSuggestions, searchProductsV2 } from "@/lib/api";
import type { ActivityFeedItem, AdminIntelStatus, Brand, Channel, SaleHighlight, SearchSuggestion, SearchV2Item } from "@/lib/types";
import { SearchDropdown } from "@/components/SearchDropdown";

const SEARCH_PLACEHOLDERS = [
  "팔라스 박스로고티 M사이즈 재고있는 채널은?",
  "슈프림 요즘 세일 많이 해?",
  "나이키 SB 덩크 최저가 어디서 살 수 있어?",
  "최근 2주 안에 드롭된 신제품 알려줘",
];

function formatKrw(value: number | null) {
  return value == null ? "가격 확인" : `₩${value.toLocaleString("ko-KR")}`;
}

function formatMinutes(value: number | null | undefined) {
  if (value == null) return "업데이트 시각 미상";
  if (value < 60) return `${value}분 전 업데이트`;
  if (value < 1440) return `${Math.round(value / 60)}시간 전 업데이트`;
  return `${Math.round(value / 1440)}일 전 업데이트`;
}

function feedLabel(type: ActivityFeedItem["event_type"]) {
  switch (type) {
    case "sale_start":
      return "세일 시작";
    case "new_drop":
      return "신규 드롭";
    case "price_cut":
      return "가격 인하";
    case "sold_out":
      return "품절";
    case "restock":
      return "재입고";
  }
}

export function HomePageClient({
  initialSaleHighlights,
  initialDrops,
  stats,
  channels,
  brands,
}: {
  initialSaleHighlights: SaleHighlight[];
  initialDrops: ActivityFeedItem[];
  stats: AdminIntelStatus | null;
  channels: Channel[];
  brands: Brand[];
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchV2Item[]>([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [placeholderText, setPlaceholderText] = useState("");
  const boxRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onClickOutside = (event: MouseEvent) => {
      if (!boxRef.current?.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined" && new URLSearchParams(window.location.search).get("focus") === "search") {
      inputRef.current?.focus();
    }
  }, []);

  useEffect(() => {
    const fullText = SEARCH_PLACEHOLDERS[placeholderIndex];
    let cursor = 0;
    const timer = window.setInterval(() => {
      cursor += 1;
      setPlaceholderText(fullText.slice(0, cursor));
      if (cursor >= fullText.length) {
        window.clearInterval(timer);
        window.setTimeout(() => {
          setPlaceholderIndex((prev) => (prev + 1) % SEARCH_PLACEHOLDERS.length);
          setPlaceholderText("");
        }, 1800);
      }
    }, 60);
    return () => window.clearInterval(timer);
  }, [placeholderIndex]);

  useEffect(() => {
    const trimmed = query.trim();
    if (!trimmed) {
      setSuggestions([]);
      setDropdownOpen(false);
      return;
    }
    const timer = window.setTimeout(() => {
      void getSearchSuggestions(trimmed, 8)
        .then((rows) => {
          setSuggestions(rows);
          setActiveIndex(0);
          setDropdownOpen(rows.length > 0);
        })
        .catch(() => setSuggestions([]));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  const executeSearch = async (term: string) => {
    const trimmed = term.trim();
    if (!trimmed) return;
    setSearching(true);
    setError(null);
    setDropdownOpen(false);
    try {
      const rows = await searchProductsV2(trimmed, "semantic", 12);
      setResults(rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "검색 실패");
      setResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleSuggestionSelect = (item: SearchSuggestion) => {
    if (item.type === "brand" && item.slug) {
      window.location.href = `/brands/${encodeURIComponent(item.slug)}`;
      return;
    }
    if (item.product_key) {
      window.location.href = `/product/${encodeURIComponent(item.product_key)}`;
      return;
    }
    setQuery(item.label);
    void executeSearch(item.label);
  };

  const liveStats = useMemo(() => {
    return [
      { label: "활성 채널", value: `${channels.filter((row) => row.is_active).length}` },
      { label: "브랜드", value: `${brands.length}` },
      {
        label: "최근 24h 이벤트",
        value: stats ? `${stats.activity_feed_24h}` : `${initialDrops.length}`,
      },
      {
        label: "신선도",
        value: formatMinutes(stats?.freshness_minutes),
      },
    ];
  }, [brands.length, channels, initialDrops.length, stats]);

  return (
    <div className="min-h-full bg-[radial-gradient(circle_at_top_left,_rgba(20,20,20,0.08),_transparent_36%),linear-gradient(180deg,_#f7f4ee_0%,_#f4efe7_35%,_#efe8dc_100%)]">
      <section className="mx-auto max-w-7xl px-6 py-10 md:px-10 md:py-16">
        <div className="grid gap-10 lg:grid-cols-[1.25fr_0.75fr]">
          <div className="space-y-8">
            <div className="space-y-4">
              <p className="inline-flex items-center rounded-full border border-black/10 bg-white/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.28em] text-gray-600">
                Fashion Data Infrastructure
              </p>
              <div className="space-y-3">
                <h1 className="max-w-4xl text-4xl font-black leading-none tracking-[-0.04em] text-zinc-950 md:text-6xl">
                  AI가 바로 질의할 수 있는
                  <br />
                  패션 브랜드 가격·재고 데이터
                </h1>
                <p className="max-w-2xl text-base leading-7 text-zinc-700 md:text-lg">
                  세일 시작, 가격 인하, 드롭, 채널별 재고를 자연어로 찾고 바로 비교합니다.
                </p>
              </div>
            </div>

            <div ref={boxRef} className="rounded-[28px] border border-black/10 bg-white/90 p-4 shadow-[0_20px_60px_rgba(0,0,0,0.08)] backdrop-blur">
              <div className="flex flex-col gap-3 md:flex-row">
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onFocus={() => setDropdownOpen(suggestions.length > 0)}
                  onKeyDown={(e) => {
                    if (e.key === "ArrowDown") {
                      e.preventDefault();
                      if (!suggestions.length) return;
                      setActiveIndex((prev) => (prev + 1) % suggestions.length);
                      setDropdownOpen(true);
                    } else if (e.key === "ArrowUp") {
                      e.preventDefault();
                      if (!suggestions.length) return;
                      setActiveIndex((prev) => (prev - 1 + suggestions.length) % suggestions.length);
                    } else if (e.key === "Enter") {
                      e.preventDefault();
                      const active = suggestions[activeIndex];
                      if (dropdownOpen && active) {
                        handleSuggestionSelect(active);
                      } else {
                        void executeSearch(query);
                      }
                    } else if (e.key === "Escape") {
                      setDropdownOpen(false);
                    }
                  }}
                  placeholder={placeholderText || SEARCH_PLACEHOLDERS[placeholderIndex]}
                  className="h-14 flex-1 rounded-2xl border border-transparent bg-zinc-100 px-5 text-base outline-none ring-0 placeholder:text-zinc-400 focus:border-zinc-300"
                />
                <button
                  type="button"
                  onClick={() => void executeSearch(query)}
                  className="h-14 rounded-2xl bg-zinc-950 px-6 text-sm font-semibold text-white transition hover:bg-zinc-800"
                >
                  {searching ? "검색 중..." : "AI 검색"}
                </button>
              </div>
              {dropdownOpen && query.trim() && (
                <div className="relative">
                  <SearchDropdown
                    suggestions={suggestions}
                    activeIndex={activeIndex}
                    onHover={setActiveIndex}
                    onSelect={handleSuggestionSelect}
                  />
                </div>
              )}
              <div className="mt-4 flex flex-wrap gap-2">
                {SEARCH_PLACEHOLDERS.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => {
                      setQuery(item);
                      void executeSearch(item);
                    }}
                    className="rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-xs text-zinc-600 transition hover:border-zinc-400 hover:text-zinc-950"
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>

            {error && <p className="text-sm text-red-600">{error}</p>}

            {results.length > 0 && (
              <section className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-zinc-950">검색 결과</h2>
                  <p className="text-sm text-zinc-500">{results.length}개 항목</p>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  {results.map((item) => (
                    <Link
                      key={`${item.id}-${item.url}`}
                      href={item.product_key ? `/product/${encodeURIComponent(item.product_key)}` : item.url}
                      className="rounded-2xl border border-black/10 bg-white/90 p-4 transition hover:-translate-y-0.5 hover:shadow-lg"
                    >
                      <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">
                        {item.brand_name ?? "Brand unknown"} {item.channel_name ? `· ${item.channel_name}` : ""}
                      </p>
                      <h3 className="mt-2 text-base font-semibold text-zinc-950">{item.product_name}</h3>
                      <div className="mt-3 flex items-center justify-between text-sm">
                        <span className="font-medium text-emerald-700">{formatKrw(item.price_krw)}</span>
                        {item.similarity != null && (
                          <span className="rounded-full bg-zinc-100 px-2 py-1 text-xs text-zinc-500">
                            semantic {Math.round(item.similarity * 100)}%
                          </span>
                        )}
                      </div>
                    </Link>
                  ))}
                </div>
              </section>
            )}
          </div>

          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
              {liveStats.map((item) => (
                <div key={item.label} className="rounded-[24px] border border-black/10 bg-zinc-950 p-5 text-white">
                  <p className="text-xs uppercase tracking-[0.22em] text-white/60">{item.label}</p>
                  <p className="mt-3 text-2xl font-bold tracking-tight">{item.value}</p>
                </div>
              ))}
            </div>
            <div className="rounded-[28px] border border-black/10 bg-[#d8ff63] p-5 text-zinc-950">
              <p className="text-xs uppercase tracking-[0.22em] text-zinc-700">AI Agents</p>
              <h2 className="mt-3 text-2xl font-black leading-tight">Claude, Codex, GPT에서 바로 붙일 수 있는 데이터 레이어</h2>
              <p className="mt-3 text-sm leading-6 text-zinc-800">
                MCP, OAuth, 실시간 피드, semantic search를 준비해 둔 상태입니다.
              </p>
              <div className="mt-5 flex gap-3">
                <Link href="/intel" className="rounded-full bg-zinc-950 px-4 py-2 text-sm font-semibold text-white">
                  Intel 보기
                </Link>
                <Link href="/feed" className="rounded-full border border-zinc-950 px-4 py-2 text-sm font-semibold text-zinc-950">
                  실시간 피드
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl space-y-12 px-6 pb-16 md:px-10">
        <div className="grid gap-8 xl:grid-cols-[1.1fr_0.9fr]">
          <section className="space-y-4">
            <div className="flex items-end justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-zinc-400">Sale Highlights</p>
                <h2 className="text-2xl font-bold tracking-tight text-zinc-950">지금 바로 확인할 세일</h2>
              </div>
              <Link href="/sales" className="text-sm text-zinc-500 hover:text-zinc-900">전체 보기</Link>
            </div>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {initialSaleHighlights.slice(0, 6).map((item) => (
                <Link
                  key={`${item.product_id}-${item.product_url}`}
                  href={item.product_key ? `/product/${encodeURIComponent(item.product_key)}` : item.product_url}
                  className="overflow-hidden rounded-[24px] border border-black/10 bg-white shadow-[0_14px_40px_rgba(0,0,0,0.06)] transition hover:-translate-y-0.5"
                >
                  <div className="aspect-[4/3] bg-zinc-100">
                    {item.image_url ? (
                      <img src={item.image_url} alt={item.product_name} className="h-full w-full object-cover" />
                    ) : null}
                  </div>
                  <div className="space-y-2 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">{item.channel_name}</p>
                    <h3 className="line-clamp-2 text-sm font-semibold text-zinc-950">{item.product_name}</h3>
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-bold text-emerald-700">{formatKrw(item.price_krw)}</span>
                      {item.original_price_krw != null && (
                        <span className="text-xs text-zinc-400 line-through">{formatKrw(item.original_price_krw)}</span>
                      )}
                      {item.discount_rate != null && (
                        <span className="rounded-full bg-red-100 px-2 py-0.5 text-[11px] font-semibold text-red-700">
                          -{item.discount_rate}%
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </section>

          <section className="space-y-4">
            <div className="flex items-end justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-zinc-400">New Drops</p>
                <h2 className="text-2xl font-bold tracking-tight text-zinc-950">최근 감지된 드롭</h2>
              </div>
              <Link href="/drops/calendar" className="text-sm text-zinc-500 hover:text-zinc-900">캘린더</Link>
            </div>
            <div className="space-y-3">
              {initialDrops.slice(0, 8).map((item) => (
                <article key={item.id} className="rounded-[22px] border border-black/10 bg-white p-4 shadow-[0_10px_28px_rgba(0,0,0,0.05)]">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">{feedLabel(item.event_type)}</p>
                      <h3 className="mt-1 text-sm font-semibold text-zinc-950">{item.product_name}</h3>
                      <p className="mt-1 text-xs text-zinc-500">{item.brand_name ?? "브랜드 미상"}</p>
                    </div>
                    <Link
                      href={item.product_key ? `/product/${encodeURIComponent(item.product_key)}` : (item.source_url ?? "/feed")}
                      className="rounded-full border border-zinc-200 px-3 py-1 text-xs font-medium text-zinc-700"
                    >
                      보기
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>
      </section>
    </div>
  );
}
