"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getDropsCalendar } from "@/lib/api";
import type { DropsCalendarEntry } from "@/lib/types";

function eventTone(type: string) {
  switch (type) {
    case "sale_start":
      return "bg-red-100 text-red-700";
    case "new_drop":
    case "drop":
      return "bg-blue-100 text-blue-700";
    case "price_cut":
      return "bg-amber-100 text-amber-700";
    default:
      return "bg-gray-100 text-gray-700";
  }
}

function formatExpected(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function DropsCalendarPage() {
  const today = new Date();
  const [cursor, setCursor] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1));
  const [data, setData] = useState<Record<string, DropsCalendarEntry[]>>({});
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getDropsCalendar(cursor.getFullYear(), cursor.getMonth() + 1)
      .then((rows) => {
        setData(rows);
        const firstKey = Object.keys(rows)[0] ?? null;
        setSelectedDate(firstKey);
      })
      .finally(() => setLoading(false));
  }, [cursor]);

  const monthLabel = `${cursor.getFullYear()}년 ${cursor.getMonth() + 1}월`;
  const calendar = useMemo(() => {
    const firstDay = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
    const firstWeekday = firstDay.getDay();
    const daysInMonth = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0).getDate();
    const cells: Array<{ date: string | null; day: number | null }> = [];
    for (let i = 0; i < firstWeekday; i += 1) cells.push({ date: null, day: null });
    for (let day = 1; day <= daysInMonth; day += 1) {
      const date = new Date(cursor.getFullYear(), cursor.getMonth(), day).toISOString().slice(0, 10);
      cells.push({ date, day });
    }
    while (cells.length % 7 !== 0) cells.push({ date: null, day: null });
    return cells;
  }, [cursor]);

  const selectedItems = selectedDate ? data[selectedDate] ?? [] : [];

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">드롭 캘린더</h1>
          <p className="mt-1 text-sm text-gray-500">드롭과 세일 일정을 날짜 기준으로 확인합니다.</p>
        </div>
        <Link href="/drops" className="text-sm font-medium text-blue-600 hover:underline">
          드롭 카드 보기
        </Link>
      </div>

      <div className="flex items-center justify-between rounded-2xl border border-gray-200 bg-white px-4 py-3">
        <button
          type="button"
          onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
        >
          ← 이전 달
        </button>
        <p className="text-lg font-semibold text-gray-900">{monthLabel}</p>
        <button
          type="button"
          onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
        >
          다음 달 →
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-gray-400">캘린더 로딩 중...</p>
      ) : (
        <>
          <div className="hidden gap-4 lg:grid lg:grid-cols-[minmax(0,1fr)_320px]">
            <section className="rounded-2xl border border-gray-200 bg-white p-4">
              <div className="mb-3 grid grid-cols-7 gap-2 text-center text-xs font-semibold text-gray-400">
                {["일", "월", "화", "수", "목", "금", "토"].map((day) => (
                  <div key={day}>{day}</div>
                ))}
              </div>
              <div className="grid grid-cols-7 gap-2">
                {calendar.map((cell, index) => {
                  const items = cell.date ? data[cell.date] ?? [] : [];
                  const isSelected = cell.date === selectedDate;
                  return (
                    <button
                      key={cell.date ?? `empty-${index}`}
                      type="button"
                      disabled={!cell.date}
                      onClick={() => cell.date && setSelectedDate(cell.date)}
                      className={`min-h-28 rounded-xl border p-2 text-left align-top ${
                        cell.date
                          ? isSelected
                            ? "border-gray-900 bg-gray-50"
                            : "border-gray-200 hover:border-gray-300"
                          : "border-transparent bg-transparent"
                      }`}
                    >
                      {cell.day && (
                        <>
                          <p className="text-sm font-semibold text-gray-900">{cell.day}</p>
                          <div className="mt-2 space-y-1">
                            {items.slice(0, 3).map((item, itemIndex) => (
                              <div
                                key={`${cell.date}-${item.title}-${itemIndex}`}
                                className={`line-clamp-1 rounded-md px-2 py-1 text-[11px] font-medium ${eventTone(item.event_type)}`}
                              >
                                {item.brand_name ? `${item.brand_name} · ` : ""}
                                {item.title}
                              </div>
                            ))}
                            {items.length > 3 && (
                              <p className="text-[11px] text-gray-400">+{items.length - 3}개 더</p>
                            )}
                          </div>
                        </>
                      )}
                    </button>
                  );
                })}
              </div>
            </section>

            <aside className="rounded-2xl border border-gray-200 bg-white p-4">
              <h2 className="text-sm font-semibold text-gray-900">
                {selectedDate ?? "날짜 선택"}
              </h2>
              <div className="mt-3 space-y-3">
                {selectedItems.length === 0 ? (
                  <p className="text-sm text-gray-400">선택한 날짜의 이벤트가 없습니다.</p>
                ) : (
                  selectedItems.map((item, index) => (
                    <article key={`${selectedDate}-${item.title}-${index}`} className="rounded-xl border border-gray-200 p-3">
                      <div className="flex items-center gap-2">
                        <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ${eventTone(item.event_type)}`}>
                          {item.event_type}
                        </span>
                        {item.brand_name && <span className="text-xs text-gray-500">{item.brand_name}</span>}
                      </div>
                      <p className="mt-2 text-sm font-medium text-gray-900">{item.title}</p>
                      {formatExpected(item.expected_drop_at) && (
                        <p className="mt-1 text-xs text-gray-500">예상 시각 {formatExpected(item.expected_drop_at)}</p>
                      )}
                      {item.source_url && (
                        <a href={item.source_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-xs text-blue-600 hover:underline">
                          출처 보기
                        </a>
                      )}
                    </article>
                  ))
                )}
              </div>
            </aside>
          </div>

          <div className="space-y-3 lg:hidden">
            {Object.entries(data).map(([date, items]) => (
              <section key={date} className="rounded-2xl border border-gray-200 bg-white p-4">
                <h2 className="text-sm font-semibold text-gray-900">{date}</h2>
                <div className="mt-3 space-y-2">
                  {items.map((item, index) => (
                    <div key={`${date}-${item.title}-${index}`} className="rounded-xl border border-gray-200 p-3">
                      <div className="flex items-center gap-2">
                        <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ${eventTone(item.event_type)}`}>
                          {item.event_type}
                        </span>
                        {item.brand_name && <span className="text-xs text-gray-500">{item.brand_name}</span>}
                      </div>
                      <p className="mt-2 text-sm font-medium text-gray-900">{item.title}</p>
                      {formatExpected(item.expected_drop_at) && (
                        <p className="mt-1 text-xs text-gray-500">예상 시각 {formatExpected(item.expected_drop_at)}</p>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            ))}
            {Object.keys(data).length === 0 && <p className="text-sm text-gray-400">이번 달 이벤트가 없습니다.</p>}
          </div>
        </>
      )}
    </div>
  );
}
