import type { ChatMessage, ChatOpts, LLMProvider } from "../types";
import { openaiCompatChat } from "./openaiCompat";

// Qwen CLOUD (Alibaba DashScope compatible-mode, or any OpenAI-compatible Qwen
// endpoint via QWEN_BASE_URL + QWEN_API_KEY). This is distinct from local-qwen:
// it is an external hosted provider and activates only when a key is set.
const key = () => process.env.QWEN_API_KEY || process.env.DASHSCOPE_API_KEY || "";
const base = () =>
  process.env.QWEN_BASE_URL || "https://dashscope-intl.aliyuncs.com/compatible-mode/v1";
const DEFAULT_MODEL = process.env.QWEN_CLOUD_MODEL || "qwen-plus";

const qwenCloud: LLMProvider = {
  id: "qwen-cloud",
  label: "Qwen cloud (DashScope)",
  available: () => !!key(),

  async chat(messages: ChatMessage[], opts?: ChatOpts): Promise<string> {
    if (!key()) {
      throw new Error(
        "provider 'qwen-cloud' not configured — set DASHSCOPE_API_KEY, or QWEN_BASE_URL + QWEN_API_KEY"
      );
    }
    return openaiCompatChat(base(), key(), DEFAULT_MODEL, messages, opts);
  },
};

export default qwenCloud;
