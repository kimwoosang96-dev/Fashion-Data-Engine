"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { IntelMap } from "@/components/intel/IntelMap";
import {
  addWatchlistItem,
  getIntelEventDetail,
  getIntelEvents,
  getIntelMapPoints,
  getIntelTimeline,
} from "@/lib/api";
import type { IntelEvent, IntelMapPoint, IntelTimelineOut } from "@/lib/types";

const LAYERS = ["drops", "collabs", "news", "sale_start"] as const;
const TIME_RANGES = ["24h", "7d", "30d", "90d", "all"] as const;

type TimeRange = (typeof TIME_RANGES)[number];

function formatWhen(event: IntelEvent): string {
  const raw = event.event_time ?? event.detected_at;
  const dt = new Date(raw);
  return Number.isNaN(dt.getTime()) ? raw : dt.toLocaleString("ko-KR");
}

function updateQs(
  router: ReturnType<typeof useRouter>,
  search: URLSearchParams,
  patch: Record<string, string | null>
) {
  const next = new URLSearchParams(search.toString());
  Object.entries(patch).forEach(([k, v]) => {
    if (v === null || v === "") next.delete(k);
    else next.set(k, v);
  });
  router.replace(`/intel?${next.toString()}`);
}

function IntelPageContent() {
  const search = useSearchParams();
  const router = useRouter();
  const defaultLayers = (search.get("layers") || process.env.NEXT_PUBLIC_INTEL_DEFAULT_LAYER_SET || "drops,collabs,news,sale_start")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const [layers, setLayers] = useState<string[]>(defaultLayers);
  const [timeRange, setTimeRange] = useState<TimeRange>((search.get("time_range") as TimeRange) || "7d");
  const [q, setQ] = useState(search.get("q") ?? "");
  const [events, setEvents] = useState<IntelEvent[]>([]);
  const [points, setPoints] = useState<IntelMapPoint[]>([]);
  const [timeline, setTimeline] = useState<IntelTimelineOut | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(
    Number(search.get("event_id") || 0) || null
  );
  const [selectedDetail, setSelectedDetail] = useState<(IntelEvent & { details_json?: string }) | null>(null);
  const [feedScrollTop, setFeedScrollTop] = useState(0);
  const rowHeight = 96;
  const viewportRows = 7;

  const load = async (append = false, cursor?: string | null) => {
    setLoading(true);
    try {
      if (!append) {
        updateQs(router, new URLSearchParams(search.toString()), {
          layers: layers.join(","),
          time_range: timeRange,
          q: q || null,
        });
      }
      const [eventPage, map, tline] = await Promise.all([
        getIntelEvents({ layers, time_range: timeRange, q: q || undefined, cursor: cursor || undefined, limit: 80 }),
        getIntelMapPoints({ layers, time_range: timeRange, limit: 1200 }),
        getIntelTimeline({ layers, time_range: timeRange, granularity: "day" }),
      ]);
      setEvents((prev) => (append ? [...prev, ...eventPage.items] : eventPage.items));
      setNextCursor(eventPage.next_cursor);
      setPoints(map);
      setTimeline(tline);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load(false, null);
    updateQs(router, new URLSearchParams(search.toString()), {
      layers: layers.join(","),
      time_range: timeRange,
      q: q || null,
      event_id: selectedId ? String(selectedId) : null,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layers.join(","), timeRange]);

  useEffect(() => {
    if (!selectedId) {
      setSelectedDetail(null);
      return;
    }
    updateQs(router, new URLSearchParams(search.toString()), { event_id: String(selectedId) });
    void getIntelEventDetail(selectedId).then((d) => setSelectedDetail(d));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  const toggleLayer = (layer: string) => {
    setLayers((prev) => {
      const next = prev.includes(layer) ? prev.filter((x) => x !== layer) : [...prev, layer];
      return next.length ? next : prev;
    });
  };

  const start = Math.max(0, Math.floor(feedScrollTop / rowHeight) - 3);
  const end = Math.min(events.length, start + viewportRows + 8);
  const visible = useMemo(() => events.slice(start, end), [events, start, end]);
  const topPad = start * rowHeight;
  const bottomPad = Math.max(0, (events.length - end) * rowHeight);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Intel Hub</h1>
          <p className="text-sm text-gray-500">인스타/드롭/협업/뉴스를 단일 이벤트 허브로 탐색</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void load(false, null);
            }}
            placeholder="검색어"
            className="h-9 px-3 border rounded-md text-sm"
          />
          <button
            type="button"
            onClick={() => void load(false, null)}
            className="h-9 px-3 rounded-md bg-gray-900 text-white text-sm"
          >
            조회
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {LAYERS.map((layer) => {
          const active = layers.includes(layer);
          return (
            <button
              key={layer}
              type="button"
              onClick={() => toggleLayer(layer)}
              className={`px-3 py-1.5 rounded-full text-xs border ${
                active ? "bg-gray-900 text-white border-gray-900" : "bg-white text-gray-600 border-gray-200"
              }`}
            >
              {layer}
            </button>
          );
        })}
        <div className="ml-2 flex items-center gap-1">
          {TIME_RANGES.map((tr) => (
            <button
              key={tr}
              type="button"
              onClick={() => setTimeRange(tr)}
              className={`px-2.5 py-1.5 rounded-md text-xs ${
                timeRange === tr ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600"
              }`}
            >
              {tr}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[360px_minmax(0,1fr)] gap-4">
        <div className="border rounded-xl bg-white overflow-hidden">
          <div className="px-3 py-2 border-b text-sm font-semibold">Event Feed ({events.length})</div>
          <div
            className="h-[420px] overflow-y-auto"
            onScroll={(e) => setFeedScrollTop(e.currentTarget.scrollTop)}
          >
            <div style={{ paddingTop: topPad, paddingBottom: bottomPad }}>
              {visible.map((event) => (
                <button
                  key={event.id}
                  type="button"
                  onClick={() => setSelectedId(event.id)}
                  className={`w-full text-left px-3 py-2 border-b hover:bg-gray-50 ${
                    selectedId === event.id ? "bg-blue-50" : ""
                  }`}
                  style={{ minHeight: rowHeight }}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[11px] uppercase tracking-wide text-gray-500">{event.layer}</span>
                    <span className="text-[11px] text-gray-400">{formatWhen(event)}</span>
                  </div>
                  <p className="text-sm font-semibold line-clamp-2 mt-1">{event.title}</p>
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">{event.summary || "-"}</p>
                </button>
              ))}
            </div>
          </div>
          {nextCursor && (
            <button
              type="button"
              onClick={() => void load(true, nextCursor)}
              className="w-full h-10 text-sm border-t bg-gray-50 hover:bg-gray-100"
            >
              더 보기
            </button>
          )}
        </div>

        <IntelMap points={points} selectedId={selectedId} onSelect={setSelectedId} />
      </div>

      <div className="border rounded-xl bg-white p-3">
        <p className="text-sm font-semibold mb-2">Timeline (stacked)</p>
        <div className="space-y-1">
          {(timeline?.items || []).slice(-12).map((bucket) => {
            const max = Math.max(...(timeline?.items || []).map((x) => x.total), 1);
            return (
              <div key={bucket.bucket} className="grid grid-cols-[100px_minmax(0,1fr)_40px] items-center gap-2 text-xs">
                <span className="text-gray-500">{bucket.bucket}</span>
                <div className="h-4 rounded bg-gray-100 overflow-hidden flex">
                  {Object.entries(bucket.layers).map(([layer, count]) => (
                    <div
                      key={`${bucket.bucket}-${layer}`}
                      className={
                        layer === "drops"
                          ? "bg-red-400"
                          : layer === "collabs"
                            ? "bg-blue-400"
                            : layer === "news"
                              ? "bg-gray-500"
                              : "bg-emerald-500"
                      }
                      style={{ width: `${(count / max) * 100}%` }}
                      title={`${layer}: ${count}`}
                    />
                  ))}
                </div>
                <span className="text-right text-gray-700">{bucket.total}</span>
              </div>
            );
          })}
        </div>
      </div>

      {selectedDetail && (
        <div className="fixed right-0 top-0 h-full w-[360px] bg-white border-l shadow-xl p-4 overflow-y-auto z-30">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold">Event Detail</p>
            <button type="button" className="text-sm text-gray-500" onClick={() => setSelectedId(null)}>
              닫기
            </button>
          </div>
          <h3 className="mt-3 text-base font-bold">{selectedDetail.title}</h3>
          <p className="mt-1 text-sm text-gray-600">{selectedDetail.summary || "-"}</p>
          <div className="mt-3 space-y-1 text-xs text-gray-500">
            <p>Layer: {selectedDetail.layer}</p>
            <p>When: {formatWhen(selectedDetail)}</p>
            <p>Brand: {selectedDetail.brand_name || "-"}</p>
            <p>Channel: {selectedDetail.channel_name || "-"}</p>
          </div>

          <div className="mt-4 space-y-2">
            {selectedDetail.product_key && (
              <Link
                className="block h-9 leading-9 text-center rounded-md bg-gray-900 text-white text-sm"
                href={`/compare/${encodeURIComponent(selectedDetail.product_key)}`}
              >
                가격 비교로 이동
              </Link>
            )}
            {selectedDetail.brand_slug && (
              <button
                type="button"
                className="w-full h-9 rounded-md border text-sm"
                onClick={async () => {
                  await addWatchlistItem({
                    watch_type: "brand",
                    watch_value: selectedDetail.brand_slug || "",
                    notes: "Intel 이벤트에서 추가",
                  });
                  alert("브랜드 관심목록에 추가했습니다.");
                }}
              >
                브랜드 관심등록
              </button>
            )}
            {selectedDetail.channel_id && (
              <button
                type="button"
                className="w-full h-9 rounded-md border text-sm"
                onClick={async () => {
                  await addWatchlistItem({
                    watch_type: "channel",
                    watch_value: String(selectedDetail.channel_id),
                    notes: "Intel 이벤트에서 추가",
                  });
                  alert("채널 관심목록에 추가했습니다.");
                }}
              >
                채널 관심등록
              </button>
            )}
            {selectedDetail.product_key && (
              <button
                type="button"
                className="w-full h-9 rounded-md border text-sm"
                onClick={async () => {
                  await addWatchlistItem({
                    watch_type: "product_key",
                    watch_value: selectedDetail.product_key || "",
                    notes: "Intel 이벤트에서 추가",
                  });
                  alert("제품 관심목록에 추가했습니다.");
                }}
              >
                제품 관심등록
              </button>
            )}
          </div>
        </div>
      )}

      {loading && <p className="text-xs text-gray-400">로딩 중...</p>}
    </div>
  );
}

export default function IntelPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-gray-400">로딩 중...</div>}>
      <IntelPageContent />
    </Suspense>
  );
}
