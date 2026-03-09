"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const STORAGE_KEY = "fde_enabled_ais";

interface SearchResult {
  url: string;
  normalized_url?: string;
  title: string;
  price_raw: string;
  currency: string;
  in_stock: boolean;
  source_ai: string;
  error?: string;
}

const AI_COLORS: Record<string, string> = {
  claude: "bg-orange-100 text-orange-800",
  gpt: "bg-emerald-100 text-emerald-800",
  gemini: "bg-blue-100 text-blue-800",
};

const AI_LABELS: Record<string, string> = {
  claude: "Claude",
  gpt: "GPT",
  gemini: "Gemini",
};

const EXAMPLES = [
  "팔라스 박스로고 티셔츠 M 사이즈 최저가",
  "Stone Island 아노락 한국 최저가",
  "Arc'teryx 베타 재킷 구매처",
  "Moncler 패딩 세일 중인 곳",
];

export function SearchPage() {
  const [enabled, setEnabled] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    setEnabled(stored ? JSON.parse(stored) : ["claude", "gpt", "gemini"]);
  }, []);

  async function handleSearch(q: string = query) {
    if (!q.trim()) return;
    if (enabled.length === 0) {
      setError("설정에서 최소 1개의 AI를 활성화하세요.");
      return;
    }
    setLoading(true);
    setError(null);
    setSearched(true);

    try {
      const resp = await fetch(`${API_BASE}/api/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, enabled_ais: enabled }),
      });

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail ?? `HTTP ${resp.status}`);
      }

      const data = await resp.json();
      setResults(data.results ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "검색 중 오류가 발생했습니다.");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  const validResults = results.filter((r) => !r.error);
  const errors = results.filter((r) => r.error);

  return (
    <div className="min-h-screen bg-[#f7f4ee]">
      {/* Hero */}
      <div className="mx-auto max-w-3xl px-4 pt-20 pb-12">
        <div className="mb-8 text-center">
          <p className="mb-3 inline-flex items-center rounded-full border border-black/10 bg-white/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.28em] text-gray-600">
            Personal AI Shopper
          </p>
          <h1 className="text-4xl font-black leading-none tracking-[-0.04em] text-zinc-950 md:text-5xl">
            AI가 직접 찾아주는
            <br />
            패션 브랜드 최저가
          </h1>
          <p className="mt-4 text-base text-zinc-500">
            내 Claude·ChatGPT·Gemini가 동시에 검색해 한 곳에 모아드립니다.
            <br />
            API 비용 없음 — 기존 구독 그대로 사용.
          </p>

          {/* Active AI badges */}
          <div className="mt-4 flex items-center justify-center gap-2">
            {enabled.length > 0 ? (
              enabled.map((ai) => (
                <span
                  key={ai}
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${AI_COLORS[ai] ?? "bg-zinc-100 text-zinc-700"}`}
                >
                  {AI_LABELS[ai] ?? ai} ✓
                </span>
              ))
            ) : (
              <Link
                href="/settings"
                className="rounded-full bg-zinc-900 px-4 py-1.5 text-xs font-semibold text-white hover:bg-zinc-700"
              >
                AI 설정하기 →
              </Link>
            )}
            <Link href="/settings" className="text-xs text-zinc-400 hover:text-zinc-700 underline ml-1">
              변경
            </Link>
          </div>
        </div>

        {/* Search box */}
        <div className="rounded-2xl border border-black/10 bg-white p-3 shadow-lg">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="팔라스 박스로고 M 최저가 / 제품 URL 붙여넣기"
              className="flex-1 rounded-xl px-4 py-3 text-sm outline-none placeholder:text-zinc-400"
            />
            <button
              onClick={() => handleSearch()}
              disabled={loading}
              className="rounded-xl bg-zinc-950 px-6 py-3 text-sm font-bold text-white disabled:opacity-40 hover:bg-zinc-800 transition"
            >
              {loading ? "검색 중…" : "검색"}
            </button>
          </div>

          {!searched && (
            <div className="mt-3 flex flex-wrap gap-2 px-2">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  onClick={() => { setQuery(ex); handleSearch(ex); }}
                  className="rounded-full border border-zinc-200 bg-zinc-50 px-3 py-1 text-xs text-zinc-600 hover:border-zinc-400"
                >
                  {ex}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
            {error.includes("설정") && (
              <Link href="/settings" className="ml-2 font-semibold underline">설정하러 가기</Link>
            )}
          </div>
        )}

        {/* AI 서비스 오류 */}
        {errors.length > 0 && searched && !loading && (
          <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-700 space-y-1">
            {errors.map((e, i) => (
              <p key={i}>{e.error}</p>
            ))}
          </div>
        )}
      </div>

      {/* Results */}
      {searched && (
        <div className="mx-auto max-w-3xl px-4 pb-16">
          {loading ? (
            <div className="space-y-3">
              <p className="text-sm text-zinc-400">AI가 검색 중입니다… (최대 30초)</p>
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-20 animate-pulse rounded-xl bg-zinc-200" />
              ))}
            </div>
          ) : validResults.length === 0 ? (
            <div className="py-16 text-center text-zinc-400">
              결과를 찾지 못했습니다. 다른 검색어로 시도해보세요.
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-zinc-500">{validResults.length}개 판매처 발견 (중복 제거됨)</p>
              {validResults.map((r, i) => (
                <ResultCard key={i} result={r} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ResultCard({ result }: { result: SearchResult }) {
  const domain = (() => {
    try { return new URL(result.url).hostname.replace("www.", ""); }
    catch { return result.url; }
  })();

  const aiColor = AI_COLORS[result.source_ai] ?? "bg-zinc-100 text-zinc-700";

  return (
    <div className="flex items-center gap-4 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="flex-1 min-w-0">
        <a
          href={result.url}
          target="_blank"
          rel="noopener noreferrer"
          className="block truncate font-semibold text-zinc-900 hover:underline"
        >
          {result.title || domain}
        </a>
        <p className="mt-0.5 truncate text-xs text-zinc-400">{domain}</p>
      </div>

      <div className="flex flex-shrink-0 items-center gap-2">
        {result.price_raw && (
          <span className="text-sm font-bold text-zinc-800">{result.price_raw}</span>
        )}
        {!result.in_stock && (
          <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-600">품절</span>
        )}
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${aiColor}`}>
          {AI_LABELS[result.source_ai] ?? result.source_ai}
        </span>
        <a
          href={result.url}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-lg bg-zinc-950 px-3 py-1.5 text-xs font-bold text-white hover:bg-zinc-800"
        >
          방문
        </a>
      </div>
    </div>
  );
}
