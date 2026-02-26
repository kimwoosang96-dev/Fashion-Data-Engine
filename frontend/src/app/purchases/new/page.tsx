"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { createPurchase, searchProducts } from "@/lib/api";
import type { Product } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function NewPurchasePage() {
  const router = useRouter();
  const [form, setForm] = useState({
    product_key: "",
    product_name: "",
    brand_slug: "",
    channel_name: "",
    channel_url: "",
    paid_price_krw: "",
    original_price_krw: "",
    notes: "",
  });
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Product[]>([]);
  const [saving, setSaving] = useState(false);

  const handleSearch = async (q: string) => {
    setSearchQuery(q);
    if (!q.trim()) { setSearchResults([]); return; }
    const results = await searchProducts(q);
    setSearchResults(results);
  };

  const selectProduct = (p: Product) => {
    setForm((prev) => ({
      ...prev,
      product_key: p.product_key ?? "",
      product_name: p.name,
      channel_url: p.url,
    }));
    setSearchQuery(p.name);
    setSearchResults([]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.product_name || !form.channel_name || !form.paid_price_krw) return;
    setSaving(true);
    try {
      const purchase = await createPurchase({
        product_key: form.product_key || form.product_name,
        product_name: form.product_name,
        brand_slug: form.brand_slug || null,
        channel_name: form.channel_name,
        channel_url: form.channel_url || null,
        paid_price_krw: parseInt(form.paid_price_krw),
        original_price_krw: form.original_price_krw ? parseInt(form.original_price_krw) : null,
        notes: form.notes || null,
      });
      router.push(`/purchases/${purchase.id}`);
    } finally {
      setSaving(false);
    }
  };

  const set = (key: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [key]: e.target.value }));

  return (
    <div className="p-6 max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">구매 추가</h1>
        <p className="text-sm text-gray-500 mt-1">구매한 제품 정보를 입력하세요</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        {/* Product search */}
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-500">제품 검색 (선택)</label>
          <Input
            placeholder="DB에서 제품 검색..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
          />
          {searchResults.length > 0 && (
            <ul className="border border-gray-200 rounded-lg divide-y divide-gray-100 overflow-hidden mt-1">
              {searchResults.slice(0, 6).map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() => selectProduct(p)}
                    className="w-full text-left px-3 py-2 hover:bg-gray-50 text-sm"
                  >
                    {p.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-500">제품명 *</label>
          <Input value={form.product_name} onChange={set("product_name")} required placeholder="예: Supreme Box Logo Tee" />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-500">채널명 *</label>
            <Input value={form.channel_name} onChange={set("channel_name")} required placeholder="예: NUBIAN" />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-500">브랜드 slug</label>
            <Input value={form.brand_slug} onChange={set("brand_slug")} placeholder="예: supreme" />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-500">구매가 (KRW) *</label>
            <Input type="number" value={form.paid_price_krw} onChange={set("paid_price_krw")} required placeholder="150000" />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-500">원가 (KRW)</label>
            <Input type="number" value={form.original_price_krw} onChange={set("original_price_krw")} placeholder="200000" />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-500">채널 URL</label>
          <Input value={form.channel_url} onChange={set("channel_url")} placeholder="https://..." />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-500">메모</label>
          <Input value={form.notes} onChange={set("notes")} placeholder="추가 메모..." />
        </div>

        <div className="flex gap-3 pt-2">
          <Button type="submit" disabled={saving} className="flex-1">
            {saving ? "저장 중..." : "저장"}
          </Button>
          <Button type="button" variant="outline" onClick={() => router.back()}>
            취소
          </Button>
        </div>
      </form>
    </div>
  );
}
