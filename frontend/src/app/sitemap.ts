import type { MetadataRoute } from "next";
import { getBrands, getProductKeys } from "@/lib/api";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [brands, productKeys] = await Promise.all([
    getBrands().catch(() => []),
    getProductKeys().catch(() => []),
  ]);

  const staticRoutes = [
    "",
    "/sales",
    "/brands",
    "/channels",
    "/ranking",
    "/compete",
    "/drops",
    "/drops/calendar",
    "/watchlist",
    "/brands/heatmap",
  ].map((path) => ({
    url: `${SITE_URL}${path}`,
    lastModified: new Date(),
    changeFrequency: "daily" as const,
    priority: path === "" ? 1 : 0.8,
  }));

  const brandRoutes = brands.map((brand) => ({
    url: `${SITE_URL}/brands/${encodeURIComponent(brand.slug)}`,
    lastModified: new Date(),
    changeFrequency: "daily" as const,
    priority: 0.7,
  }));

  const compareRoutes = productKeys.map((item) => ({
    url: `${SITE_URL}/compare/${encodeURIComponent(item.product_key)}`,
    lastModified: new Date(),
    changeFrequency: "daily" as const,
    priority: 0.6,
  }));

  return [...staticRoutes, ...brandRoutes, ...compareRoutes];
}
