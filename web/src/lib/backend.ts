const DEFAULT_BASE =
  typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : "http://localhost:8000";
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_BASE;

export async function login(payload: { username?: string; mobile?: string; password: string }) {
  const r = await fetch(`${API_BASE}/api/v1/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error("login failed");
  return r.json();
}

export async function getMe(token: string) {
  const r = await fetch(`${API_BASE}/api/v1/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error("me failed");
  return r.json();
}

export async function streamLLM(
  prompt: string,
  onToken: (token: string) => void,
  options?: { delay_ms?: number; signal?: AbortSignal },
) {
  const r = await fetch(`${API_BASE}/api/v1/llm/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, delay_ms: options?.delay_ms ?? 0 }),
    signal: options?.signal,
  });
  if (!r.ok || !r.body) throw new Error("stream failed");
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    const blocks = chunk.split(/\n\n/);
    for (const block of blocks) {
      const m = block.match(/^data:\s*(.*)$/m);
      if (!m) continue;
      const payload = m[1];
      if (payload === "[DONE]") continue;
      try {
        const obj = JSON.parse(payload);
        const t = obj?.token;
        if (typeof t === "string") onToken(t);
      } catch {
        void 0;
      }
    }
  }
}

export function startLLMStream(
  prompt: string,
  onToken: (token: string) => void,
  delay_ms = 0,
) {
  const ctrl = new AbortController();
  streamLLM(prompt, onToken, { delay_ms, signal: ctrl.signal }).catch(() => undefined);
  return () => ctrl.abort();
}
