export interface Product {
  id: number;
  channel_id: number;
  brand_id: number | null;
  name: string;
  product_key: string | null;
  url: string;
  image_url: string | null;
  is_sale: boolean;
  is_active: boolean;
}

export interface PriceComparisonItem {
  channel_name: string;
  channel_country: string | null;
  channel_url: string;
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
  tier: string | null;
  description_ko: string | null;
}

export interface Channel {
  id: number;
  name: string;
  url: string;
  channel_type: string | null;
  country: string | null;
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
}

export interface ChannelHighlight {
  channel_id: number;
  channel_name: string;
  channel_url: string;
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
  tier: string | null;
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
