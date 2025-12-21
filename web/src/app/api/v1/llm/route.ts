import type { NextRequest } from "next/server";

const FASTAPI_BASE = process.env.FASTAPI_BASE_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const prompt = String(body?.prompt ?? "").trim();
    const delay_ms = Number(body?.delay_ms ?? 50) || 0;

    if (!prompt) {
      return new Response(JSON.stringify({ error: "empty prompt" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    const traceId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    const target = `${FASTAPI_BASE}/api/v1/llm/stream`;
    const r = await fetch(target, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Trace-Id": traceId,
      },
      body: JSON.stringify({ prompt, delay_ms }),
    });

    if (!r.ok || !r.body) {
      return new Response(JSON.stringify({ error: "upstream failed" }), {
        status: 502,
        headers: { "Content-Type": "application/json" },
      });
    }

    const headers = new Headers(r.headers);
    headers.set("Content-Type", "text/event-stream");
    headers.set("Cache-Control", "no-cache");

    return new Response(r.body, { status: r.status, headers });
  } catch (e) {
    return new Response(JSON.stringify({ error: "proxy error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}

export const runtime = "nodejs";
