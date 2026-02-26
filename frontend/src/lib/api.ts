import type {
  Product, PriceComparison, Brand, Purchase, PurchaseInput,
  Score, PurchaseStats, WatchListItem, Drop, Channel,
  SaleHighlight, ChannelHighlight, BrandHighlight, ChannelPriceHistory,
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
export const getSaleHighlights = (limit = 120, offset = 0) =>
  apiFetch<SaleHighlight[]>(`/products/sales-highlights?limit=${limit}&offset=${offset}`);
export const getSaleCount = () =>
  apiFetch<{ total: number }>("/products/sales-count");
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
