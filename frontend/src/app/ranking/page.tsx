"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { getBrandRanking, getProductRanking } from "@/lib/api";
import type { BrandRankingItem, ProductRankingItem } from "@/lib/types";

type RankingTab = "sale_hot" | "price_drop" | "brand";

function fmt(value: number) {
  return `₩${value.toLocaleString("ko-KR")}`;
}

function formatSaleStart(hours: number | null) {
  if (hours == null) return null;
  if (hours < 1) return "1시간 이내 세일 시작";
  if (hours < 24) return `${Math.floor(hours)}시간 전 세일 시작`;
  return `${Math.floor(hours / 24)}일 전 세일 시작`;
}

export default function RankingPage() {
  const [tab, setTab] = useState<RankingTab>("sale_hot");
  const [saleHot, setSaleHot] = useState<ProductRankingItem[]>([]);
  const [priceDrop, setPriceDrop] = useState<ProductRankingItem[]>([]);
  const [brands, setBrands] = useState<BrandRankingItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getProductRanking("sale_hot", 100),
      getProductRanking("price_drop", 50),
      getBrandRanking(50),
    ])
      .then(([saleHotRes, priceDropRes, brandRes]) => {
        setSaleHot(saleHotRes);
        setPriceDrop(priceDropRes);
        setBrands(brandRes);
      })
      .finally(() => setLoading(false));
  }, []);

  const current = useMemo(() => {
    if (tab === "sale_hot") return saleHot;
    if (tab === "price_drop") return priceDrop;
    return brands;
  }, [brands, priceDrop, saleHot, tab]);

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">랭킹</h1>
        <p className="mt-1 text-sm text-gray-500">할인율보다 지금의 정보 가치가 높은 상품과 브랜드를 우선 보여줍니다.</p>
      </div>

      <div className="flex flex-wrap gap-2">
        <TabButton active={tab === "sale_hot"} onClick={() => setTab("sale_hot")}>세일 HOT</TabButton>
        <TabButton active={tab === "price_drop"} onClick={() => setTab("price_drop")}>가격 급락</TabButton>
        <TabButton active={tab === "brand"} onClick={() => setTab("brand")}>브랜드 랭킹</TabButton>
      </div>

      {loading ? (
        <p className="text-sm text-gray-400">랭킹을 불러오는 중...</p>
      ) : tab === "brand" ? (
        <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 bg-gray-50 text-gray-500">
              <tr>
                <th className="px-4 py-3 text-left font-medium">순위</th>
                <th className="px-4 py-3 text-left font-medium">브랜드</th>
                <th className="px-4 py-3 text-right font-medium">72h 이벤트</th>
                <th className="px-4 py-3 text-right font-medium">세일 제품</th>
                <th className="px-4 py-3 text-right font-medium">평균 할인율</th>
                <th className="px-4 py-3 text-right font-medium">채널 수</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(current as BrandRankingItem[]).map((item, index) => (
                <tr key={item.brand_id}>
                  <td className="px-4 py-3 font-bold text-gray-400">{index + 1}</td>
                  <td className="px-4 py-3">
                    <Link href={`/brands/${encodeURIComponent(item.brand_slug)}`} className="font-semibold text-gray-900 hover:underline">
                      {item.brand_name}
                    </Link>
                    <p className="mt-1 text-xs text-gray-500">
                      {item.tier ?? "tier 미분류"} · {item.origin_country ?? "국가 미상"}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-red-600">{item.event_count_72h}</td>
                  <td className="px-4 py-3 text-right font-semibold">{item.sale_product_count.toLocaleString("ko-KR")}</td>
                  <td className="px-4 py-3 text-right">{item.avg_discount_rate}%</td>
                  <td className="px-4 py-3 text-right text-gray-500">{item.active_channel_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {(current as ProductRankingItem[]).map((item, index) => (
            <article key={`${tab}-${item.product_key}-${item.channel_name}-${index}`} className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
              {item.image_url && (
                <div className="relative h-48 w-full bg-gray-100">
                  <Image
                    src={item.image_url}
                    alt={item.product_name}
                    fill
                    className="object-cover"
                    sizes="(max-width: 768px) 100vw, (max-width: 1280px) 50vw, 33vw"
                    unoptimized
                  />
                  <div className="absolute left-3 top-3 rounded-full bg-gray-900/80 px-2.5 py-1 text-xs font-semibold text-white backdrop-blur-sm">
                    {tab === "sale_hot"
                      ? `${item.discount_rate ?? 0}% OFF`
                      : `${item.price_drop_pct ?? 0}% DROP`}
                  </div>
                  <div className="absolute right-3 top-3 rounded-full bg-white/90 px-2 py-0.5 text-xs font-bold text-gray-500 backdrop-blur-sm">
                    #{index + 1}
                  </div>
                </div>
              )}
              <div className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  {!item.image_url && <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-300">Rank {index + 1}</p>}
                  <p className="mt-2 line-clamp-2 text-base font-semibold text-gray-900">{item.product_name}</p>
                  <p className="mt-1 text-sm text-gray-500">
                    {item.brand_name ? `${item.brand_name} · ` : ""}
                    {item.channel_name}
                  </p>
                </div>
                {!item.image_url && (
                  <div className="rounded-full bg-gray-900 px-2.5 py-1 text-xs font-semibold text-white">
                    {tab === "sale_hot"
                      ? `${item.discount_rate ?? 0}% OFF`
                      : `${item.price_drop_pct ?? 0}% DROP`}
                  </div>
                )}
              </div>
              <div className="mt-4 flex items-end gap-2">
                <span className="text-2xl font-bold text-gray-900">{fmt(item.price_krw)}</span>
                {item.original_price_krw && (
                  <span className="text-xs text-gray-400 line-through">{fmt(item.original_price_krw)}</span>
                )}
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-500">
                {item.badges.map((badge) => (
                  <span key={badge} className="rounded-full bg-red-600 px-2 py-1 font-semibold text-white">
                    {badge}
                  </span>
                ))}
                <span className="rounded-full bg-gray-100 px-2 py-1">{item.total_channels}개 채널</span>
                {tab === "price_drop" && item.price_drop_krw != null && (
                  <span className="rounded-full bg-red-50 px-2 py-1 text-red-600">
                    {fmt(item.price_drop_krw)} 하락
                  </span>
                )}
              </div>
              {tab === "sale_hot" && item.hours_since_sale_start != null && (
                <p className="mt-3 text-xs font-medium text-red-600">
                  {formatSaleStart(item.hours_since_sale_start)}
                </p>
              )}
              <div className="mt-4 flex items-center justify-between text-sm">
                <span className="text-gray-400">{item.channel_country ?? "국가 미상"}</span>
                {item.product_key ? (
                  <Link href={`/product/${encodeURIComponent(item.product_key)}`} className="font-medium text-blue-600 hover:underline">
                    비교 보기
                  </Link>
                ) : (
                  <a href={item.product_url} target="_blank" rel="noreferrer" className="font-medium text-blue-600 hover:underline">
                    상품 보기
                  </a>
                )}
              </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-4 py-2 text-sm font-medium ${
        active
          ? "bg-gray-900 text-white"
          : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
      }`}
    >
      {children}
    </button>
  );
}
