"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { getBrand, getBrandChannels, getBrandNews, getBrandProducts } from "@/lib/api";
import type { Brand, Channel, FashionNews, Product } from "@/lib/types";
import { ProductCard } from "@/components/ProductCard";

export default function BrandDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [brand, setBrand] = useState<Brand | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [news, setNews] = useState<FashionNews[]>([]);
  const [saleOnly, setSaleOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const decoded = decodeURIComponent(slug);
        const [brandRes, channelsRes, productsRes] = await Promise.all([
          getBrand(decoded),
          getBrandChannels(decoded),
          getBrandProducts(decoded, false, 500),
        ]);
        setBrand(brandRes);
        setChannels(channelsRes);
        setProducts(productsRes);
        const newsRes = await getBrandNews(decoded, 20);
        setNews(newsRes);
      } catch (e) {
        setError(e instanceof Error ? e.message : "브랜드 데이터를 불러오지 못했습니다.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [slug]);

  useEffect(() => {
    if (!brand) return;
    const loadProducts = async () => {
      try {
        const result = await getBrandProducts(brand.slug, saleOnly, 500);
        setProducts(result);
      } catch (e) {
        setError(e instanceof Error ? e.message : "제품 목록을 불러오지 못했습니다.");
      }
    };
    void loadProducts();
  }, [saleOnly, brand]);

  const saleCount = useMemo(() => products.filter((p) => p.is_sale).length, [products]);

  if (loading) return <div className="p-6 text-sm text-gray-400">로딩 중...</div>;
  if (error || !brand) return <div className="p-6 text-sm text-red-500">{error ?? "브랜드를 찾을 수 없습니다."}</div>;

  return (
    <div className="p-6 space-y-6">
      <div>
        <Link href="/brands" className="text-xs text-gray-400 hover:text-gray-600">← 브랜드 목록</Link>
        <h1 className="text-2xl font-bold mt-1">{brand.name}</h1>
        <div className="mt-2 flex flex-wrap gap-2 text-xs">
          <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">{brand.slug}</span>
          <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">{brand.tier ?? "tier 미분류"}</span>
          <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">{brand.origin_country ?? "국가 미상"}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <StatCard label="총 제품 수" value={products.length} />
        <StatCard label="세일 제품 수" value={saleCount} />
        <StatCard label="취급 채널 수" value={channels.length} />
      </div>

      <div className="flex items-center gap-2">
        <label className="inline-flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={saleOnly}
            onChange={(e) => setSaleOnly(e.target.checked)}
          />
          세일 제품만 보기
        </label>
      </div>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">브랜드 소식</h2>
          <Link href="/collabs" className="text-xs text-gray-500 hover:underline">
            협업 타임라인 보기
          </Link>
        </div>
        {news.length === 0 ? (
          <p className="text-sm text-gray-400">등록된 브랜드 소식이 없습니다.</p>
        ) : (
          <div className="space-y-2">
            {news.slice(0, 8).map((item) => (
              <a
                key={item.id}
                href={item.url}
                target="_blank"
                rel="noreferrer"
                className="block rounded-lg border border-gray-200 bg-white p-3 hover:bg-gray-50"
              >
                <p className="text-sm font-medium">{item.title}</p>
                <p className="text-xs text-gray-500 mt-1">
                  {item.source}
                  {item.published_at ? ` · ${item.published_at.slice(0, 10)}` : ""}
                </p>
              </a>
            ))}
          </div>
        )}
      </section>

      {products.length === 0 ? (
        <p className="text-sm text-gray-400">표시할 제품이 없습니다.</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {products.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900">{value.toLocaleString("ko-KR")}</p>
    </div>
  );
}
