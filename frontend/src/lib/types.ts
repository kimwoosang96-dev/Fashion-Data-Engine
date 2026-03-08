export interface Product {
  id: number;
  channel_id: number;
  brand_id: number | null;
  name: string;
  product_key: string | null;
  normalized_key?: string | null;
  match_confidence?: number | null;
  gender: string | null;
  subcategory: string | null;
  url: string;
  image_url: string | null;
  price_krw?: number | null;
  original_price_krw?: number | null;
  discount_rate?: number | null;
  sale_started_at?: string | null;
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
  brand_name: string | null;
  image_url: string | null;
  listings: PriceComparisonItem[];
  cheapest_channel: string | null;
  cheapest_price_krw: number | null;
  total_listings: number;
}

export interface SearchV2Item {
  id: number;
  product_key: string | null;
  normalized_key: string | null;
  product_name: string;
  brand_name: string | null;
  channel_name: string | null;
  url: string;
  image_url: string | null;
  price_krw: number | null;
  similarity: number | null;
}

export interface BrandSaleChannel {
  channel_name: string;
  url: string;
  products_on_sale: number;
}

export interface BrandSaleHistory {
  month: string;
  product_count: number;
  avg_discount: number | null;
}

export interface BrandSaleIntel {
  brand_slug: string;
  brand_name: string;
  is_currently_on_sale: boolean;
  current_sale_products: number;
  current_max_discount_rate: number | null;
  sale_channels: BrandSaleChannel[];
  monthly_sale_history: BrandSaleHistory[];
  last_sale_started_at: string | null;
  typical_sale_months: number[];
}

export interface CrossChannelPriceHistoryPoint {
  date: string;
  channel_name: string;
  price_krw: number;
  is_sale: boolean;
}

export interface CrossChannelPriceHistory {
  product_key: string;
  product_name: string;
  history: CrossChannelPriceHistoryPoint[];
  all_time_low: CrossChannelPriceHistoryPoint | null;
  current_lowest: CrossChannelPriceHistoryPoint | null;
  price_trend: "falling" | "stable" | "rising";
}

export interface ProductAvailabilityChannel {
  channel_name: string;
  channel_country: string | null;
  channel_url: string;
  product_url: string;
  price_krw: number | null;
  original_price_krw: number | null;
  discount_rate: number | null;
  stock_status: string | null;
  size_availability: Array<Record<string, unknown>> | null;
  is_sale: boolean;
  image_url: string | null;
  last_crawled_at?: string | null;
  data_freshness_hours?: number | null;
}

export interface ProductAvailability {
  product_key: string;
  normalized_key: string | null;
  product_name: string;
  brand_name: string | null;
  brand_slug: string | null;
  image_url: string | null;
  in_stock_anywhere: boolean;
  lowest_price: ProductAvailabilityChannel | null;
  channels: ProductAvailabilityChannel[];
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
  poll_priority: number;
  use_gpt_parser: boolean;
  is_active: boolean;
  last_crawled_at?: string | null;
  data_freshness_hours?: number | null;
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
  last_crawled_at?: string | null;
  data_freshness_hours?: number | null;
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

export interface ProductRankingItem {
  product_key: string | null;
  product_name: string;
  brand_name: string | null;
  image_url: string | null;
  channel_name: string;
  channel_country: string | null;
  product_url: string;
  price_krw: number;
  original_price_krw: number | null;
  discount_rate: number | null;
  total_channels: number;
  price_drop_pct: number | null;
  price_drop_krw: number | null;
  sale_started_at: string | null;
  hours_since_sale_start: number | null;
  badges: string[];
}

export interface SearchSuggestion {
  type: "brand" | "product";
  label: string;
  slug: string | null;
  product_key: string | null;
  channel_name: string | null;
  product_url: string | null;
}

export interface BrandRankingItem {
  brand_id: number;
  brand_name: string;
  brand_slug: string;
  tier: string | null;
  origin_country: string | null;
  sale_product_count: number;
  avg_discount_rate: number;
  max_discount_rate: number | null;
  active_channel_count: number;
  event_count_72h: number;
  latest_event_at: string | null;
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
  channel_name: string;
  channel_url: string;
  platform: string | null;
  is_active: boolean;
  recent_yields: number[];
  avg_yield: number;
  last_success_at: string | null;
  last_probe_at: string | null;
  parse_method: string | null;
  status: "healthy" | "degraded" | "dead";
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

export interface ChannelSignalOut {
  channel_id: number;
  name: string;
  channel_type: string | null;
  country: string | null;
  poll_priority: number;
  product_count: number;
  active_count: number;
  inactive_count: number;
  last_crawled_at: string | null;
  crawl_status: "ok" | "stale" | "never";
  recent_success_rate: number;
  last_error_msg: string | null;
  error_type: string | null;
  traffic_light: "red" | "yellow" | "green";
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
  error_type: string | null;
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
  gpt_fallback_count: number;
}

export interface CrawlRunDetail extends CrawlRunOut {
  logs: CrawlChannelLog[];
}

export interface ChannelNoteOut {
  id: number;
  channel_id: number;
  channel_name: string;
  note_type: string;
  body: string;
  operator: string;
  created_at: string;
  resolved_at: string | null;
}

export interface ActivityFeedItem {
  id: number;
  event_type: "sale_start" | "new_drop" | "price_cut" | "sold_out" | "restock";
  product_name: string | null;
  brand_name: string | null;
  channel_name: string | null;
  price_krw: number | null;
  discount_rate: number | null;
  source_url: string | null;
  image_url: string | null;
  product_key: string | null;
  detected_at: string;
}

export interface PushPublicKey {
  public_key: string;
}

export interface AdminDraftChannel {
  id: number;
  name: string;
  url: string;
  channel_type: string | null;
  platform: string | null;
  country: string | null;
  description: string | null;
  created_at: string;
  product_count: number;
  poll_priority: number;
  use_gpt_parser: boolean;
}

export interface IntelEvent {
  id: number;
  event_type: string;
  layer: string;
  title: string;
  summary: string | null;
  event_time: string | null;
  detected_at: string;
  severity: string;
  confidence: string;
  brand_id: number | null;
  brand_name: string | null;
  brand_slug: string | null;
  channel_id: number | null;
  channel_name: string | null;
  product_id: number | null;
  product_name: string | null;
  product_key: string | null;
  geo_country: string | null;
  geo_city: string | null;
  geo_lat: number | null;
  geo_lng: number | null;
  geo_precision: string;
  source_url: string | null;
  source_domain: string | null;
  source_type: string;
  is_verified: boolean;
}

export interface IntelEventsPage {
  items: IntelEvent[];
  next_cursor: string | null;
  total: number;
}

export interface IntelMapPoint {
  id: number;
  layer: string;
  severity: string;
  confidence: string;
  lat: number;
  lng: number;
  title: string;
  event_time: string;
  geo_precision: string;
}

export interface IntelTimelineOut {
  granularity: string;
  items: Array<{
    bucket: string;
    total: number;
    layers: Record<string, number>;
  }>;
}

export interface AdminIntelStatus {
  latest_run: {
    id: number | null;
    job_name: string | null;
    status: string | null;
    started_at: string | null;
    finished_at: string | null;
    inserted_count: number;
    updated_count: number;
    error_count: number;
  };
  events_total: number;
  events_last_24h: number;
  latest_event_at: string | null;
  freshness_minutes: number | null;
  layers: Array<{ layer: string; count: number }>;
  derived_24h: Record<string, number>;
  activity_feed_24h: number;
  activity_feed_by_type: Record<string, number>;
  gpt_parser_usage: {
    enabled_channels: number;
    last_24h_calls: number;
  };
  oauth_active: boolean;
  top_active_brands: Array<{
    brand_name: string;
    event_count: number;
  }>;
}

export interface AdminLlmCostDaily {
  day: string;
  provider: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
}

export interface AdminLlmCostChannel {
  channel_id: number;
  channel_name: string;
  provider: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
  last_used_at: string | null;
}

export interface AdminLlmCosts {
  window_days: number;
  monthly_total_usd: number;
  providers: Record<string, number>;
  daily: AdminLlmCostDaily[];
  by_channel: AdminLlmCostChannel[];
}

export interface AdminPerformanceMetric {
  path: string;
  count: number;
  avg_ms: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
}

export interface AdminPerformanceSnapshot {
  captured_at: string;
  endpoints: AdminPerformanceMetric[];
  slow_queries: Array<{
    statement: string;
    elapsed_ms: number;
    captured_at: string;
  }>;
  alerts: AdminPerformanceMetric[];
}

export interface DropsCalendarEntry {
  brand_name: string | null;
  title: string;
  event_type: string;
  source_url: string | null;
}

export interface BrandsHeatmapData {
  brands: Array<{ id: number; name: string; slug: string; tier: string | null }>;
  channels: Array<{ id: number; name: string; country: string | null }>;
  cells: Array<{ brand_id: number; channel_id: number; discount_rate: number; product_count: number }>;
}
