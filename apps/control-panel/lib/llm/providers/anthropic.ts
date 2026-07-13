import type { ChatMessage, ChatOpts, LLMProvider } from "../types";

// Claude via the Anthropic Messages API — plain fetch, no SDK. Activates only
// when ANTHROPIC_API_KEY is set in the Next.js server env (never sent to the
// browser; this module is dispatched server-side by /api/llm/chat).
const key = () => process.env.ANTHROPIC_API_KEY || "";
const DEFAULT_MODEL = process.env.ANTHROPIC_MODEL || "claude-sonnet-4-5";

const anthropic: LLMProvider = {
  id: "anthropic",
  label: "Claude (Anthropic)",
  available: () => !!key(),

  async chat(messages: ChatMessage[], opts?: ChatOpts): Promise<string> {
    if (!key()) throw new Error("provider 'anthropic' not configured — set ANTHROPIC_API_KEY");
    // The Messages API takes system as a top-level param, not a message role.
    const system = messages.filter((m) => m.role === "system").map((m) => m.content).join("\n\n");
    const turns = messages.filter((m) => m.role !== "system");
    let res: Response;
    try {
      res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-api-key": key(),
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({
          model: opts?.model || DEFAULT_MODEL,
          max_tokens: opts?.maxTokens ?? 1024,
          ...(system ? { system } : {}),
          ...(opts?.temperature != null ? { temperature: opts.temperature } : {}),
          messages: turns,
        }),
        signal: AbortSignal.timeout(120_000),
      });
    } catch (e: any) {
      throw new Error(`anthropic unreachable: ${e?.message || e}`);
    }
    if (!res.ok) {
      const detail = (await res.text().catch(() => "")).slice(0, 300);
      throw new Error(`anthropic error ${res.status}: ${detail}`);
    }
    const data = await res.json();
    const text = (data?.content || [])
      .filter((b: any) => b?.type === "text")
      .map((b: any) => b.text)
      .join("");
    if (!text) throw new Error("anthropic returned no text content");
    return text.trim();
  },
};

export default anthropic;
