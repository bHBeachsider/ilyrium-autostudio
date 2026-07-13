import type { ChatMessage, ChatOpts } from "../types";

// Shared plain-fetch client for OpenAI-compatible chat/completions endpoints
// (grok, qwen-cloud/DashScope, gemini's OpenAI-compat surface). No SDK — one
// POST with a bearer key, per the no-new-heavy-deps rule.
export async function openaiCompatChat(
  baseUrl: string,
  apiKey: string,
  model: string,
  messages: ChatMessage[],
  opts?: ChatOpts
): Promise<string> {
  const base = baseUrl.replace(/\/+$/, "");
  let res: Response;
  try {
    res = await fetch(`${base}/chat/completions`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: opts?.model || model,
        messages,
        ...(opts?.temperature != null ? { temperature: opts.temperature } : {}),
        ...(opts?.maxTokens != null ? { max_tokens: opts.maxTokens } : {}),
      }),
      signal: AbortSignal.timeout(120_000),
    });
  } catch (e: any) {
    throw new Error(`provider unreachable at ${base}: ${e?.message || e}`);
  }
  if (!res.ok) {
    const detail = (await res.text().catch(() => "")).slice(0, 300);
    throw new Error(`provider error ${res.status}: ${detail}`);
  }
  const data = await res.json();
  const text = data?.choices?.[0]?.message?.content;
  if (typeof text !== "string") throw new Error("provider returned no message content");
  return text.trim();
}
