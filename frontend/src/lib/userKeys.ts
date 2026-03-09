/**
 * 사용자 AI API 키 관리 (LocalStorage)
 * 키는 브라우저에만 저장되며 서버로 전송 시 요청 헤더에 포함됩니다.
 */

export interface UserAIKeys {
  openai?: string;   // sk-...
  gemini?: string;   // AIza...
  claude?: string;   // sk-ant-...
}

const STORAGE_KEY = "fde_ai_keys";

export function loadKeys(): UserAIKeys {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function saveKeys(keys: UserAIKeys): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(keys));
}

export function clearKeys(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export function buildAIHeaders(keys: UserAIKeys): Record<string, string> {
  const headers: Record<string, string> = {};
  if (keys.openai) headers["X-OpenAI-Key"] = keys.openai;
  if (keys.gemini) headers["X-Gemini-Key"] = keys.gemini;
  if (keys.claude) headers["X-Claude-Key"] = keys.claude;
  return headers;
}

export function activeAIs(keys: UserAIKeys): string[] {
  const active: string[] = [];
  if (keys.openai) active.push("GPT");
  if (keys.gemini) active.push("Gemini");
  if (keys.claude) active.push("Claude");
  return active;
}
