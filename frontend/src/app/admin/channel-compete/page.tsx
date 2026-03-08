"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getAdminChannelCompete } from "@/lib/api";
import type { AdminChannelCompeteRow } from "@/lib/types";

function pct(value: number) {
  return `${value.toFixed(1)}%`;
}

export default function AdminChannelCompetePage() {
  const [token, setToken] = useState("");
  const [rows, setRows] = useState<AdminChannelCompeteRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [minMatches, setMinMatches] = useState(10);

  const load = async (adminToken: string, matches = minMatches) => {
    setLoading(true);
    try {
      const data = await getAdminChannelCompete(adminToken, matches, 120);
      setRows(data);
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "채널 경쟁력 데이터를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const stored = localStorage.getItem("admin_token") || "";
    setToken(stored);
    if (stored) {
      void load(stored, minMatches);
    } else {
      setLoading(false);
      setMessage("admin_token이 없습니다. /admin 페이지에서 먼저 토큰을 저장하세요.");
    }
  }, []);

  const summary = useMemo(() => {
    if (!rows.length) return null;
    const best = [...rows].sort((a, b) => b.cheapest_ratio - a.cheapest_ratio)[0];
    return {
      channels: rows.length,
      best,
    };
  }, [rows]);

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-zinc-400">Admin</p>
          <h1 className="text-3xl font-black tracking-tight text-zinc-950">채널 경쟁력 분석</h1>
          <p className="mt-1 text-sm text-zinc-500">같은 normalized key 기준으로 채널별 최저가 점유율과 평균 가격 순위를 집계합니다.</p>
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

      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-zinc-200 bg-white px-4 py-3">
        <label className="text-sm text-zinc-600">
          최소 매칭 수
          <input
            type="number"
            min={1}
            max={100}
            value={minMatches}
            onChange={(e) => setMinMatches(Math.max(1, Math.min(100, Number(e.target.value) || 1)))}
            className="ml-2 w-20 rounded-lg border border-zinc-300 px-2 py-1"
          />
        </label>
        <button
          type="button"
          onClick={() => token && load(token, minMatches)}
          className="rounded-full border border-zinc-300 px-3 py-1.5 text-xs font-semibold text-zinc-700"
        >
          적용
        </button>
        {summary && (
          <p className="ml-auto text-sm text-zinc-500">
            {summary.channels}개 채널 분석 · 최고 점유율 {summary.best.channel_name} {pct(summary.best.cheapest_ratio)}
          </p>
        )}
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
                <th className="px-4 py-3 text-right font-medium">매칭 제품</th>
                <th className="px-4 py-3 text-right font-medium">평균 순위</th>
                <th className="px-4 py-3 text-right font-medium">최저가 횟수</th>
                <th className="px-4 py-3 text-right font-medium">최저가 점유율</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {rows.map((row) => (
                <tr key={row.channel_id}>
                  <td className="px-4 py-4">
                    <div className="font-semibold text-zinc-950">{row.channel_name}</div>
                    <div className="text-xs text-zinc-400">
                      {row.country ?? "국가 미상"} · {row.platform ?? "platform unknown"}
                    </div>
                  </td>
                  <td className="px-4 py-4 text-right font-semibold text-zinc-900">{row.matched_products}</td>
                  <td className="px-4 py-4 text-right text-zinc-700">{row.avg_price_rank.toFixed(2)}</td>
                  <td className="px-4 py-4 text-right text-zinc-700">{row.cheapest_count}</td>
                  <td className="px-4 py-4 text-right">
                    <span className="rounded-full bg-lime-100 px-2 py-1 text-xs font-semibold text-lime-800">
                      {pct(row.cheapest_ratio)}
                    </span>
                  </td>
                </tr>
              ))}
              {!rows.length && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-zinc-400">
                    집계할 경쟁 데이터가 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
