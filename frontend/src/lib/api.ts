import type {
  Product, PriceComparison, Brand, Purchase, PurchaseInput,
  Score, PurchaseStats, WatchListItem, Drop, Channel,
  SaleHighlight, ChannelHighlight, BrandHighlight, ChannelPriceHistory,
  SaleFilters,
  AdminStats, AdminChannelHealth,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  if (res.status === 204) return undefined as T;
  return res.json();
}

async function adminFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers ?? {});
  headers.set("Content-Type", "application/json");
  headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers,
  });
  if (!res.ok) throw new Error(`ADMIN API ${res.status}: ${path}`);
  return res.json();
}

// ── Products ──────────────────────────────────────────────────────────────
export const getSaleProducts = (limit = 50, brand?: string) =>
  apiFetch<Product[]>(`/products/sales?limit=${limit}${brand ? `&brand=${brand}` : ""}`);

export const searchProducts = (q: string) =>
  apiFetch<Product[]>(`/products/search?q=${encodeURIComponent(q)}&limit=20`);
export const getRelatedSearches = (q: string, limit = 8) =>
  apiFetch<string[]>(
    `/products/related-searches?q=${encodeURIComponent(q)}&limit=${limit}`
  );

export const getPriceComparison = (productKey: string) =>
  apiFetch<PriceComparison>(`/products/compare/${encodeURIComponent(productKey)}`);
const salesFilterQuery = (filters?: SaleFilters) => {
  const params = new URLSearchParams();
  if (filters?.gender) params.set("gender", filters.gender);
  if (filters?.category) params.set("category", filters.category);
  if (typeof filters?.min_price === "number") params.set("min_price", String(filters.min_price));
  if (typeof filters?.max_price === "number") params.set("max_price", String(filters.max_price));
  const str = params.toString();
  return str ? `&${str}` : "";
};
export const getSaleHighlights = (limit = 120, offset = 0, filters?: SaleFilters) =>
  apiFetch<SaleHighlight[]>(
    `/products/sales-highlights?limit=${limit}&offset=${offset}${salesFilterQuery(filters)}`
  );
export const getSaleCount = (filters?: SaleFilters) =>
  apiFetch<{ total: number }>(
    (() => {
      const q = salesFilterQuery(filters).replace(/^&/, "");
      return q ? `/products/sales-count?${q}` : "/products/sales-count";
    })()
  );
export const getPriceHistory = (productKey: string, days = 30) =>
  apiFetch<ChannelPriceHistory[]>(
    `/products/price-history/${encodeURIComponent(productKey)}?days=${days}`
  );

// ── Brands ────────────────────────────────────────────────────────────────
export const getBrands = () => apiFetch<Brand[]>("/brands/");
export const searchBrands = (q: string) =>
  apiFetch<Brand[]>(`/brands/search?q=${encodeURIComponent(q)}`);
export const getBrandHighlights = (limit = 300, offset = 0) =>
  apiFetch<BrandHighlight[]>(`/brands/highlights?limit=${limit}&offset=${offset}`);
export const getBrand = (slug: string) =>
  apiFetch<Brand>(`/brands/${encodeURIComponent(slug)}`);
export const getBrandChannels = (slug: string) =>
  apiFetch<Channel[]>(`/brands/${encodeURIComponent(slug)}/channels`);
export const getBrandProducts = (slug: string, isSale?: boolean, limit = 500) =>
  apiFetch<Product[]>(
    `/brands/${encodeURIComponent(slug)}/products?limit=${limit}${isSale ? "&is_sale=true" : ""}`
  );

// ── Channels ──────────────────────────────────────────────────────────────
export const getChannels = () => apiFetch<Channel[]>("/channels/");
export const getChannelHighlights = (limit = 200, offset = 0) =>
  apiFetch<ChannelHighlight[]>(`/channels/highlights?limit=${limit}&offset=${offset}`);

// ── Watchlist ─────────────────────────────────────────────────────────────
export const getWatchlist = () => apiFetch<WatchListItem[]>("/watchlist/");

export const addWatchlistItem = (data: { watch_type: string; watch_value: string; notes?: string }) =>
  apiFetch<WatchListItem>("/watchlist/", { method: "POST", body: JSON.stringify(data) });

export const deleteWatchlistItem = (id: number) =>
  apiFetch<void>(`/watchlist/${id}`, { method: "DELETE" });

// ── Purchases ─────────────────────────────────────────────────────────────
export const getPurchases = (limit = 50) =>
  apiFetch<Purchase[]>(`/purchases/?limit=${limit}`);

export const getPurchaseStats = () => apiFetch<PurchaseStats>("/purchases/stats");

export const createPurchase = (data: PurchaseInput) =>
  apiFetch<Purchase>("/purchases/", { method: "POST", body: JSON.stringify(data) });

export const getPurchaseScore = (id: number) =>
  apiFetch<Score>(`/purchases/${id}/score`);

export const deletePurchase = (id: number) =>
  apiFetch<void>(`/purchases/${id}`, { method: "DELETE" });

// ── Drops ─────────────────────────────────────────────────────────────────
export const getUpcomingDrops = () => apiFetch<Drop[]>("/drops/upcoming");
export const getDrops = (status?: string) =>
  apiFetch<Drop[]>(`/drops/${status ? `?status=${status}` : ""}`);

// ── Admin ────────────────────────────────────────────────────────────────
export const getAdminStats = (token: string) =>
  adminFetch<AdminStats>("/admin/stats", token);

export const getAdminChannelsHealth = (token: string, limit = 200, offset = 0) =>
  adminFetch<AdminChannelHealth[]>(
    `/admin/channels-health?limit=${limit}&offset=${offset}`,
    token
  );

export const triggerAdminCrawl = (token: string, job: "brands" | "products" | "drops", dryRun = false) =>
  adminFetch<{ ok: boolean; pid?: number; command: string; job: string }>(
    `/admin/crawl-trigger?job=${job}&dry_run=${dryRun ? "true" : "false"}`,
    token,
    { method: "POST" }
  );
