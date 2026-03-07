"use client";

import { useEffect, useState } from "react";
import { getPriceBadge } from "@/lib/api";
import type { PriceBadge as PriceBadgeData } from "@/lib/types";

const badgeCache = new Map<string, PriceBadgeData | null>();

function badgeTone(position: PriceBadgeData["price_position"], isAllTimeLow: boolean) {
  if (isAllTimeLow) return "bg-red-100 text-red-700 border-red-200";
  if (position === "low") return "bg-amber-100 text-amber-700 border-amber-200";
  if (position === "mid") return "bg-blue-100 text-blue-700 border-blue-200";
  return "bg-gray-100 text-gray-600 border-gray-200";
}

function badgeLabel(data: PriceBadgeData) {
  if (data.is_all_time_low) return "🔥 역대 최저가";
  if (data.price_position === "low") return "저가 구간";
  if (data.price_position === "mid") return "중간 가격대";
  return "고가 구간";
}

function formatKrw(value: number | null) {
  if (value == null) return "—";
  return `₩${value.toLocaleString("ko-KR")}`;
}

export function PriceBadge({
  productKey,
  detailed = false,
  initialData,
}: {
  productKey: string | null | undefined;
  detailed?: boolean;
  initialData?: PriceBadgeData | null;
}) {
  const [data, setData] = useState<PriceBadgeData | null>(initialData ?? null);

  useEffect(() => {
    if (!productKey) return;
    if (initialData) {
      badgeCache.set(productKey, initialData);
      setData(initialData);
      return;
    }
    const cached = badgeCache.get(productKey);
    if (cached !== undefined) {
      setData(cached);
      return;
    }
    let cancelled = false;
    getPriceBadge(productKey)
      .then((res) => {
        badgeCache.set(productKey, res);
        if (!cancelled) setData(res);
      })
      .catch(() => {
        badgeCache.set(productKey, null);
        if (!cancelled) setData(null);
      });
    return () => {
      cancelled = true;
    };
  }, [initialData, productKey]);

  if (!productKey || !data) return null;

  return (
    <div className={`flex flex-wrap items-center gap-2 ${detailed ? "justify-start" : ""}`}>
      <span
        className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${badgeTone(
          data.price_position,
          data.is_all_time_low,
        )}`}
      >
        {badgeLabel(data)}
      </span>
      {detailed && (
        <>
          <span className="text-xs text-gray-500">
            90일 최저: {formatKrw(data.historical_min_krw)}
            {data.historical_min_date ? ` (${data.historical_min_date})` : ""}
          </span>
          {data.discount_from_historical_high_pct != null && (
            <span className="text-xs text-gray-500">
              고점 대비 {data.discount_from_historical_high_pct}% 낮음
            </span>
          )}
        </>
      )}
    </div>
  );
}
