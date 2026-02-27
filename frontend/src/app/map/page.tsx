"use client";

import { useEffect, useMemo, useState } from "react";
import { ComposableMap, Geographies, Geography, Marker } from "react-simple-maps";
import { getChannelHighlights } from "@/lib/api";
import type { ChannelHighlight } from "@/lib/types";

const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

const COUNTRY_COORDS: Record<string, [number, number]> = {
  KR: [127.8, 36.2],
  JP: [138.2, 36.6],
  US: [-98.5, 39.8],
  GB: [-1.5, 52.6],
  DE: [10.4, 51.2],
  FR: [2.2, 46.4],
  IT: [12.6, 42.8],
  ES: [-3.7, 40.4],
  NL: [5.4, 52.1],
  DK: [10.0, 56.2],
  SE: [15.1, 62.0],
  HK: [114.2, 22.3],
  SG: [103.8, 1.3],
  CA: [-106.3, 56.1],
  TW: [121.0, 23.7],
  CN: [103.8, 35.9],
  AU: [134.5, -25.7],
};

export default function MapPage() {
  const [channels, setChannels] = useState<ChannelHighlight[]>([]);
  const [selectedCode, setSelectedCode] = useState<string>("");

  useEffect(() => {
    getChannelHighlights(500, 0).then(setChannels).catch(() => setChannels([]));
  }, []);

  const markers = useMemo(() => {
    const byCountry: Record<string, ChannelHighlight[]> = {};
    channels.forEach((c) => {
      const code = (c.country || "").toUpperCase();
      if (!code || !COUNTRY_COORDS[code]) return;
      byCountry[code] = byCountry[code] || [];
      byCountry[code].push(c);
    });
    return Object.entries(byCountry).map(([code, list]) => ({
      code,
      coords: COUNTRY_COORDS[code],
      channelCount: list.length,
      saleCount: list.filter((c) => c.is_running_sales).length,
      channels: list,
    }));
  }, [channels]);

  const selected = markers.find((m) => m.code === selectedCode) ?? null;

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold">세계지도</h1>
        <p className="text-sm text-gray-500 mt-1">국가별 채널 분포 / 세일 채널 강조</p>
      </div>
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-4">
        <div className="bg-white border border-gray-200 rounded-xl p-3">
          <ComposableMap projectionConfig={{ scale: 145 }}>
            <Geographies geography={GEO_URL}>
              {({ geographies }) =>
                geographies.map((geo) => (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill="#eef2f7"
                    stroke="#d1d5db"
                    strokeWidth={0.4}
                  />
                ))
              }
            </Geographies>
            {markers.map((m) => {
              const isSaleCountry = m.saleCount > 0;
              const active = selectedCode === m.code;
              return (
                <Marker key={m.code} coordinates={m.coords} onClick={() => setSelectedCode(m.code)}>
                  <circle
                    r={active ? 10 : 8}
                    fill={isSaleCountry ? "#dc2626" : "#2563eb"}
                    opacity={0.85}
                    stroke="#fff"
                    strokeWidth={1.5}
                  />
                  <text y={-14} textAnchor="middle" className="fill-gray-700 text-[10px] font-medium">
                    {m.code}
                  </text>
                </Marker>
              );
            })}
          </ComposableMap>
        </div>
        <aside className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
          <h2 className="text-base font-semibold">국가 상세</h2>
          {!selected ? (
            <p className="text-sm text-gray-500">지도의 마커를 클릭하면 채널 목록이 표시됩니다.</p>
          ) : (
            <>
              <div className="text-sm">
                <p className="font-medium">{selected.code}</p>
                <p className="text-gray-500">채널 {selected.channelCount}개 · 세일 채널 {selected.saleCount}개</p>
              </div>
              <div className="max-h-[520px] overflow-auto space-y-2">
                {selected.channels.map((ch) => (
                  <div key={ch.channel_id} className="border border-gray-100 rounded-md p-2">
                    <p className="text-sm font-medium">{ch.channel_name}</p>
                    <p className="text-xs text-gray-500">{ch.channel_type ?? "-"}</p>
                    <div className="mt-1 flex gap-1.5">
                      {ch.is_running_sales && (
                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-red-100 text-red-700">
                          세일
                        </span>
                      )}
                      {ch.is_selling_new_products && (
                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">
                          NEW
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
