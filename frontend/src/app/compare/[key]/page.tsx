import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPriceComparison } from "@/lib/api";
import { ComparePageClient } from "./ComparePageClient";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export async function generateMetadata(
  { params }: { params: Promise<{ key: string }> },
): Promise<Metadata> {
  const { key } = await params;
  const decodedKey = decodeURIComponent(key);
  try {
    const data = await getPriceComparison(decodedKey);
    const minPriceText = data.cheapest_price_krw != null
      ? `${data.cheapest_price_krw.toLocaleString("ko-KR")}원`
      : "가격 확인";
    return {
      title: `${data.product_name} 최저가 비교 | 패션 다나와`,
      description: `${data.brand_name ? `${data.brand_name} ` : ""}${data.product_name} · ${data.total_listings}개 채널 최저가 ${minPriceText}`,
      openGraph: {
        title: `${data.product_name} 최저가 비교 | 패션 다나와`,
        description: `${data.total_listings}개 채널 실시간 가격 비교`,
        url: `${SITE_URL}/compare/${encodeURIComponent(decodedKey)}`,
        images: data.image_url ? [{ url: data.image_url }] : undefined,
      },
    };
  } catch {
    return {
      title: "가격 비교 | 패션 다나와",
      description: "패션 제품 최저가 비교",
    };
  }
}

export default async function ComparePage(
  { params }: { params: Promise<{ key: string }> },
) {
  const { key } = await params;
  const decodedKey = decodeURIComponent(key);
  const data = await getPriceComparison(decodedKey).catch(() => null);
  if (!data) {
    notFound();
  }
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: data.product_name,
    image: data.image_url ? [data.image_url] : undefined,
    brand: data.brand_name ? { "@type": "Brand", name: data.brand_name } : undefined,
    offers: data.listings.map((listing) => ({
      "@type": "Offer",
      priceCurrency: "KRW",
      price: listing.price_krw,
      url: listing.product_url,
      seller: {
        "@type": "Organization",
        name: listing.channel_name,
      },
      availability: "https://schema.org/InStock",
    })),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <ComparePageClient initialData={data} />
    </>
  );
}
