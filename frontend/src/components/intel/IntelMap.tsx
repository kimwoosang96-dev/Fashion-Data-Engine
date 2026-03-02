"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { IntelMapPoint } from "@/lib/types";

type IntelMapProps = {
  points: IntelMapPoint[];
  selectedId?: number | null;
  onSelect?: (eventId: number) => void;
  className?: string;
};

type ClusterPoint = IntelMapPoint & { count?: number; ids?: number[] };

const clusterPoints = (points: IntelMapPoint[]): ClusterPoint[] => {
  const groups = new Map<string, ClusterPoint>();
  for (const p of points) {
    const key = `${p.layer}:${p.lat.toFixed(1)}:${p.lng.toFixed(1)}`;
    const g = groups.get(key);
    if (g) {
      g.count = (g.count ?? 1) + 1;
      g.ids = [...(g.ids ?? [g.id]), p.id];
      continue;
    }
    groups.set(key, { ...p, count: 1, ids: [p.id] });
  }
  return Array.from(groups.values());
};

export function IntelMap({ points, selectedId, onSelect, className }: IntelMapProps) {
  const styleUrl =
    process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? "https://demotiles.maplibre.org/style.json";
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker[]>([]);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [ready, setReady] = useState(false);
  const clustered = useMemo(() => clusterPoints(points), [points]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    mapRef.current = new maplibregl.Map({
      container: containerRef.current,
      style: styleUrl,
      center: [127, 20],
      zoom: 1.2,
    });
    mapRef.current.addControl(new maplibregl.NavigationControl(), "top-right");
    mapRef.current.on("load", () => setReady(true));

    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [styleUrl]);

  useEffect(() => {
    if (!mapRef.current || !ready) return;
    markerRef.current.forEach((m) => m.remove());
    markerRef.current = [];

    for (const p of clustered) {
      const el = document.createElement("button");
      const count = p.count ?? 1;
      el.className =
        "h-7 min-w-7 px-1 rounded-full border border-white shadow text-[11px] font-semibold";
      el.style.background = p.id === selectedId ? "#111827" : "#ef4444";
      el.style.color = "white";
      el.textContent = count > 1 ? String(count) : "•";
      el.title = p.title;
      el.onclick = () => onSelect?.(p.id);
      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([p.lng, p.lat])
        .addTo(mapRef.current!);
      markerRef.current.push(marker);
    }
  }, [clustered, selectedId, onSelect, ready]);

  useEffect(() => {
    if (!mapRef.current || !selectedId) return;
    const p = points.find((x) => x.id === selectedId);
    if (!p) return;
    mapRef.current.flyTo({ center: [p.lng, p.lat], zoom: Math.max(2.5, mapRef.current.getZoom()) });
  }, [points, selectedId]);

  return (
    <div className={className ?? "w-full min-h-[420px] rounded-xl border border-gray-200 overflow-hidden"}>
      <div ref={containerRef} className="w-full h-[420px] bg-gray-100" />
    </div>
  );
}
