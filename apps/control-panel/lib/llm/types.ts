// Text-chat provider abstraction for the studio console's multi-provider chat.
// This layer is SEPARATE from the media adapter-bus (image/video generation) —
// it covers conversation only. Providers are pluggable: local qwen3 (on Brad's
// EC2 box via the ollama tunnel) is the default and needs no key; cloud
// providers light up only when their API-key env var is present. There is no
// policy/routing logic here beyond "send the messages to the selected backend"
// — each provider is responsible for its own behavior.

export type ChatRole = "system" | "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ChatOpts {
  /** override the provider's default model id */
  model?: string;
  temperature?: number;
  /** max tokens for the reply (providers map this to their own param name) */
  maxTokens?: number;
}

export interface LLMProvider {
  id: string;
  label: string;
  /** true when this provider can be called right now (e.g. its key env var is set) */
  available(): boolean;
  /** Send the full message history; resolves to the assistant's reply text. */
  chat(messages: ChatMessage[], opts?: ChatOpts): Promise<string>;
}

/** Shape the chat panel consumes from GET /api/llm/chat. */
export interface ProviderInfo {
  id: string;
  label: string;
  available: boolean;
}
