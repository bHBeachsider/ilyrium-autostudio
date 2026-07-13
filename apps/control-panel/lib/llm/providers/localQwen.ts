import type { ChatMessage, ChatOpts, LLMProvider } from "../types";

// Local qwen3 on the EC2 box, reached DIRECTLY at ollama through the SSH tunnel
// (cli/box.ps1 tunnel forwards :11434). No cloud SDK, no external call, no API
// key — the conversation never leaves Brad's hardware. This module runs
// server-side (dispatched by app/api/llm/chat/route.ts), so 127.0.0.1 resolves
// on the machine that holds the tunnel.
const OLLAMA_URL =
  process.env.OLLAMA_URL || process.env.NEXT_PUBLIC_OLLAMA_URL || "http://127.0.0.1:11434";
const DEFAULT_MODEL =
  process.env.LOCAL_LLM_MODEL || process.env.NEXT_PUBLIC_LOCAL_LLM_MODEL || "qwen3-coder:latest";

const localQwen: LLMProvider = {
  id: "local-qwen",
  label: "Local qwen3 · on-box (ollama)",
  // No key required. Reachability is a runtime property of the tunnel, so
  // chat() reports it as a clear error instead of hiding the provider.
  available: () => true,

  async chat(messages: ChatMessage[], opts?: ChatOpts): Promise<string> {
    const base = OLLAMA_URL.replace(/\/+$/, "");
    let res: Response;
    try {
      res = await fetch(`${base}/api/chat`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          model: opts?.model || DEFAULT_MODEL,
          messages,
          stream: false,
          options: {
            ...(opts?.temperature != null ? { temperature: opts.temperature } : {}),
            ...(opts?.maxTokens != null ? { num_predict: opts.maxTokens } : {}),
          },
        }),
        signal: AbortSignal.timeout(180_000),
      });
    } catch (e: any) {
      throw new Error(
        `ollama unreachable at ${base} — start the box + open the tunnel in the Box panel. (${e?.message || e})`
      );
    }
    if (!res.ok) {
      const detail = (await res.text().catch(() => "")).slice(0, 300);
      throw new Error(`ollama error ${res.status}: ${detail}`);
    }
    const data = await res.json();
    const text: string = data?.message?.content ?? "";
    // qwen3 emits <think>…</think> reasoning blocks; strip them from the transcript.
    return text.replace(/<think>[\s\S]*?<\/think>/g, "").trim();
  },
};

export default localQwen;
