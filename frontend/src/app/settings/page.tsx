"use client";

import { useState, useEffect } from "react";
import { loadKeys, saveKeys, UserAIKeys } from "@/lib/userKeys";

const AI_CONFIG = [
  {
    key: "openai" as keyof UserAIKeys,
    label: "OpenAI (ChatGPT)",
    placeholder: "sk-...",
    hint: "platform.openai.com → API Keys",
    color: "bg-emerald-50 border-emerald-200",
    badge: "bg-emerald-100 text-emerald-800",
  },
  {
    key: "gemini" as keyof UserAIKeys,
    label: "Google Gemini",
    placeholder: "AIza...",
    hint: "aistudio.google.com → Get API key",
    color: "bg-blue-50 border-blue-200",
    badge: "bg-blue-100 text-blue-800",
  },
  {
    key: "claude" as keyof UserAIKeys,
    label: "Anthropic Claude",
    placeholder: "sk-ant-...",
    hint: "console.anthropic.com → API Keys",
    color: "bg-orange-50 border-orange-200",
    badge: "bg-orange-100 text-orange-800",
  },
];

export default function SettingsPage() {
  const [keys, setKeys] = useState<UserAIKeys>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setKeys(loadKeys());
  }, []);

  function handleChange(aiKey: keyof UserAIKeys, value: string) {
    setKeys((prev) => ({ ...prev, [aiKey]: value || undefined }));
    setSaved(false);
  }

  function handleSave() {
    saveKeys(keys);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  function handleClear(aiKey: keyof UserAIKeys) {
    setKeys((prev) => {
      const next = { ...prev };
      delete next[aiKey];
      return next;
    });
    setSaved(false);
  }

  const activeCount = [keys.openai, keys.gemini, keys.claude].filter(Boolean).length;

  return (
    <div className="min-h-screen bg-[#f7f4ee] px-4 py-12">
      <div className="mx-auto max-w-xl space-y-8">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-zinc-950">AI 키 설정</h1>
          <p className="mt-1 text-sm text-zinc-500">
            키는 브라우저 LocalStorage에만 저장됩니다. 서버에 전송되지 않습니다.
          </p>
        </div>

        {activeCount > 0 && (
          <div className="rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm">
            <span className="font-semibold text-zinc-800">활성 AI: </span>
            {AI_CONFIG.filter((c) => keys[c.key]).map((c) => (
              <span key={c.key} className={`mr-2 rounded-full px-2 py-0.5 text-xs font-medium ${c.badge}`}>
                {c.label.split(" ")[0]}
              </span>
            ))}
          </div>
        )}

        <div className="space-y-4">
          {AI_CONFIG.map((config) => (
            <div key={config.key} className={`rounded-xl border p-4 ${config.color}`}>
              <div className="mb-2 flex items-center justify-between">
                <label className="text-sm font-semibold text-zinc-800">{config.label}</label>
                {keys[config.key] && (
                  <button
                    onClick={() => handleClear(config.key)}
                    className="text-xs text-zinc-400 hover:text-red-500"
                  >
                    삭제
                  </button>
                )}
              </div>
              <input
                type="password"
                value={keys[config.key] ?? ""}
                onChange={(e) => handleChange(config.key, e.target.value)}
                placeholder={config.placeholder}
                className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-mono outline-none focus:border-zinc-400"
              />
              <p className="mt-1 text-xs text-zinc-400">{config.hint}</p>
            </div>
          ))}
        </div>

        <button
          onClick={handleSave}
          className="w-full rounded-xl bg-zinc-950 py-3 text-sm font-bold text-white transition hover:bg-zinc-800"
        >
          {saved ? "저장됨 ✓" : "저장"}
        </button>

        <p className="text-center text-xs text-zinc-400">
          키가 없는 AI는 검색에서 자동으로 제외됩니다.
          구독한 AI만 입력하면 됩니다.
        </p>
      </div>
    </div>
  );
}
