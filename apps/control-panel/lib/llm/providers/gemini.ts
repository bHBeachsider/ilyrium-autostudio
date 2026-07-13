import type { ChatMessage, ChatOpts, LLMProvider } from "../types";
import { openaiCompatChat } from "./openaiCompat";

// Gemini via Google's OpenAI-compatibility endpoint — plain fetch, no SDK.
// Activates only when GEMINI_API_KEY (or GOOGLE_API_KEY) is set server-side.
const key = () => process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY || "";
const BASE = "https://generativelanguage.googleapis.com/v1beta/openai";
const DEFAULT_MODEL = process.env.GEMINI_MODEL || "gemini-2.5-flash";

const gemini: LLMProvider = {
  id: "gemini",
  label: "Gemini (Google)",
  available: () => !!key(),

  async chat(messages: ChatMessage[], opts?: ChatOpts): Promise<string> {
    if (!key()) throw new Error("provider 'gemini' not configured — set GEMINI_API_KEY or GOOGLE_API_KEY");
    return openaiCompatChat(BASE, key(), DEFAULT_MODEL, messages, opts);
  },
};

export default gemini;
