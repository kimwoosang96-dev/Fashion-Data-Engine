export interface Product {
  id: number;
  channel_id: number;
  brand_id: number | null;
  name: string;
  product_key: string | null;
  gender: string | null;
  subcategory: string | null;
  url: string;
  image_url: string | null;
  is_sale: boolean;
  is_active: boolean;
  archived_at?: string | null;
}

export interface MultiChannelProduct {
  product_key: string;
  product_name: string;
  image_url: string | null;
  channel_count: number;
  min_price_krw: number;
  max_price_krw: number;
  price_spread_krw: number;
  spread_rate_pct: number;
}

export interface SaleFilters {
  gender?: string;
  category?: string;
  min_price?: number;
  max_price?: number;
}

export interface PriceComparisonItem {
  channel_name: string;
  channel_country: string | null;
  channel_url: string;
  channel_type: string | null;
  is_official: boolean;
  price_krw: number;
  original_price_krw: number | null;
  is_sale: boolean;
  discount_rate: number | null;
  product_url: string;
  image_url: string | null;
}

export interface PriceComparison {
  product_key: string;
  product_name: string;
  listings: PriceComparisonItem[];
  cheapest_channel: string | null;
  cheapest_price_krw: number | null;
  total_listings: number;
}

export interface Brand {
  id: number;
  name: string;
  slug: string;
  name_ko: string | null;
  origin_country: string | null;
  official_url: string | null;
  instagram_url: string | null;
  tier: string | null;
  description_ko: string | null;
}

export interface Channel {
  id: number;
  name: string;
  url: string;
  channel_type: string | null;
  platform: string | null;
  country: string | null;
  instagram_url: string | null;
  is_active: boolean;
}

export interface Purchase {
  id: number;
  product_key: string;
  product_name: string;
  brand_slug: string | null;
  channel_name: string;
  channel_url: string | null;
  paid_price_krw: number;
  original_price_krw: number | null;
  purchased_at: string;
  notes: string | null;
  created_at: string;
}

export interface PurchaseInput {
  product_key: string;
  product_name: string;
  brand_slug?: string | null;
  channel_name: string;
  channel_url?: string | null;
  paid_price_krw: number;
  original_price_krw?: number | null;
  notes?: string | null;
}

export interface Score {
  purchase_id: number;
  product_key: string;
  product_name: string;
  paid_price_krw: number;
  grade: string;
  percentile: number | null;
  badge: string;
  min_ever_krw: number | null;
  max_ever_krw: number | null;
  avg_krw: number | null;
  data_points: number;
  savings_vs_full: number | null;
  savings_vs_avg: number | null;
  verdict: string;
}

export interface PurchaseStats {
  total_purchases: number;
  total_paid_krw: number;
  total_savings_vs_full_krw: number;
  best_deal: {
    id: number;
    product_name: string;
    paid_price_krw: number;
    original_price_krw: number;
    savings_krw: number;
    discount_rate: number;
  } | null;
}

export interface WatchListItem {
  id: number;
  watch_type: "brand" | "channel" | "product_key";
  watch_value: string;
  notes: string | null;
}

export interface Drop {
  id: number;
  brand_id: number | null;
  product_name: string;
  product_key: string | null;
  source_url: string;
  image_url: string | null;
  price_krw: number | null;
  release_date: string | null;
  status: string;
  detected_at: string;
  notified_at: string | null;
}

export interface SaleHighlight {
  product_id: number;
  product_name: string;
  product_key: string | null;
  product_url: string;
  image_url: string | null;
  channel_name: string;
  channel_country: string | null;
  is_new: boolean;
  is_active: boolean;
  price_krw: number;
  original_price_krw: number | null;
  discount_rate: number | null;
  total_channels: number;
}

export interface ChannelHighlight {
  channel_id: number;
  channel_name: string;
  channel_url: string;
  instagram_url: string | null;
  channel_type: string | null;
  country: string | null;
  total_product_count: number;
  sale_product_count: number;
  new_product_count: number;
  is_running_sales: boolean;
  is_selling_new_products: boolean;
}

export interface BrandHighlight {
  brand_id: number;
  brand_name: string;
  brand_slug: string;
  instagram_url: string | null;
  tier: string | null;
  origin_country: string | null;
  total_product_count: number;
  new_product_count: number;
  is_selling_new_products: boolean;
}

export interface PriceHistoryPoint {
  date: string;
  price_krw: number;
  is_sale: boolean;
}

export interface ChannelPriceHistory {
  channel_name: string;
  history: PriceHistoryPoint[];
}

export interface FashionNews {
  id: number;
  entity_type: "brand" | "channel";
  entity_id: number;
  entity_name: string | null;
  title: string;
  url: string;
  summary: string | null;
  published_at: string | null;
  source: string;
  crawled_at: string;
}

export interface CollabItem {
  id: number;
  brand_a_id: number;
  brand_b_id: number;
  collab_name: string;
  collab_category: string | null;
  release_year: number | null;
  hype_score: number;
  source_url: string | null;
  notes: string | null;
  created_at: string;
}

export interface BrandDirector {
  id: number;
  brand_id: number;
  brand_name: string | null;
  brand_slug: string | null;
  name: string;
  role: string;
  start_year: number | null;
  end_year: number | null;
  note: string | null;
  created_at: string;
}

export interface DirectorsByBrand {
  brand_slug: string;
  brand_name: string;
  current_directors: BrandDirector[];
  past_directors: BrandDirector[];
}

export interface AdminStats {
  counts: {
    channels: number;
    channel_brands: number;
    products: number;
    price_history: number;
  };
  latest_crawls: {
    brands: string | null;
    products: string | null;
  };
  exchange_rates: Array<{
    from_currency: string;
    rate: number;
    fetched_at: string | null;
  }>;
}

export interface AdminChannelHealth {
  channel_id: number;
  name: string;
  url: string;
  channel_type: string | null;
  country: string | null;
  brand_count: number;
  product_count: number;
  sale_count: number;
  health: "ok" | "needs_review";
}

export interface AdminCrawlStatus {
  channel_id: number;
  channel_name: string;
  channel_url: string;
  channel_type: string | null;
  product_count: number;
  active_count: number;
  inactive_count: number;
  last_crawled_at: string | null;
  status: "ok" | "never" | "stale";
}

export interface AdminCollabItem {
  id: number;
  brand_a_id: number;
  brand_b_id: number;
  collab_name: string;
  collab_category: string | null;
  release_year: number | null;
  hype_score: number;
  source_url: string | null;
  notes: string | null;
  created_at: string | null;
  brand_a_name: string | null;
  brand_a_slug: string | null;
}

export interface AdminAuditItem {
  audit_type: string;
  channel_id: number;
  channel_name: string;
  channel_type: string | null;
  channel_url: string;
  brand_count: number;
  linked_brands: string[];
  reason: string;
  suggestion: string;
}

export interface CrawlChannelLog {
  id: number;
  channel_id: number;
  channel_name: string;
  status: "success" | "failed" | "skipped";
  products_found: number;
  products_new: number;
  products_updated: number;
  error_msg: string | null;
  strategy: string | null;
  duration_ms: number;
  crawled_at: string;
}

export interface CrawlRunOut {
  id: number;
  started_at: string;
  finished_at: string | null;
  status: "running" | "done" | "failed";
  total_channels: number;
  done_channels: number;
  new_products: number;
  updated_products: number;
  error_channels: number;
}

export interface CrawlRunDetail extends CrawlRunOut {
  logs: CrawlChannelLog[];
}
