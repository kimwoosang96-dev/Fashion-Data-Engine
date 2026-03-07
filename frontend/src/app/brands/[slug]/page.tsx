import type { Metadata } from "next";
import { getBrand } from "@/lib/api";
import { BrandDetailClient } from "./BrandDetailClient";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export async function generateMetadata(
  { params }: { params: Promise<{ slug: string }> },
): Promise<Metadata> {
  const { slug } = await params;
  const decodedSlug = decodeURIComponent(slug);
  try {
    const brand = await getBrand(decodedSlug);
    return {
      title: `${brand.name} 브랜드 세일 | 패션 다나와`,
      description: `${brand.name} 브랜드 세일 제품과 취급 채널, 협업, 브랜드 소식을 한 번에 확인합니다.`,
      openGraph: {
        title: `${brand.name} 브랜드 세일 | 패션 다나와`,
        description: `${brand.name} 브랜드 세일 제품과 브랜드 개요`,
        url: `${SITE_URL}/brands/${encodeURIComponent(decodedSlug)}`,
      },
    };
  } catch {
    return {
      title: "브랜드 상세 | 패션 다나와",
      description: "브랜드 세일과 채널 정보를 확인합니다.",
    };
  }
}

export default async function BrandDetailPage(
  { params }: { params: Promise<{ slug: string }> },
) {
  const { slug } = await params;
  return <BrandDetailClient slug={decodeURIComponent(slug)} />;
}
