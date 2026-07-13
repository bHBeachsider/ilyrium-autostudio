import type { LLMProvider, ProviderInfo } from "./types";
import localQwen from "./providers/localQwen";
import anthropic from "./providers/anthropic";
import gemini from "./providers/gemini";
import grok from "./providers/grok";
import qwenCloud from "./providers/qwenCloud";

export type { ChatMessage, ChatOpts, ChatRole, LLMProvider, ProviderInfo } from "./types";

// Registration order is UI order — local qwen3 is always first / the default.
const ALL: LLMProvider[] = [localQwen, anthropic, gemini, grok, qwenCloud];

/** Providers that can be called right now (key present / no key needed). Local qwen3 stays first. */
export function listProviders(): LLMProvider[] {
  return ALL.filter((p) => p.available());
}

/** Every registered provider with its availability — for the chat panel's dropdown hints. */
export function describeProviders(): ProviderInfo[] {
  return ALL.map((p) => ({ id: p.id, label: p.label, available: p.available() }));
}

export function getProvider(id: string): LLMProvider | undefined {
  return ALL.find((p) => p.id === id);
}
