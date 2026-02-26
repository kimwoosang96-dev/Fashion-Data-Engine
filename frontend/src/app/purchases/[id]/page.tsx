"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getPurchaseScore, deletePurchase } from "@/lib/api";
import type { Score } from "@/lib/types";
import { ScoreBadge } from "@/components/ScoreBadge";

export default function PurchaseScorePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [score, setScore] = useState<Score | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPurchaseScore(Number(id))
      .then(setScore)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const handleDelete = async () => {
    if (!confirm("이 구매 기록을 삭제하시겠습니까?")) return;
    await deletePurchase(Number(id));
    router.push("/purchases");
  };

  const fmt = (n: number) => n.toLocaleString("ko-KR") + "원";

  if (loading) return <div className="p-6 text-sm text-gray-400">로딩 중...</div>;
  if (error || !score) return <div className="p-6 text-sm text-red-500">{error ?? "데이터를 불러올 수 없습니다"}</div>;

  const percentileText = score.percentile !== null
    ? `하위 ${score.percentile.toFixed(0)}% (${score.data_points}개 데이터 중)`
    : `데이터 부족 (${score.data_points}개)`;

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <Link href="/purchases" className="text-xs text-gray-400 hover:text-gray-600">← 구매 이력</Link>
          <h1 className="text-xl font-bold mt-1">{score.product_name}</h1>
          <p className="text-sm text-gray-500">#{score.purchase_id}</p>
        </div>
        <button onClick={handleDelete} className="text-sm text-red-400 hover:text-red-600">삭제</button>
      </div>

      {/* Grade card */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 flex items-center gap-6">
        <div className="text-center">
          <ScoreBadge grade={score.grade} size="lg" />
          <p className="text-xs text-gray-400 mt-2">등급</p>
        </div>
        <div className="flex-1 space-y-1">
          <p className="text-2xl font-bold">{fmt(score.paid_price_krw)}</p>
          <p className="text-sm text-gray-500">{percentileText}</p>
          <p className="text-sm text-gray-700 mt-2">{score.verdict}</p>
          <p className="text-lg">{score.badge}</p>
        </div>
      </div>

      {/* Price analysis */}
      <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
        <div className="px-5 py-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">가격 분석</h2>
          <div className="grid grid-cols-3 gap-4">
            <PriceRow label="최저가" value={score.min_ever_krw} fmt={fmt} highlight="green" />
            <PriceRow label="평균가" value={score.avg_krw} fmt={fmt} />
            <PriceRow label="최고가" value={score.max_ever_krw} fmt={fmt} highlight="red" />
          </div>
        </div>
        {(score.savings_vs_full !== null || score.savings_vs_avg !== null) && (
          <div className="px-5 py-4 space-y-2">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">절감액</h2>
            {score.savings_vs_full !== null && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">원가 대비</span>
                <span className={score.savings_vs_full >= 0 ? "text-emerald-600 font-medium" : "text-red-500 font-medium"}>
                  {score.savings_vs_full >= 0 ? "+" : ""}{fmt(score.savings_vs_full)}
                </span>
              </div>
            )}
            {score.savings_vs_avg !== null && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">평균가 대비</span>
                <span className={score.savings_vs_avg >= 0 ? "text-emerald-600 font-medium" : "text-red-500 font-medium"}>
                  {score.savings_vs_avg >= 0 ? "+" : ""}{fmt(score.savings_vs_avg)}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Price compare link */}
      {score.product_key && (
        <Link
          href={`/compare/${encodeURIComponent(score.product_key)}`}
          className="block text-center text-sm text-blue-600 hover:underline"
        >
          채널별 가격 비교 보기 →
        </Link>
      )}
    </div>
  );
}

function PriceRow({
  label, value, fmt, highlight,
}: {
  label: string;
  value: number | null;
  fmt: (n: number) => string;
  highlight?: "green" | "red";
}) {
  const color = highlight === "green" ? "text-emerald-600" : highlight === "red" ? "text-red-500" : "text-gray-900";
  return (
    <div className="text-center">
      <p className="text-xs text-gray-400">{label}</p>
      <p className={`text-sm font-medium mt-1 ${color}`}>{value !== null ? fmt(value) : "—"}</p>
    </div>
  );
}
