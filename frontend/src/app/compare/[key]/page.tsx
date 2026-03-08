import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getProductAvailability } from "@/lib/api";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

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
    return {
      title: `${data.product_name} 최저가 비교 | 패션 다나와`,
      description: `${data.brand_name ? `${data.brand_name} ` : ""}${data.product_name} · ${data.channels.length}개 채널 최저가 ${minPriceText}`,
      openGraph: {
        title: `${data.product_name} 최저가 비교 | 패션 다나와`,
        description: `${data.channels.length}개 채널 실시간 가격 비교`,
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
  redirect(`/product/${encodeURIComponent(decodedKey)}`);
}
