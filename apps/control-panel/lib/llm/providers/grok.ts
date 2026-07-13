import type { ChatMessage, ChatOpts, LLMProvider } from "../types";
import { openaiCompatChat } from "./openaiCompat";

// Grok via xAI's OpenAI-compatible API — plain fetch, no SDK. Activates only
// when XAI_API_KEY (or GROK_API_KEY) is set server-side.
const key = () => process.env.XAI_API_KEY || process.env.GROK_API_KEY || "";
const BASE = process.env.XAI_BASE_URL || "https://api.x.ai/v1";
const DEFAULT_MODEL = process.env.GROK_MODEL || "grok-4";

const grok: LLMProvider = {
  id: "grok",
  label: "Grok (xAI)",
  available: () => !!key(),

  async chat(messages: ChatMessage[], opts?: ChatOpts): Promise<string> {
    if (!key()) throw new Error("provider 'grok' not configured — set XAI_API_KEY or GROK_API_KEY");
    return openaiCompatChat(BASE, key(), DEFAULT_MODEL, messages, opts);
  },
};

export default grok;
