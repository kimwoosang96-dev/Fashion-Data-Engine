"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getPurchases, getPurchaseStats, deletePurchase } from "@/lib/api";
import type { Purchase, PurchaseStats } from "@/lib/types";
import { ScoreBadge } from "@/components/ScoreBadge";

export default function PurchasesPage() {
  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [stats, setStats] = useState<PurchaseStats | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    const [p, s] = await Promise.all([getPurchases(100), getPurchaseStats()]);
    setPurchases(p);
    setStats(s);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleDelete = async (id: number) => {
    if (!confirm("삭제하시겠습니까?")) return;
    await deletePurchase(id);
    setPurchases((prev) => prev.filter((p) => p.id !== id));
  };

  const fmt = (n: number) => n.toLocaleString("ko-KR") + "원";

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">구매 이력</h1>
          <p className="text-sm text-gray-500 mt-1">구매 성공도 및 절감액 분석</p>
        </div>
        <Link
          href="/purchases/new"
          className="bg-gray-900 text-white text-sm px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors"
        >
          + 구매 추가
        </Link>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500">총 구매</p>
            <p className="text-xl font-bold">{stats.total_purchases}건</p>
            <p className="text-sm text-gray-600 mt-1">{fmt(stats.total_paid_krw)}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500">총 절감액</p>
            <p className="text-xl font-bold text-emerald-600">
              {stats.total_savings_vs_full_krw > 0 ? fmt(stats.total_savings_vs_full_krw) : "—"}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500">베스트 딜</p>
            {stats.best_deal ? (
              <>
                <p className="text-sm font-medium truncate">{stats.best_deal.product_name}</p>
                <p className="text-xs text-emerald-600">
                  {stats.best_deal.discount_rate}% 할인 · {fmt(stats.best_deal.savings_krw)} 절감
                </p>
              </>
            ) : (
              <p className="text-sm text-gray-400">없음</p>
            )}
          </div>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <p className="text-sm text-gray-400">로딩 중...</p>
      ) : purchases.length === 0 ? (
        <p className="text-sm text-gray-400">구매 이력이 없습니다.</p>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-500">제품</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500">채널</th>
                <th className="text-right px-4 py-3 font-medium text-gray-500">구매가</th>
                <th className="text-right px-4 py-3 font-medium text-gray-500">원가</th>
                <th className="text-center px-4 py-3 font-medium text-gray-500">등급</th>
                <th className="text-right px-4 py-3 font-medium text-gray-500">날짜</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {purchases.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <Link href={`/purchases/${p.id}`} className="font-medium hover:underline">
                      {p.product_name}
                    </Link>
                    {p.brand_slug && (
                      <span className="text-xs text-gray-400 ml-2">{p.brand_slug}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{p.channel_name}</td>
                  <td className="px-4 py-3 text-right font-medium">{fmt(p.paid_price_krw)}</td>
                  <td className="px-4 py-3 text-right text-gray-400">
                    {p.original_price_krw ? fmt(p.original_price_krw) : "—"}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Link href={`/purchases/${p.id}`}>
                      <GradeCell purchaseId={p.id} />
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-400 text-xs">
                    {p.purchased_at.slice(0, 10)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDelete(p.id)}
                      className="text-gray-300 hover:text-red-500 transition-colors"
                    >
                      ×
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

// Lazy-load grade from score API
function GradeCell({ purchaseId }: { purchaseId: number }) {
  const [grade, setGrade] = useState<string | null>(null);
  useEffect(() => {
    import("@/lib/api").then(({ getPurchaseScore }) =>
      getPurchaseScore(purchaseId).then((s) => setGrade(s.grade)).catch(() => {})
    );
  }, [purchaseId]);
  if (!grade) return <span className="text-gray-300 text-xs">—</span>;
  return <ScoreBadge grade={grade} />;
}
