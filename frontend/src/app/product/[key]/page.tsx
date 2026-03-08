import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getBrandProducts, getCrossChannelPriceHistory, getProductAvailability } from "@/lib/api";
import { ProductPageClient } from "./ProductPageClient";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
export const revalidate = 180;

export async function generateStaticParams() {
  const { getProductKeys } = await import("@/lib/api");
  const rows = await getProductKeys(120).catch(() => []);
  return rows.map((item) => ({ key: item.product_key }));
}

export async function generateMetadata(
  { params }: { params: Promise<{ key: string }> },
): Promise<Metadata> {
  const { key } = await params;
  const decodedKey = decodeURIComponent(key);
  try {
    const data = await getProductAvailability(decodedKey);
    const minPriceText = data.lowest_price?.price_krw != null
      ? `${data.lowest_price.price_krw.toLocaleString("ko-KR")}원`
      : "가격 확인";
    const ogUrl = new URL("/api/og", SITE_URL);
    ogUrl.searchParams.set("name", data.product_name);
    ogUrl.searchParams.set("price", minPriceText);
    if (data.brand_name) ogUrl.searchParams.set("brand", data.brand_name);
    return {
      title: `${data.product_name} | 채널별 최저가`,
      description: `${data.in_stock_anywhere ? "재고 있음" : "품절"} · ${data.channels.length}개 채널 비교 · 최저가 ${minPriceText}`,
      openGraph: {
        title: `${data.product_name} | 채널별 최저가`,
        description: `${data.brand_name ? `${data.brand_name} · ` : ""}${data.channels.length}개 채널 실시간 비교`,
        url: `${SITE_URL}/product/${encodeURIComponent(decodedKey)}`,
        images: [{ url: ogUrl.toString() }],
      },
    };
  } catch {
    return {
      title: "제품 상세 | Fashion Data Engine",
      description: "제품별 채널 가격과 재고 현황",
    };
  }
}

export default async function ProductPage(
  { params }: { params: Promise<{ key: string }> },
) {
  const { key } = await params;
  const decodedKey = decodeURIComponent(key);
  const availability = await getProductAvailability(decodedKey).catch(() => null);
  if (!availability) {
    notFound();
  }

  const [priceHistory, relatedProducts] = await Promise.all([
    getCrossChannelPriceHistory(decodedKey, 90).catch(() => null),
    availability.brand_slug
      ? getBrandProducts(availability.brand_slug, true, 8)
          .then((rows) => rows.filter((row) => row.product_key !== availability.product_key).slice(0, 4))
          .catch(() => [])
      : Promise.resolve([]),
  ]);

  return (
    <ProductPageClient
      availability={availability}
      priceHistory={priceHistory}
      relatedProducts={relatedProducts}
    />
  );
}
