"use client";

import { useEffect, useState } from "react";
import {
  createAdminCollab,
  createAdminDirector,
  deleteAdminCollab,
  deleteAdminDirector,
  getAdminBrandChannelAudit,
  getAdminCrawlStatus,
  getAdminChannelsHealth,
  getAdminCollabs,
  getAdminDirectors,
  getAdminStats,
  getBrands,
  getChannels,
  patchAdminBrandInstagram,
  patchAdminChannelInstagram,
  triggerChannelCrawl,
  triggerAdminCrawl,
} from "@/lib/api";
import type {
  AdminAuditItem,
  AdminCrawlStatus,
  AdminChannelHealth,
  AdminCollabItem,
  AdminStats,
  Brand,
  BrandDirector,
  Channel,
} from "@/lib/types";
import { Input } from "@/components/ui/input";

export default function AdminPage() {
  const [token, setToken] = useState("");
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [health, setHealth] = useState<AdminChannelHealth[]>([]);
  const [crawlStatus, setCrawlStatus] = useState<AdminCrawlStatus[]>([]);
  const [crawlFilter, setCrawlFilter] = useState<"all" | "ok" | "never" | "stale">("all");
  const [directors, setDirectors] = useState<BrandDirector[]>([]);
  const [collabs, setCollabs] = useState<AdminCollabItem[]>([]);
  const [auditItems, setAuditItems] = useState<AdminAuditItem[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string>("");
  const [directorForm, setDirectorForm] = useState({
    brand_slug: "",
    name: "",
    role: "Creative Director",
    start_year: "",
    end_year: "",
    note: "",
  });
  const [brandIdForInsta, setBrandIdForInsta] = useState<number | "">("");
  const [brandInsta, setBrandInsta] = useState("");
  const [channelIdForInsta, setChannelIdForInsta] = useState<number | "">("");
  const [channelInsta, setChannelInsta] = useState("");
  const [collabForm, setCollabForm] = useState({
    brand_a_slug: "",
    brand_b_slug: "",
    collab_name: "",
    collab_category: "",
    release_year: "",
    hype_score: "",
    source_url: "",
    notes: "",
  });

  const load = async (adminToken: string) => {
    setLoading(true);
    setMsg("");
    try {
      const [s, h] = await Promise.all([
        getAdminStats(adminToken),
        getAdminChannelsHealth(adminToken, 250, 0),
      ]);
      setStats(s);
      setHealth(h);
      const [d, b, c, k, audit, crawl] = await Promise.all([
        getAdminDirectors(adminToken),
        getBrands(),
        getChannels(),
        getAdminCollabs(adminToken, 300, 0),
        getAdminBrandChannelAudit(adminToken, 300),
        getAdminCrawlStatus(adminToken, 500, 0),
      ]);
      setDirectors(d);
      setBrands(b);
      setChannels(c);
      setCollabs(k);
      setAuditItems(audit.items);
      setCrawlStatus(crawl);
      localStorage.setItem("admin_token", adminToken);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "관리 API 호출 실패");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const stored = localStorage.getItem("admin_token") || "";
    if (stored) {
      setToken(stored);
      void load(stored);
    }
  }, []);

  const runJob = async (job: "brands" | "products" | "drops") => {
    if (!token.trim()) return;
    setMsg("");
    try {
      const res = await triggerAdminCrawl(token.trim(), job, false);
      setMsg(`${res.job} 크롤 트리거됨 (pid=${res.pid ?? "-"})`);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "크롤 트리거 실패");
    }
  };

  const runChannelCrawl = async (channelId: number) => {
    if (!token.trim()) return;
    setMsg("");
    try {
      const res = await triggerChannelCrawl(token.trim(), channelId, false);
      setMsg(`channel(${channelId}) 크롤 트리거됨 (pid=${res.pid ?? "-"})`);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "단일 채널 크롤 트리거 실패");
    }
  };

  const submitDirector = async () => {
    if (!token.trim()) return;
    if (!directorForm.brand_slug.trim() || !directorForm.name.trim()) {
      setMsg("브랜드 slug와 디렉터 이름을 입력하세요.");
      return;
    }
    try {
      await createAdminDirector(token.trim(), {
        brand_slug: directorForm.brand_slug.trim(),
        name: directorForm.name.trim(),
        role: directorForm.role.trim() || "Creative Director",
        start_year: directorForm.start_year ? Number(directorForm.start_year) : undefined,
        end_year: directorForm.end_year ? Number(directorForm.end_year) : undefined,
        note: directorForm.note.trim() || undefined,
      });
      setDirectorForm({ brand_slug: "", name: "", role: "Creative Director", start_year: "", end_year: "", note: "" });
      const d = await getAdminDirectors(token.trim());
      setDirectors(d);
      setMsg("디렉터가 등록되었습니다.");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "디렉터 등록 실패");
    }
  };

  const removeDirector = async (directorId: number) => {
    if (!token.trim()) return;
    try {
      await deleteAdminDirector(token.trim(), directorId);
      setDirectors((prev) => prev.filter((d) => d.id !== directorId));
      setMsg("디렉터가 삭제되었습니다.");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "디렉터 삭제 실패");
    }
  };

  const saveBrandInstagram = async () => {
    if (!token.trim() || !brandIdForInsta) return;
    try {
      await patchAdminBrandInstagram(token.trim(), Number(brandIdForInsta), brandInsta.trim() || undefined);
      setMsg("브랜드 인스타그램 URL 저장 완료");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "브랜드 인스타그램 저장 실패");
    }
  };

  const saveChannelInstagram = async () => {
    if (!token.trim() || !channelIdForInsta) return;
    try {
      await patchAdminChannelInstagram(token.trim(), Number(channelIdForInsta), channelInsta.trim() || undefined);
      setMsg("채널 인스타그램 URL 저장 완료");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "채널 인스타그램 저장 실패");
    }
  };

  const submitCollab = async () => {
    if (!token.trim()) return;
    if (!collabForm.brand_a_slug.trim() || !collabForm.brand_b_slug.trim() || !collabForm.collab_name.trim()) {
      setMsg("협업 등록은 brand_a_slug / brand_b_slug / collab_name이 필수입니다.");
      return;
    }
    try {
      await createAdminCollab(token.trim(), {
        brand_a_slug: collabForm.brand_a_slug.trim(),
        brand_b_slug: collabForm.brand_b_slug.trim(),
        collab_name: collabForm.collab_name.trim(),
        collab_category: collabForm.collab_category.trim() || undefined,
        release_year: collabForm.release_year ? Number(collabForm.release_year) : undefined,
        hype_score: collabForm.hype_score ? Number(collabForm.hype_score) : undefined,
        source_url: collabForm.source_url.trim() || undefined,
        notes: collabForm.notes.trim() || undefined,
      });
      setCollabForm({
        brand_a_slug: "",
        brand_b_slug: "",
        collab_name: "",
        collab_category: "",
        release_year: "",
        hype_score: "",
        source_url: "",
        notes: "",
      });
      const list = await getAdminCollabs(token.trim(), 300, 0);
      setCollabs(list);
      setMsg("협업이 등록되었습니다.");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "협업 등록 실패");
    }
  };

  const removeCollab = async (collabId: number) => {
    if (!token.trim()) return;
    try {
      await deleteAdminCollab(token.trim(), collabId);
      setCollabs((prev) => prev.filter((c) => c.id !== collabId));
      setMsg("협업이 삭제되었습니다.");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "협업 삭제 실패");
    }
  };

  const filteredCrawlStatus =
    crawlFilter === "all"
      ? crawlStatus
      : crawlStatus.filter((row) => row.status === crawlFilter);

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold">운영관리</h1>
        <p className="text-sm text-gray-500 mt-1">DB 현황, 채널 헬스, 크롤 제어, 환율</p>
      </div>
      <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
        <div className="flex gap-2">
          <Input
            type="password"
            placeholder="ADMIN_BEARER_TOKEN"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
          <button
            type="button"
            onClick={() => void load(token.trim())}
            className="px-4 h-10 rounded-md bg-gray-900 text-white text-sm"
          >
            조회
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => void runJob("brands")} className="px-3 h-9 rounded-md border text-sm">
            브랜드 크롤 실행
          </button>
          <button type="button" onClick={() => void runJob("products")} className="px-3 h-9 rounded-md border text-sm">
            제품 크롤 실행
          </button>
          <button type="button" onClick={() => void runJob("drops")} className="px-3 h-9 rounded-md border text-sm">
            드롭 크롤 실행
          </button>
        </div>
        {msg && <p className="text-xs text-gray-600">{msg}</p>}
      </div>

      {loading && <p className="text-sm text-gray-400">로딩 중...</p>}

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Stat label="채널" value={stats.counts.channels} />
          <Stat label="채널-브랜드 링크" value={stats.counts.channel_brands} />
          <Stat label="제품" value={stats.counts.products} />
          <Stat label="가격 이력" value={stats.counts.price_history} />
        </div>
      )}

      {stats && (
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <h2 className="text-sm font-semibold mb-2">환율 (→ KRW)</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
            {stats.exchange_rates.slice(0, 8).map((r) => (
              <div key={`${r.from_currency}-${r.fetched_at}`} className="border rounded-md px-3 py-2">
                <p className="font-medium">{r.from_currency}</p>
                <p className="text-gray-600">{r.rate.toLocaleString("ko-KR")}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <section className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
        <h2 className="text-sm font-semibold">크리에이티브 디렉터 관리</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <Input
            placeholder="brand slug (예: nike)"
            value={directorForm.brand_slug}
            onChange={(e) => setDirectorForm((p) => ({ ...p, brand_slug: e.target.value }))}
          />
          <Input
            placeholder="디렉터 이름"
            value={directorForm.name}
            onChange={(e) => setDirectorForm((p) => ({ ...p, name: e.target.value }))}
          />
          <Input
            placeholder="역할 (기본 Creative Director)"
            value={directorForm.role}
            onChange={(e) => setDirectorForm((p) => ({ ...p, role: e.target.value }))}
          />
          <Input
            placeholder="시작 연도"
            value={directorForm.start_year}
            onChange={(e) => setDirectorForm((p) => ({ ...p, start_year: e.target.value }))}
          />
          <Input
            placeholder="종료 연도"
            value={directorForm.end_year}
            onChange={(e) => setDirectorForm((p) => ({ ...p, end_year: e.target.value }))}
          />
          <Input
            placeholder="메모"
            value={directorForm.note}
            onChange={(e) => setDirectorForm((p) => ({ ...p, note: e.target.value }))}
          />
        </div>
        <button type="button" onClick={() => void submitDirector()} className="px-3 h-9 rounded-md bg-gray-900 text-white text-sm">
          디렉터 등록
        </button>
        <div className="space-y-1 max-h-56 overflow-auto">
          {directors.map((d) => (
            <div key={d.id} className="flex items-center justify-between border rounded-md px-3 py-2">
              <p className="text-sm">
                <span className="font-medium">{d.name}</span> · {d.brand_name ?? d.brand_slug} ({d.start_year ?? "?"}~{d.end_year ?? "현재"})
              </p>
              <button
                type="button"
                onClick={() => void removeDirector(d.id)}
                className="text-xs px-2 py-1 rounded border text-red-600 border-red-200"
              >
                삭제
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-white border border-gray-200 rounded-xl p-4 space-y-4">
        <h2 className="text-sm font-semibold">인스타그램 URL 관리</h2>
        <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr_auto] gap-2 items-center">
          <select
            className="h-10 px-3 rounded-md border border-gray-200 bg-white text-sm"
            value={brandIdForInsta}
            onChange={(e) => setBrandIdForInsta(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">브랜드 선택</option>
            {brands.map((b) => (
              <option key={b.id} value={b.id}>{b.name} ({b.slug})</option>
            ))}
          </select>
          <Input placeholder="브랜드 인스타그램 URL" value={brandInsta} onChange={(e) => setBrandInsta(e.target.value)} />
          <button type="button" onClick={() => void saveBrandInstagram()} className="px-3 h-10 rounded-md border text-sm">저장</button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr_auto] gap-2 items-center">
          <select
            className="h-10 px-3 rounded-md border border-gray-200 bg-white text-sm"
            value={channelIdForInsta}
            onChange={(e) => setChannelIdForInsta(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">채널 선택</option>
            {channels.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <Input placeholder="채널 인스타그램 URL" value={channelInsta} onChange={(e) => setChannelInsta(e.target.value)} />
          <button type="button" onClick={() => void saveChannelInstagram()} className="px-3 h-10 rounded-md border text-sm">저장</button>
        </div>
      </section>

      <section className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
        <h2 className="text-sm font-semibold">협업 관리</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <Input
            placeholder="brand_a slug (예: nike)"
            value={collabForm.brand_a_slug}
            onChange={(e) => setCollabForm((p) => ({ ...p, brand_a_slug: e.target.value }))}
          />
          <Input
            placeholder="brand_b slug (예: stussy)"
            value={collabForm.brand_b_slug}
            onChange={(e) => setCollabForm((p) => ({ ...p, brand_b_slug: e.target.value }))}
          />
          <Input
            placeholder="협업명"
            value={collabForm.collab_name}
            onChange={(e) => setCollabForm((p) => ({ ...p, collab_name: e.target.value }))}
          />
          <Input
            placeholder="카테고리 (footwear/apparel...)"
            value={collabForm.collab_category}
            onChange={(e) => setCollabForm((p) => ({ ...p, collab_category: e.target.value }))}
          />
          <Input
            placeholder="출시연도"
            value={collabForm.release_year}
            onChange={(e) => setCollabForm((p) => ({ ...p, release_year: e.target.value }))}
          />
          <Input
            placeholder="하입 점수(미입력 시 자동)"
            value={collabForm.hype_score}
            onChange={(e) => setCollabForm((p) => ({ ...p, hype_score: e.target.value }))}
          />
          <Input
            placeholder="출처 URL"
            value={collabForm.source_url}
            onChange={(e) => setCollabForm((p) => ({ ...p, source_url: e.target.value }))}
          />
          <Input
            placeholder="메모"
            value={collabForm.notes}
            onChange={(e) => setCollabForm((p) => ({ ...p, notes: e.target.value }))}
          />
        </div>
        <button type="button" onClick={() => void submitCollab()} className="px-3 h-9 rounded-md bg-gray-900 text-white text-sm">
          협업 등록
        </button>
        <div className="space-y-1 max-h-64 overflow-auto">
          {collabs.map((c) => (
            <div key={c.id} className="flex items-center justify-between border rounded-md px-3 py-2">
              <p className="text-sm">
                <span className="font-medium">{c.collab_name}</span> · hype {c.hype_score}
                {c.collab_category ? ` · ${c.collab_category}` : ""}
              </p>
              <button
                type="button"
                onClick={() => void removeCollab(c.id)}
                className="text-xs px-2 py-1 rounded border text-red-600 border-red-200"
              >
                삭제
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
        <h2 className="text-sm font-semibold">브랜드-채널 혼재 감사</h2>
        <p className="text-xs text-gray-500">유형 불일치/브랜드 수 이상치를 탐지한 결과입니다.</p>
        <div className="space-y-2 max-h-80 overflow-auto">
          {auditItems.map((item) => (
            <div key={`${item.audit_type}-${item.channel_id}`} className="border rounded-md p-3">
              <p className="text-sm font-medium">
                {item.channel_name} <span className="text-xs text-gray-400">({item.channel_type ?? "-"})</span>
              </p>
              <p className="text-xs text-red-600 mt-1">{item.reason}</p>
              <p className="text-xs text-gray-600 mt-1">제안: {item.suggestion}</p>
              <p className="text-xs text-gray-500 mt-1">
                브랜드 수 {item.brand_count} · 연결 브랜드 {item.linked_brands.slice(0, 5).join(", ") || "-"}
              </p>
            </div>
          ))}
          {auditItems.length === 0 && <p className="text-xs text-gray-400">탐지 항목이 없습니다.</p>}
        </div>
      </section>

      {crawlStatus.length > 0 && (
        <section className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold">채널 크롤 현황</h2>
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-500">상태 필터</label>
              <select
                className="h-8 px-2 rounded-md border border-gray-200 bg-white text-xs"
                value={crawlFilter}
                onChange={(e) => setCrawlFilter(e.target.value as "all" | "ok" | "never" | "stale")}
              >
                <option value="all">전체</option>
                <option value="never">never</option>
                <option value="stale">stale</option>
                <option value="ok">ok</option>
              </select>
            </div>
          </div>

          <div className="max-h-[28rem] overflow-auto border rounded-md">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100 sticky top-0">
                <tr>
                  <th className="text-left px-4 py-3">채널</th>
                  <th className="text-left px-4 py-3">타입</th>
                  <th className="text-right px-4 py-3">제품</th>
                  <th className="text-right px-4 py-3">활성</th>
                  <th className="text-right px-4 py-3">품절</th>
                  <th className="text-left px-4 py-3">마지막 크롤</th>
                  <th className="text-left px-4 py-3">상태</th>
                  <th className="text-right px-4 py-3">실행</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filteredCrawlStatus.map((row) => (
                  <tr key={row.channel_id}>
                    <td className="px-4 py-3">
                      <p className="font-medium">{row.channel_name}</p>
                      <p className="text-xs text-gray-400">{row.channel_url}</p>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{row.channel_type ?? "-"}</td>
                    <td className="px-4 py-3 text-right">{row.product_count}</td>
                    <td className="px-4 py-3 text-right">{row.active_count}</td>
                    <td className="px-4 py-3 text-right">{row.inactive_count}</td>
                    <td className="px-4 py-3 text-xs text-gray-600">{row.last_crawled_at ?? "never"}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          row.status === "ok"
                            ? "bg-emerald-100 text-emerald-700"
                            : row.status === "stale"
                            ? "bg-amber-100 text-amber-700"
                            : "bg-rose-100 text-rose-700"
                        }`}
                      >
                        {row.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => void runChannelCrawl(row.channel_id)}
                        className="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-50"
                      >
                        크롤 실행
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {health.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3">채널</th>
                <th className="text-left px-4 py-3">국가</th>
                <th className="text-right px-4 py-3">브랜드</th>
                <th className="text-right px-4 py-3">제품</th>
                <th className="text-right px-4 py-3">세일</th>
                <th className="text-left px-4 py-3">헬스</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {health.map((row) => (
                <tr key={row.channel_id}>
                  <td className="px-4 py-3">
                    <p className="font-medium">{row.name}</p>
                    <p className="text-xs text-gray-400">{row.channel_type ?? "-"}</p>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{row.country ?? "-"}</td>
                  <td className="px-4 py-3 text-right">{row.brand_count}</td>
                  <td className="px-4 py-3 text-right">{row.product_count}</td>
                  <td className="px-4 py-3 text-right">{row.sale_count}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        row.health === "ok" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
                      }`}
                    >
                      {row.health === "ok" ? "정상" : "점검필요"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-xl font-bold mt-1">{value.toLocaleString("ko-KR")}</p>
    </div>
  );
}
