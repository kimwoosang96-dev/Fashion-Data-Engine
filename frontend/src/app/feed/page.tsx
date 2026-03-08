"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getActivityFeed, getPushPublicKey, subscribePush, unsubscribePush } from "@/lib/api";
import type { ActivityFeedItem } from "@/lib/types";

const FILTERS = [
  { label: "전체", value: "" },
  { label: "세일시작", value: "sale_start" },
  { label: "신제품", value: "new_drop" },
  { label: "가격인하", value: "price_cut" },
  { label: "품절", value: "sold_out" },
  { label: "재입고", value: "restock" },
] as const;

const PAGE_SIZE = 30;

function urlBase64ToUint8Array(base64String: string) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
}

function formatKrw(value: number | null) {
  return value == null ? null : `₩${value.toLocaleString("ko-KR")}`;
}

function formatWhen(value: string) {
  const diffMs = Date.now() - new Date(value).getTime();
  const diffMin = Math.max(1, Math.floor(diffMs / 60000));
  if (diffMin < 60) return `${diffMin}분 전`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}시간 전`;
  const diffDay = Math.floor(diffHour / 24);
  return `${diffDay}일 전`;
}

function badgeTone(type: ActivityFeedItem["event_type"]) {
  switch (type) {
    case "sale_start":
      return "bg-red-100 text-red-700";
    case "new_drop":
      return "bg-emerald-100 text-emerald-700";
    case "price_cut":
      return "bg-amber-100 text-amber-700";
    case "sold_out":
      return "bg-gray-200 text-gray-700";
    case "restock":
      return "bg-blue-100 text-blue-700";
  }
}

function badgeLabel(type: ActivityFeedItem["event_type"]) {
  switch (type) {
    case "sale_start":
      return "세일시작";
    case "new_drop":
      return "신제품";
    case "price_cut":
      return "가격인하";
    case "sold_out":
      return "품절";
    case "restock":
      return "재입고";
  }
}

export default function FeedPage() {
  const [items, setItems] = useState<ActivityFeedItem[]>([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [eventType, setEventType] = useState("");
  const [pushSupported, setPushSupported] = useState(false);
  const [pushBusy, setPushBusy] = useState(false);
  const [pushMsg, setPushMsg] = useState<string | null>(null);
  const [brandIdsInput, setBrandIdsInput] = useState("");

  const load = async (nextOffset: number, replace = false) => {
    const setter = replace ? setLoading : setLoadingMore;
    setter(true);
    setError(null);
    try {
      const rows = await getActivityFeed({
        event_type: eventType || undefined,
        limit: PAGE_SIZE,
        offset: nextOffset,
      });
      setItems((prev) => (replace ? rows : [...prev, ...rows]));
      setOffset(nextOffset + rows.length);
    } catch (err) {
      setError(err instanceof Error ? err.message : "피드 로드 실패");
    } finally {
      setter(false);
    }
  };

  useEffect(() => {
    void load(0, true);
    const timer = window.setInterval(() => {
      void load(0, true);
    }, 30000);
    return () => window.clearInterval(timer);
  }, [eventType]);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const wsBase = apiUrl.replace(/^http/, "ws").replace(/\/$/, "");
    let socket: WebSocket | null = null;
    let pingTimer: number | null = null;
    let retryTimer: number | null = null;
    let retryDelay = 1000;

    const connect = () => {
      socket = new WebSocket(`${wsBase}/ws/feed`);
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as ActivityFeedItem;
          if (eventType && payload.event_type !== eventType) {
            return;
          }
          setItems((prev) => {
            const next = [payload, ...prev.filter((item) => item.id !== payload.id)];
            return next.slice(0, 100);
          });
        } catch {
          // ignore malformed payloads
        }
      };
      socket.onopen = () => {
        retryDelay = 1000;
        pingTimer = window.setInterval(() => {
          socket?.send("ping");
        }, 15000);
      };
      socket.onclose = () => {
        if (pingTimer) window.clearInterval(pingTimer);
        retryTimer = window.setTimeout(connect, retryDelay);
        retryDelay = Math.min(retryDelay * 2, 30000);
      };
    };

    connect();
    return () => {
      if (pingTimer) window.clearInterval(pingTimer);
      if (retryTimer) window.clearTimeout(retryTimer);
      socket?.close();
    };
  }, [eventType]);

  useEffect(() => {
    setPushSupported(typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window);
  }, []);

  const enablePush = async () => {
    if (!pushSupported) {
      setPushMsg("이 브라우저는 웹 푸시를 지원하지 않습니다.");
      return;
    }
    setPushBusy(true);
    setPushMsg(null);
    try {
      const registration = await navigator.serviceWorker.ready;
      const keyRes = await getPushPublicKey();
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setPushMsg("알림 권한이 거부되었습니다.");
        return;
      }
      const existing = await registration.pushManager.getSubscription();
      if (existing) {
        await unsubscribePush(existing.endpoint);
        await existing.unsubscribe();
      }
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(keyRes.public_key),
      });
      const json = subscription.toJSON();
      const brandIds = brandIdsInput
        .split(",")
        .map((row) => Number(row.trim()))
        .filter((row) => Number.isInteger(row) && row > 0);
      await subscribePush({
        endpoint: subscription.endpoint,
        keys: {
          p256dh: json.keys?.p256dh ?? "",
          auth: json.keys?.auth ?? "",
        },
        brand_ids: brandIds,
      });
      setPushMsg("웹 푸시 구독이 저장되었습니다.");
    } catch (err) {
      setPushMsg(err instanceof Error ? err.message : "푸시 구독 실패");
    } finally {
      setPushBusy(false);
    }
  };

  const disablePush = async () => {
    if (!pushSupported) return;
    setPushBusy(true);
    setPushMsg(null);
    try {
      const registration = await navigator.serviceWorker.ready;
      const existing = await registration.pushManager.getSubscription();
      if (existing) {
        await unsubscribePush(existing.endpoint);
        await existing.unsubscribe();
      }
      setPushMsg("웹 푸시 구독이 해제되었습니다.");
    } catch (err) {
      setPushMsg(err instanceof Error ? err.message : "푸시 해제 실패");
    } finally {
      setPushBusy(false);
    }
  };

  const hasMore = useMemo(() => items.length >= PAGE_SIZE && items.length === offset, [items.length, offset]);

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">실시간 피드</h1>
        <p className="mt-1 text-sm text-gray-500">intel 이벤트를 기반으로 최근 변화만 빠르게 모아봅니다.</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((filter) => (
          <button
            key={filter.value || "all"}
            type="button"
            onClick={() => setEventType(filter.value)}
            className={`rounded-full px-3 py-1.5 text-xs font-medium ${
              eventType === filter.value
                ? "bg-gray-900 text-white"
                : "bg-white text-gray-600 ring-1 ring-gray-200 hover:bg-gray-50"
            }`}
          >
            {filter.label}
          </button>
        ))}
      </div>

      <section className="rounded-2xl border border-gray-200 bg-white p-4 space-y-3">
        <div>
          <h2 className="text-sm font-semibold text-gray-900">웹 푸시 알림</h2>
          <p className="mt-1 text-xs text-gray-500">
            브랜드 ID를 쉼표로 입력하면 해당 브랜드 이벤트만 구독합니다. 비워두면 전체 이벤트를 받습니다.
          </p>
        </div>
        <div className="flex flex-col gap-2 md:flex-row">
          <input
            value={brandIdsInput}
            onChange={(e) => setBrandIdsInput(e.target.value)}
            placeholder="예: 12,34,56"
            className="h-10 flex-1 rounded-md border border-gray-200 px-3 text-sm"
          />
          <button
            type="button"
            onClick={() => void enablePush()}
            disabled={pushBusy}
            className="rounded-lg bg-gray-900 px-4 py-2 text-sm text-white disabled:opacity-60"
          >
            {pushBusy ? "처리 중..." : "알림 받기"}
          </button>
          <button
            type="button"
            onClick={() => void disablePush()}
            disabled={pushBusy}
            className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm text-gray-700 disabled:opacity-60"
          >
            구독 해제
          </button>
        </div>
        {pushMsg && <p className="text-xs text-gray-500">{pushMsg}</p>}
      </section>

      {loading ? (
        <p className="text-sm text-gray-400">피드 로딩 중...</p>
      ) : error ? (
        <p className="text-sm text-red-500">{error}</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-gray-400">표시할 이벤트가 없습니다.</p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const href = item.product_key
              ? `/product/${encodeURIComponent(item.product_key)}`
              : item.source_url;
            return (
              <article key={item.id} className="rounded-2xl border border-gray-200 bg-white p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ${badgeTone(item.event_type)}`}>
                        {badgeLabel(item.event_type)}
                      </span>
                      <span className="text-xs text-gray-400">{formatWhen(item.detected_at)}</span>
                    </div>
                    <p className="mt-2 text-sm font-semibold text-gray-900">
                      {item.brand_name ? `${item.brand_name} — ` : ""}
                      {item.product_name ?? "이름 미상"}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">
                      {item.channel_name ?? "채널 미상"}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs text-gray-600">
                      {formatKrw(item.price_krw) && <span>{formatKrw(item.price_krw)}</span>}
                      {item.discount_rate != null && (
                        <span className="font-medium text-red-600">{item.discount_rate}% OFF</span>
                      )}
                    </div>
                  </div>
                  {href ? (
                    href.startsWith("/") ? (
                      <Link href={href} className="shrink-0 text-sm font-medium text-blue-600 hover:underline">
                        바로 보기
                      </Link>
                    ) : (
                      <a href={href} target="_blank" rel="noreferrer" className="shrink-0 text-sm font-medium text-blue-600 hover:underline">
                        바로 보기
                      </a>
                    )
                  ) : null}
                </div>
              </article>
            );
          })}

          {hasMore && (
            <div className="pt-2">
              <button
                type="button"
                onClick={() => void load(offset)}
                disabled={loadingMore}
                className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-60"
              >
                {loadingMore ? "불러오는 중..." : "더 보기"}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
