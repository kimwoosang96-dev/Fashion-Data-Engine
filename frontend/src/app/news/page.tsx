"use client";
import { useEffect, useRef, useState } from "react";
import { getNews } from "@/lib/api";
import type { FashionNews } from "@/lib/types";

const SOURCES = ["전체", "hypebeast.com", "highsnobiety.com", "sneakernews.com", "complex.com"];
const LIMIT = 50;

export default function NewsPage() {
  const [items, setItems] = useState<FashionNews[]>([]);
  const [source, setSource] = useState("");
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const offsetRef = useRef(0);
  const sentinelRef = useRef<HTMLDivElement>(null);

  async function loadMore(reset = false) {
    const offset = reset ? 0 : offsetRef.current;
    setLoading(true);
    try {
      const data = await getNews(LIMIT, offset);
      const filtered = source ? data.filter((n) => n.source === source) : data;
      if (reset) {
        setItems(filtered);
      } else {
        setItems((prev) => [...prev, ...filtered]);
      }
      offsetRef.current = offset + data.length;
      setHasMore(data.length === LIMIT);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    offsetRef.current = 0;
    setHasMore(true);
    loadMore(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source]);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loading) {
          loadMore();
        }
      },
      { threshold: 0.1 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasMore, loading]);

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">패션 뉴스</h1>
        <span className="text-sm text-gray-400">{items.length}건</span>
      </div>

      <div className="flex gap-2 flex-wrap">
        {SOURCES.map((s) => (
          <button
            key={s}
            onClick={() => setSource(s === "전체" ? "" : s)}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              (s === "전체" ? source === "" : source === s)
                ? "bg-gray-900 text-white border-gray-900"
                : "border-gray-300 text-gray-600 hover:bg-gray-100"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {items.length === 0 && !loading && (
        <p className="text-sm text-gray-400 py-12 text-center">
          뉴스가 없습니다. <code className="text-xs bg-gray-100 px-1 rounded">make news</code>를 실행해 크롤해 주세요.
        </p>
      )}

      <div className="space-y-3">
        {items.map((item) => (
          <a
            key={item.id}
            href={item.url}
            target="_blank"
            rel="noreferrer"
            className="block rounded-xl border border-gray-200 bg-white p-4 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm font-medium leading-snug">{item.title}</p>
              {item.entity_name && (
                <span className="shrink-0 text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">
                  {item.entity_name}
                </span>
              )}
            </div>
            {item.summary && (
              <p className="text-xs text-gray-500 mt-1.5 line-clamp-2">{item.summary}</p>
            )}
            <p className="text-xs text-gray-400 mt-2">
              {item.source}
              {item.published_at ? ` · ${item.published_at.slice(0, 10)}` : ""}
            </p>
          </a>
        ))}
      </div>

      <div ref={sentinelRef} className="py-4 text-center text-sm text-gray-400">
        {loading ? "불러오는 중..." : hasMore ? "" : items.length > 0 ? "모두 로드됨" : ""}
      </div>
    </div>
  );
}
