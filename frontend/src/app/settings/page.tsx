"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

const STORAGE_KEY = "fde_enabled_ais";
const PROFILE_KEY = "fde_profile_dir";
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const AI_CONFIG = [
  {
    key: "claude",
    label: "Claude",
    desc: "Anthropic Claude Pro",
    loginUrl: "https://claude.ai/login",
    color: "bg-orange-50 border-orange-200",
    badge: "bg-orange-100 text-orange-800",
    dot: "bg-orange-400",
  },
  {
    key: "gpt",
    label: "ChatGPT",
    desc: "OpenAI ChatGPT Plus",
    loginUrl: "https://chat.openai.com/auth/login",
    color: "bg-emerald-50 border-emerald-200",
    badge: "bg-emerald-100 text-emerald-800",
    dot: "bg-emerald-400",
  },
  {
    key: "gemini",
    label: "Gemini",
    desc: "Google Gemini Advanced",
    loginUrl: "https://gemini.google.com",
    color: "bg-blue-50 border-blue-200",
    badge: "bg-blue-100 text-blue-800",
    dot: "bg-blue-400",
  },
];

interface LoginStatus {
  [key: string]: { logged_in: boolean; login_url?: string; error?: string };
}

export default function SettingsPage() {
  const [enabled, setEnabled] = useState<string[]>(["claude", "gpt", "gemini"]);
  const [profileDir, setProfileDir] = useState("");
  const [loginStatus, setLoginStatus] = useState<LoginStatus>({});
  const [checking, setChecking] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) setEnabled(JSON.parse(stored));
    const dir = localStorage.getItem(PROFILE_KEY);
    if (dir) setProfileDir(dir);
  }, []);

  function toggle(key: string) {
    setEnabled((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
    setSaved(false);
  }

  function handleSave() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(enabled));
    if (profileDir) localStorage.setItem(PROFILE_KEY, profileDir);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function checkLogin() {
    setChecking(true);
    try {
      const params = profileDir ? `?profile_dir=${encodeURIComponent(profileDir)}` : "";
      const resp = await fetch(`${API_BASE}/api/login-status${params}`);
      if (resp.ok) setLoginStatus(await resp.json());
    } catch {
      // 백엔드 미실행 시 무시
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f7f4ee] px-4 py-12">
      <div className="mx-auto max-w-xl space-y-8">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-zinc-950">AI 설정</h1>
          <p className="mt-1 text-sm text-zinc-500">
            구독 중인 AI를 선택하세요. Chrome에서 미리 로그인해두면 자동으로 사용됩니다.
          </p>
        </div>

        <div className="space-y-3">
          {AI_CONFIG.map((ai) => {
            const isEnabled = enabled.includes(ai.key);
            const status = loginStatus[ai.key];
            return (
              <button
                key={ai.key}
                onClick={() => toggle(ai.key)}
                className={`w-full rounded-xl border p-4 text-left transition ${
                  isEnabled ? ai.color : "bg-white border-zinc-200 opacity-60"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={`h-4 w-4 rounded-full border-2 flex items-center justify-center ${
                        isEnabled ? "border-zinc-800 bg-zinc-800" : "border-zinc-300"
                      }`}
                    >
                      {isEnabled && <div className="h-2 w-2 rounded-full bg-white" />}
                    </div>
                    <div>
                      <p className="font-semibold text-zinc-900">{ai.label}</p>
                      <p className="text-xs text-zinc-500">{ai.desc}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {status && (
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          status.logged_in
                            ? "bg-green-100 text-green-700"
                            : "bg-red-100 text-red-600"
                        }`}
                      >
                        {status.logged_in ? "로그인됨" : "미로그인"}
                      </span>
                    )}
                    {status && !status.logged_in && (
                      <a
                        href={ai.loginUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="rounded-lg bg-zinc-900 px-2 py-1 text-xs font-bold text-white"
                      >
                        로그인
                      </a>
                    )}
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        <button
          onClick={checkLogin}
          disabled={checking}
          className="w-full rounded-xl border border-zinc-300 bg-white py-3 text-sm font-semibold text-zinc-700 hover:bg-zinc-50 disabled:opacity-50"
        >
          {checking ? "확인 중…" : "로그인 상태 확인"}
        </button>

        <div className="space-y-2">
          <label className="block text-sm font-semibold text-zinc-700">
            Chrome 프로필 경로 (선택)
          </label>
          <input
            value={profileDir}
            onChange={(e) => { setProfileDir(e.target.value); setSaved(false); }}
            placeholder="비워두면 자동 감지 (~/Library/Application Support/Google/Chrome)"
            className="w-full rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm font-mono outline-none focus:border-zinc-400"
          />
          <p className="text-xs text-zinc-400">
            Chrome 프로필을 지정하면 해당 계정의 로그인 상태를 사용합니다.
          </p>
        </div>

        <button
          onClick={handleSave}
          className="w-full rounded-xl bg-zinc-950 py-3 text-sm font-bold text-white transition hover:bg-zinc-800"
        >
          {saved ? "저장됨 ✓" : "저장"}
        </button>

        <div className="rounded-xl border border-zinc-200 bg-white p-4 text-xs text-zinc-500 space-y-1">
          <p className="font-semibold text-zinc-700">사용 방법</p>
          <p>1. 위에서 사용할 AI를 선택합니다</p>
          <p>2. Chrome에서 각 AI 서비스에 로그인합니다</p>
          <p>3. "로그인 상태 확인"으로 연결을 테스트합니다</p>
          <p>4. <Link href="/" className="underline">홈으로</Link> 돌아가서 검색을 시작합니다</p>
        </div>
      </div>
    </div>
  );
}
