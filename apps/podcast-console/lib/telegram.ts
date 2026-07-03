import type { IdeaRow } from "@/lib/db"

// Optional Telegram HITL mirror. The in-app review queue is the source of truth;
// Telegram only notifies and offers inline approve/reject that route through the
// same applyIdeaDecision path. Fully feature-flagged: with TELEGRAM_BOT_TOKEN or
// TELEGRAM_CHAT_ID unset every call is a silent no-op.

function config() {
  const token = process.env.TELEGRAM_BOT_TOKEN
  const chatId = process.env.TELEGRAM_CHAT_ID
  return token && chatId ? { token, chatId } : null
}

export function telegramEnabled(): boolean {
  return !!config()
}

async function api(token: string, method: string, payload: Record<string, unknown>): Promise<boolean> {
  try {
    const res = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      console.warn(`[telegram] ${method} failed:`, res.status, (await res.text()).slice(0, 200))
    }
    return res.ok
  } catch (err) {
    console.warn(`[telegram] ${method} error:`, err instanceof Error ? err.message : err)
    return false
  }
}

/** Mirror a new proposal to the configured chat with inline approve/reject. */
export async function notifyIdeaProposed(idea: IdeaRow): Promise<void> {
  const cfg = config()
  if (!cfg) return
  const text =
    `🎙 New episode idea proposed\n\n` +
    `*${idea.title}*\n` +
    (idea.angle ? `_${idea.angle}_\n\n` : "\n") +
    (idea.summary ?? "") +
    (idea.score != null ? `\n\nScore: ${idea.score}/10` : "") +
    `\n\nDecide here or in the in-app review queue (app wins on conflict).`
  await api(cfg.token, "sendMessage", {
    chat_id: cfg.chatId,
    text,
    parse_mode: "Markdown",
    reply_markup: {
      inline_keyboard: [
        [
          { text: "✅ Approve", callback_data: `idea:${idea.id}:approved` },
          { text: "❌ Reject", callback_data: `idea:${idea.id}:rejected` },
        ],
      ],
    },
  })
}

export async function answerCallback(callbackQueryId: string, text: string): Promise<void> {
  const cfg = config()
  if (!cfg) return
  await api(cfg.token, "answerCallbackQuery", { callback_query_id: callbackQueryId, text })
}

/** Rewrite the mirrored message once a decision lands, removing the buttons. */
export async function markMessageDecided(chatId: number | string, messageId: number, outcome: string): Promise<void> {
  const cfg = config()
  if (!cfg) return
  await api(cfg.token, "editMessageReplyMarkup", {
    chat_id: chatId,
    message_id: messageId,
    reply_markup: { inline_keyboard: [] },
  })
  await api(cfg.token, "sendMessage", {
    chat_id: chatId,
    reply_to_message_id: messageId,
    text: outcome,
  })
}
