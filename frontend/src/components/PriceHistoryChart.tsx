"use client";

import {
  LineChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  CartesianGrid,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import type { ChannelPriceHistory } from "@/lib/types";

const COLORS = ["#0f766e", "#2563eb", "#dc2626", "#d97706", "#7c3aed", "#0891b2", "#4f46e5"];

type ChartRow = {
  date: string;
  [channel: string]: number | string | null;
};

function formatKrw(value: number) {
  return `₩${value.toLocaleString("ko-KR")}`;
}

function buildRows(series: ChannelPriceHistory[]): ChartRow[] {
  const byDate = new Map<string, ChartRow>();
  for (const channel of series) {
    for (const point of channel.history) {
      const row = byDate.get(point.date) ?? { date: point.date };
      row[channel.channel_name] = point.price_krw;
      byDate.set(point.date, row);
    }
  }
  return [...byDate.values()].sort((a, b) => String(a.date).localeCompare(String(b.date)));
}

export function PriceHistoryChart({ data }: { data: ChannelPriceHistory[] }) {
  const rows = buildRows(data);
  if (rows.length === 0) {
    return <p className="text-sm text-gray-400">표시할 가격 이력이 없습니다.</p>;
  }

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 24, bottom: 8, left: 12 }}>
          <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tick={{ fill: "#6b7280", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tickFormatter={(value: number) => `${Math.round(value / 1000)}k`}
            tick={{ fill: "#6b7280", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={56}
          />
          <Tooltip
            content={({ active, label, payload }) => {
              if (!active || !payload || payload.length === 0) return null;
              return (
                <div className="rounded-xl border border-gray-200 bg-white px-3 py-2 shadow-xl">
                  <p className="text-xs font-semibold text-gray-500">날짜 {label}</p>
                  <div className="mt-2 space-y-1">
                    {payload.map((entry) => (
                      <div key={String(entry.name)} className="flex items-center justify-between gap-3 text-xs">
                        <span className="text-gray-500">{entry.name}</span>
                        <span className="font-semibold text-gray-900">
                          {typeof entry.value === "number" ? formatKrw(entry.value) : "—"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            }}
            contentStyle={{
              borderRadius: 12,
              borderColor: "#d1d5db",
              boxShadow: "0 10px 30px rgba(15, 23, 42, 0.08)",
            }}
          />
          <Legend />
          {data.map((channel, index) => (
            <Line
              key={channel.channel_name}
              type="monotone"
              dataKey={channel.channel_name}
              stroke={COLORS[index % COLORS.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
