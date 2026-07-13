import { NextResponse } from "next/server";
import { describeProviders, getProvider } from "../../../../lib/llm";
import type { ChatMessage } from "../../../../lib/llm";

// Multi-provider chat dispatcher (server-side). The browser never talks to a
// model endpoint directly: API keys stay in the Next.js server env, and the
// default local-qwen provider reaches ollama at 127.0.0.1:11434 through the
// SSH tunnel from this server process (no CORS, no key, no external call).
// This route only ROUTES the message history to the selected provider — no
// policy or prompt manipulation of any kind.
export const dynamic = "force-dynamic";

const ROLES = new Set(["system", "user", "assistant"]);

export async function GET() {
  // Provider list for the chat panel's dropdown (availability = server env keys).
  return NextResponse.json({ providers: describeProviders(), default: "local-qwen" });
}

export async function POST(req: Request) {
  let body: any;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 });
  }
  const id: string = body?.provider || "local-qwen";
  const messages = body?.messages as ChatMessage[] | undefined;
  if (
    !Array.isArray(messages) ||
    messages.length === 0 ||
    messages.some((m: any) => !m || typeof m.content !== "string" || !ROLES.has(m.role))
  ) {
    return NextResponse.json(
      { error: "messages must be a non-empty array of {role: system|user|assistant, content}" },
      { status: 400 }
    );
  }
  const provider = getProvider(id);
  if (!provider) {
    return NextResponse.json({ error: `unknown provider '${id}'` }, { status: 400 });
  }
  if (!provider.available()) {
    return NextResponse.json(
      { error: `provider '${id}' is not configured (missing API key env var)`, provider: id },
      { status: 400 }
    );
  }
  try {
    const reply = await provider.chat(messages, body?.opts);
    return NextResponse.json({ ok: true, provider: provider.id, reply });
  } catch (e: any) {
    // Clean JSON error (tunnel down, provider 4xx/5xx, timeout) — never a crash page.
    return NextResponse.json({ error: e?.message || String(e), provider: provider.id }, { status: 502 });
  }
}
