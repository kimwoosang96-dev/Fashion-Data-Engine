"use client";

import { useEffect, useMemo, useState } from "react";
import { getCollabHypeByCategory, getCollabs } from "@/lib/api";
import type { CollabItem } from "@/lib/types";

const CATEGORIES = [
  { label: "전체", value: "" },
  { label: "신발", value: "footwear" },
  { label: "의류", value: "apparel" },
  { label: "액세서리", value: "accessories" },
  { label: "라이프스타일", value: "lifestyle" },
];

export default function CollabsPage() {
  const [items, setItems] = useState<CollabItem[]>([]);
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(true);
  const [hypeSummary, setHypeSummary] = useState<
    Array<{ category: string; count: number; avg_hype: number; max_hype: number }>
  >([]);

  useEffect(() => {
    setLoading(true);
    Promise.all([getCollabs(category || undefined), getCollabHypeByCategory()])
      .then(([collabs, summary]) => {
        setItems(collabs);
        setHypeSummary(summary);
      })
      .finally(() => setLoading(false));
  }, [category]);

  const timeline = useMemo(() => {
    return [...items].sort((a, b) => {
      const ay = a.release_year ?? 0;
      const by = b.release_year ?? 0;
      if (ay !== by) return by - ay;
      return b.hype_score - a.hype_score;
    });
  }, [items]);

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold">협업 타임라인</h1>
        <p className="text-sm text-gray-500 mt-1">브랜드 협업 이력과 하입 점수</p>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map((c) => (
            <button
              key={c.value || "all"}
              type="button"
              onClick={() => setCategory(c.value)}
              className={`text-xs px-3 py-1.5 rounded-full border ${
                category === c.value
                  ? "bg-gray-900 text-white border-gray-900"
                  : "bg-white text-gray-600 border-gray-200"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          {hypeSummary.map((s) => (
            <span key={s.category} className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-700">
              {s.category}: 평균 {s.avg_hype} / 최고 {s.max_hype} ({s.count}건)
            </span>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-gray-400">로딩 중...</p>
      ) : timeline.length === 0 ? (
        <p className="text-sm text-gray-400">협업 데이터가 없습니다.</p>
      ) : (
        <div className="space-y-3">
          {timeline.map((item) => (
            <article key={item.id} className="bg-white border border-gray-200 rounded-xl p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold">{item.collab_name}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {item.release_year ?? "연도 미상"} · {item.collab_category ?? "카테고리 미분류"}
                  </p>
                </div>
                <span className="text-xs px-2 py-1 rounded-full bg-red-100 text-red-700 font-medium">
                  HYPE {item.hype_score}
                </span>
              </div>
              {item.notes && <p className="text-sm text-gray-600 mt-2">{item.notes}</p>}
              {item.source_url && (
                <a
                  href={item.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-block mt-2 text-xs text-blue-600 hover:underline"
                >
                  출처 보기
                </a>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
