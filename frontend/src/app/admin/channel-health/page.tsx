"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { getAdminChannelHealth, reactivateAdminChannel } from "@/lib/api";
import type { AdminChannelHealth } from "@/lib/types";

type FilterKey = "all" | "healthy" | "degraded" | "dead";

function Sparkline({ values }: { values: number[] }) {
  if (!values.length) {
    return <span className="text-xs text-zinc-400">기록 없음</span>;
  }
  const width = 110;
  const height = 28;
  const max = Math.max(...values, 1);
  const points = values.map((value, index) => {
    const x = values.length === 1 ? width / 2 : (index / (values.length - 1)) * width;
    const y = height - (value / max) * (height - 4) - 2;
    return `${x},${y}`;
  });
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-7 w-28">
      <polyline
        points={points.join(" ")}
        fill="none"
        stroke="#18181b"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleString("ko-KR");
}

export default function ChannelHealthPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<AdminChannelHealth[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterKey>("all");
  const [message, setMessage] = useState("");

  const load = async (adminToken: string) => {
    setLoading(true);
    try {
      const rows = await getAdminChannelHealth(adminToken);
      setItems(rows);
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "채널 건강 상태를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const stored = localStorage.getItem("admin_token") || "";
    setToken(stored);
    if (stored) {
      void load(stored);
    } else {
      setLoading(false);
      setMessage("admin_token이 없습니다. /admin 페이지에서 먼저 토큰을 저장하세요.");
    }
  }, []);

  const filtered = useMemo(() => {
    if (filter === "all") return items;
    return items.filter((item) => item.status === filter);
  }, [filter, items]);

  const onReactivate = async (channelId: number) => {
    if (!token) return;
    try {
      const res = await reactivateAdminChannel(token, channelId);
      setMessage(
        res.reactivated
          ? `채널 ${channelId} 재활성화 성공 (${res.platform_detected ?? "platform unknown"})`
          : `채널 ${channelId} 재활성화 실패 (${res.http_status ?? "no-status"} / ${res.note || "probe failed"})`
      );
      await load(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "재활성화 요청 실패");
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-zinc-400">Admin</p>
          <h1 className="text-3xl font-black tracking-tight text-zinc-950">채널 건강 대시보드</h1>
          <p className="mt-1 text-sm text-zinc-500">최근 5회 yield와 마지막 성공 시각 기준으로 채널 수집 상태를 확인합니다.</p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/admin" className="rounded-full border border-zinc-300 px-4 py-2 text-sm font-semibold text-zinc-700">
            관리자 홈
          </Link>
          <button
            type="button"
            onClick={() => token && load(token)}
            className="rounded-full bg-zinc-950 px-4 py-2 text-sm font-semibold text-white"
          >
            새로고침
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {(["all", "healthy", "degraded", "dead"] as FilterKey[]).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setFilter(key)}
            className={`rounded-full px-3 py-1.5 text-sm font-medium ${
              filter === key ? "bg-zinc-950 text-white" : "bg-zinc-100 text-zinc-600"
            }`}
          >
            {key === "all" ? "전체" : key}
          </button>
        ))}
      </div>

      {message && <p className="rounded-2xl bg-zinc-100 px-4 py-3 text-sm text-zinc-600">{message}</p>}

      {loading ? (
        <p className="text-sm text-zinc-400">불러오는 중...</p>
      ) : (
        <div className="overflow-hidden rounded-[28px] border border-black/10 bg-white shadow-[0_16px_48px_rgba(0,0,0,0.05)]">
          <table className="min-w-full text-sm">
            <thead className="bg-zinc-50 text-zinc-500">
              <tr>
                <th className="px-4 py-3 text-left font-medium">채널</th>
                <th className="px-4 py-3 text-left font-medium">플랫폼</th>
                <th className="px-4 py-3 text-left font-medium">최근 yield</th>
                <th className="px-4 py-3 text-left font-medium">평균</th>
                <th className="px-4 py-3 text-left font-medium">최근 성공</th>
                <th className="px-4 py-3 text-left font-medium">상태</th>
                <th className="px-4 py-3 text-right font-medium">조치</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {filtered.map((item) => (
                <tr key={item.channel_id} className="align-top">
                  <td className="px-4 py-4">
                    <div className="font-semibold text-zinc-950">{item.channel_name}</div>
                    <a href={item.channel_url} target="_blank" rel="noreferrer" className="text-xs text-zinc-400 hover:underline">
                      {item.channel_url}
                    </a>
                    <div className="mt-1 text-xs text-zinc-400">parse: {item.parse_method ?? "unknown"}</div>
                  </td>
                  <td className="px-4 py-4 text-zinc-600">{item.platform ?? "unknown"}</td>
                  <td className="px-4 py-4">
                    <Sparkline values={item.recent_yields} />
                    <div className="mt-1 text-xs text-zinc-400">{item.recent_yields.join(" / ") || "기록 없음"}</div>
                  </td>
                  <td className="px-4 py-4 font-semibold text-zinc-950">{item.avg_yield}</td>
                  <td className="px-4 py-4 text-zinc-600">{formatDate(item.last_success_at)}</td>
                  <td className="px-4 py-4">
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-semibold ${
                        item.status === "healthy"
                          ? "bg-emerald-100 text-emerald-700"
                          : item.status === "degraded"
                            ? "bg-amber-100 text-amber-700"
                            : "bg-red-100 text-red-700"
                      }`}
                    >
                      {item.status}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-right">
                    <button
                      type="button"
                      onClick={() => onReactivate(item.channel_id)}
                      className="rounded-full border border-zinc-300 px-3 py-1.5 text-xs font-semibold text-zinc-700"
                    >
                      재활성화 시도
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
