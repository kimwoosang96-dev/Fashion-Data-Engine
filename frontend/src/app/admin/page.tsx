"use client";

import { useEffect, useState } from "react";
import { getAdminChannelsHealth, getAdminStats, triggerAdminCrawl } from "@/lib/api";
import type { AdminChannelHealth, AdminStats } from "@/lib/types";
import { Input } from "@/components/ui/input";

export default function AdminPage() {
  const [token, setToken] = useState("");
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [health, setHealth] = useState<AdminChannelHealth[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string>("");

  const load = async (adminToken: string) => {
    setLoading(true);
    setMsg("");
    try {
      const [s, h] = await Promise.all([
        getAdminStats(adminToken),
        getAdminChannelsHealth(adminToken, 250, 0),
      ]);
      setStats(s);
      setHealth(h);
      localStorage.setItem("admin_token", adminToken);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "관리 API 호출 실패");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const stored = localStorage.getItem("admin_token") || "";
    if (stored) {
      setToken(stored);
      void load(stored);
    }
  }, []);

  const runJob = async (job: "brands" | "products" | "drops") => {
    if (!token.trim()) return;
    setMsg("");
    try {
      const res = await triggerAdminCrawl(token.trim(), job, false);
      setMsg(`${res.job} 크롤 트리거됨 (pid=${res.pid ?? "-"})`);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "크롤 트리거 실패");
    }
  };

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold">운영관리</h1>
        <p className="text-sm text-gray-500 mt-1">DB 현황, 채널 헬스, 크롤 제어, 환율</p>
      </div>
      <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
        <div className="flex gap-2">
          <Input
            type="password"
            placeholder="ADMIN_BEARER_TOKEN"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
          <button
            type="button"
            onClick={() => void load(token.trim())}
            className="px-4 h-10 rounded-md bg-gray-900 text-white text-sm"
          >
            조회
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => void runJob("brands")} className="px-3 h-9 rounded-md border text-sm">
            브랜드 크롤 실행
          </button>
          <button type="button" onClick={() => void runJob("products")} className="px-3 h-9 rounded-md border text-sm">
            제품 크롤 실행
          </button>
          <button type="button" onClick={() => void runJob("drops")} className="px-3 h-9 rounded-md border text-sm">
            드롭 크롤 실행
          </button>
        </div>
        {msg && <p className="text-xs text-gray-600">{msg}</p>}
      </div>

      {loading && <p className="text-sm text-gray-400">로딩 중...</p>}

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Stat label="채널" value={stats.counts.channels} />
          <Stat label="채널-브랜드 링크" value={stats.counts.channel_brands} />
          <Stat label="제품" value={stats.counts.products} />
          <Stat label="가격 이력" value={stats.counts.price_history} />
        </div>
      )}

      {stats && (
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <h2 className="text-sm font-semibold mb-2">환율 (→ KRW)</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
            {stats.exchange_rates.slice(0, 8).map((r) => (
              <div key={`${r.from_currency}-${r.fetched_at}`} className="border rounded-md px-3 py-2">
                <p className="font-medium">{r.from_currency}</p>
                <p className="text-gray-600">{r.rate.toLocaleString("ko-KR")}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {health.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3">채널</th>
                <th className="text-left px-4 py-3">국가</th>
                <th className="text-right px-4 py-3">브랜드</th>
                <th className="text-right px-4 py-3">제품</th>
                <th className="text-right px-4 py-3">세일</th>
                <th className="text-left px-4 py-3">헬스</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {health.map((row) => (
                <tr key={row.channel_id}>
                  <td className="px-4 py-3">
                    <p className="font-medium">{row.name}</p>
                    <p className="text-xs text-gray-400">{row.channel_type ?? "-"}</p>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{row.country ?? "-"}</td>
                  <td className="px-4 py-3 text-right">{row.brand_count}</td>
                  <td className="px-4 py-3 text-right">{row.product_count}</td>
                  <td className="px-4 py-3 text-right">{row.sale_count}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        row.health === "ok" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
                      }`}
                    >
                      {row.health === "ok" ? "정상" : "점검필요"}
                    </span>
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

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-xl font-bold mt-1">{value.toLocaleString("ko-KR")}</p>
    </div>
  );
}
