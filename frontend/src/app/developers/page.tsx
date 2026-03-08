"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function CopyBlock({ label, content }: { label: string; content: string }) {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <section className="rounded-[28px] border border-black/10 bg-white p-5 shadow-[0_16px_48px_rgba(0,0,0,0.05)]">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-zinc-950">{label}</h2>
        <button
          type="button"
          onClick={() => void onCopy()}
          className="rounded-full border border-zinc-300 px-3 py-1.5 text-xs font-semibold text-zinc-700"
        >
          {copied ? "복사됨" : "복사"}
        </button>
      </div>
      <pre className="mt-4 overflow-x-auto rounded-2xl bg-zinc-950 p-4 text-sm text-zinc-100">
        <code>{content}</code>
      </pre>
    </section>
  );
}

export default function DevelopersPage() {
  const mcpConfig = JSON.stringify(
    {
      mcpServers: {
        "fashion-data-engine": {
          url: `${API_BASE}/mcp`,
          headers: {
            Authorization: "Bearer ${API_KEY}",
          },
        },
      },
    },
    null,
    2,
  );

  const curlSearch = `curl -H "X-API-Key: $API_KEY" "${API_BASE}/api/v2/search?q=black%20cargo&mode=keyword"`;
  const curlAvailability = `curl -H "X-API-Key: $API_KEY" "${API_BASE}/api/v2/availability/new-balance:new-balance-2002r"`;
  const curlExport = `curl -H "X-API-Key: $API_KEY" "${API_BASE}/api/v2/export/products?format=csv&is_sale=true" -o products.csv`;

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-6 py-8 md:px-10">
      <section className="rounded-[32px] bg-zinc-950 px-6 py-8 text-white shadow-[0_24px_80px_rgba(0,0,0,0.18)]">
        <p className="text-xs uppercase tracking-[0.28em] text-zinc-400">Developers</p>
        <h1 className="mt-3 text-4xl font-black tracking-tight">Fashion Data Engine API</h1>
        <p className="mt-4 max-w-3xl text-sm leading-6 text-zinc-300">
          MCP 클라이언트, 외부 자동화(Zapier/n8n), 파트너 리서치 툴이 같은 표준 인터페이스로 붙을 수 있도록
          OpenAPI, API key, export, webhook 연동 예시를 한 곳에 모았습니다.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <a
            href={`${API_BASE}/api/docs`}
            target="_blank"
            rel="noreferrer"
            className="rounded-full bg-lime-300 px-4 py-2 text-sm font-semibold text-zinc-950"
          >
            Swagger 열기
          </a>
          <a
            href={`${API_BASE}/openapi.json`}
            target="_blank"
            rel="noreferrer"
            className="rounded-full border border-zinc-700 px-4 py-2 text-sm font-semibold text-zinc-100"
          >
            OpenAPI JSON 다운로드
          </a>
          <a
            href="/admin"
            className="rounded-full border border-zinc-700 px-4 py-2 text-sm font-semibold text-zinc-100"
          >
            API 키 발급
          </a>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-3xl border border-black/10 bg-white p-5">
          <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">Search</p>
          <p className="mt-3 text-2xl font-bold text-zinc-950">`/api/v2/search`</p>
          <p className="mt-2 text-sm text-zinc-500">키워드/semantic 제품 검색</p>
        </div>
        <div className="rounded-3xl border border-black/10 bg-white p-5">
          <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">Availability</p>
          <p className="mt-3 text-2xl font-bold text-zinc-950">`/api/v2/availability`</p>
          <p className="mt-2 text-sm text-zinc-500">채널별 가격·재고·사이즈 희소성</p>
        </div>
        <div className="rounded-3xl border border-black/10 bg-white p-5">
          <p className="text-xs uppercase tracking-[0.18em] text-zinc-400">Export</p>
          <p className="mt-3 text-2xl font-bold text-zinc-950">`/api/v2/export/products`</p>
          <p className="mt-2 text-sm text-zinc-500">CSV / NDJSON 스트리밍 다운로드</p>
        </div>
      </div>

      <CopyBlock label="MCP 설정" content={mcpConfig} />
      <CopyBlock label="제품 검색 cURL" content={curlSearch} />
      <CopyBlock label="재고 조회 cURL" content={curlAvailability} />
      <CopyBlock label="CSV Export cURL" content={curlExport} />
    </div>
  );
}
