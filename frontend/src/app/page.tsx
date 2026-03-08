import { getActivityFeed, getAdminIntelStatus, getBrands, getChannels, getSaleHighlights } from "@/lib/api";
import { HomePageClient } from "./HomePageClient";

export default async function HomePage() {
  const adminToken = process.env.ADMIN_BEARER_TOKEN;
  const [initialSaleHighlights, initialDrops, channels, brands, stats] = await Promise.all([
    getSaleHighlights(12, 0).catch(() => []),
    getActivityFeed({ event_type: "new_drop", limit: 8, offset: 0 }).catch(() => []),
    getChannels().catch(() => []),
    getBrands().catch(() => []),
    adminToken ? getAdminIntelStatus(adminToken).catch(() => null) : Promise.resolve(null),
  ]);

  return (
    <HomePageClient
      initialSaleHighlights={initialSaleHighlights}
      initialDrops={initialDrops}
      channels={channels}
      brands={brands}
      stats={stats}
    />
  );
}
