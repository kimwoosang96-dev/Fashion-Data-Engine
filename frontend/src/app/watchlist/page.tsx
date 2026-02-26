"use client";
import { useEffect, useState } from "react";
import { getWatchlist, addWatchlistItem, deleteWatchlistItem, searchBrands, getChannels } from "@/lib/api";
import type { WatchListItem, Brand, Channel } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const TYPE_LABELS: Record<string, string> = {
  brand: "브랜드",
  channel: "채널",
  product_key: "제품",
};

const TYPE_COLORS: Record<string, string> = {
  brand: "bg-blue-100 text-blue-700",
  channel: "bg-green-100 text-green-700",
  product_key: "bg-purple-100 text-purple-700",
};

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchListItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Brand search
  const [brandQuery, setBrandQuery] = useState("");
  const [brandResults, setBrandResults] = useState<Brand[]>([]);

  // Channel search
  const [channelQuery, setChannelQuery] = useState("");
  const [channelResults, setChannelResults] = useState<Channel[]>([]);
  const [allChannels, setAllChannels] = useState<Channel[]>([]);

  // Product key input
  const [productKey, setProductKey] = useState("");
  const [notes, setNotes] = useState("");

  const loadItems = async () => {
    const data = await getWatchlist();
    setItems(data);
    setLoading(false);
  };

  useEffect(() => {
    loadItems();
    getChannels().then(setAllChannels);
  }, []);

  const handleBrandSearch = async (q: string) => {
    setBrandQuery(q);
    if (!q.trim()) { setBrandResults([]); return; }
    const results = await searchBrands(q);
    setBrandResults(results);
  };

  const handleChannelSearch = (q: string) => {
    setChannelQuery(q);
    if (!q.trim()) { setChannelResults([]); return; }
    setChannelResults(
      allChannels.filter((c) =>
        c.name.toLowerCase().includes(q.toLowerCase()) ||
        c.url.toLowerCase().includes(q.toLowerCase())
      ).slice(0, 8)
    );
  };

  const addBrand = async (brand: Brand) => {
    await addWatchlistItem({ watch_type: "brand", watch_value: brand.slug, notes: brand.name });
    setBrandQuery(""); setBrandResults([]);
    loadItems();
  };

  const addChannel = async (channel: Channel) => {
    await addWatchlistItem({ watch_type: "channel", watch_value: channel.url, notes: channel.name });
    setChannelQuery(""); setChannelResults([]);
    loadItems();
  };

  const addProduct = async () => {
    if (!productKey.trim()) return;
    await addWatchlistItem({ watch_type: "product_key", watch_value: productKey.trim(), notes: notes || undefined });
    setProductKey(""); setNotes("");
    loadItems();
  };

  const handleDelete = async (id: number) => {
    await deleteWatchlistItem(id);
    setItems((prev) => prev.filter((i) => i.id !== id));
  };

  return (
    <div className="p-6 space-y-8">
      <div>
        <h1 className="text-2xl font-bold">관심목록</h1>
        <p className="text-sm text-gray-500 mt-1">등록된 항목에 대해서만 Discord 알림이 전송됩니다</p>
      </div>

      {/* Current list */}
      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          등록 항목 ({items.length})
        </h2>
        {loading ? (
          <p className="text-sm text-gray-400">로딩 중...</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-gray-400">등록된 항목이 없습니다. 아래에서 추가하세요.</p>
        ) : (
          <ul className="space-y-2">
            {items.map((item) => (
              <li key={item.id} className="flex items-center gap-3 bg-white rounded-lg border border-gray-200 px-4 py-3">
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${TYPE_COLORS[item.watch_type]}`}>
                  {TYPE_LABELS[item.watch_type]}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{item.watch_value}</p>
                  {item.notes && <p className="text-xs text-gray-400 truncate">{item.notes}</p>}
                </div>
                <button
                  onClick={() => handleDelete(item.id)}
                  className="text-gray-300 hover:text-red-500 transition-colors text-lg leading-none"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Add brand */}
      <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
        <h2 className="text-sm font-semibold">브랜드 추가</h2>
        <Input
          placeholder="브랜드 이름 검색..."
          value={brandQuery}
          onChange={(e) => handleBrandSearch(e.target.value)}
        />
        {brandResults.length > 0 && (
          <ul className="border border-gray-200 rounded-lg divide-y divide-gray-100 overflow-hidden">
            {brandResults.map((b) => (
              <li key={b.id}>
                <button
                  onClick={() => addBrand(b)}
                  className="w-full text-left px-4 py-2.5 hover:bg-gray-50 transition-colors"
                >
                  <span className="text-sm font-medium">{b.name}</span>
                  {b.name_ko && <span className="text-xs text-gray-400 ml-2">{b.name_ko}</span>}
                  <span className="text-xs text-gray-300 ml-2">{b.slug}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Add channel */}
      <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
        <h2 className="text-sm font-semibold">채널 추가</h2>
        <Input
          placeholder="채널 이름 또는 URL 검색..."
          value={channelQuery}
          onChange={(e) => handleChannelSearch(e.target.value)}
        />
        {channelResults.length > 0 && (
          <ul className="border border-gray-200 rounded-lg divide-y divide-gray-100 overflow-hidden">
            {channelResults.map((c) => (
              <li key={c.id}>
                <button
                  onClick={() => addChannel(c)}
                  className="w-full text-left px-4 py-2.5 hover:bg-gray-50 transition-colors"
                >
                  <span className="text-sm font-medium">{c.name}</span>
                  <span className="text-xs text-gray-400 ml-2">{c.url}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Add product key */}
      <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
        <h2 className="text-sm font-semibold">제품 키 추가</h2>
        <Input
          placeholder="product_key (예: supreme:box-logo-tee)"
          value={productKey}
          onChange={(e) => setProductKey(e.target.value)}
        />
        <Input
          placeholder="메모 (선택)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
        <Button onClick={addProduct} disabled={!productKey.trim()} size="sm">
          추가
        </Button>
      </section>
    </div>
  );
}
