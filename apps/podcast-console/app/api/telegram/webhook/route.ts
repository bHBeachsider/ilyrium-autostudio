import { NextResponse } from "next/server"
import { DbNotConfiguredError } from "@/lib/db"
import { applyIdeaDecision, isDecision } from "@/lib/ideas"
import { answerCallback, markMessageDecided, telegramEnabled } from "@/lib/telegram"

export const runtime = "nodejs"

// Telegram webhook for the optional HITL mirror. Register with:
//   https://api.telegram.org/bot<token>/setWebhook?url=<app>/api/telegram/webhook&secret_token=<TELEGRAM_WEBHOOK_SECRET>
// Callback data format: idea:<uuid>:<approved|rejected>. Applies the same
// applyIdeaDecision path as the in-app queue; the app remains authoritative —
// an already-decided idea just answers "already decided".
//
// Always returns 200 (except on bad secret) so Telegram doesn't retry-loop.
export async function POST(req: Request) {
  const secret = process.env.TELEGRAM_WEBHOOK_SECRET
  if (!telegramEnabled() || !secret) {
    return NextResponse.json({ ok: true, disabled: true })
  }
  if (req.headers.get("x-telegram-bot-api-secret-token") !== secret) {
    return NextResponse.json({ error: "bad secret" }, { status: 401 })
  }

  const update = await req.json().catch(() => null)
  const cb = update?.callback_query
  const data: string | undefined = cb?.data
  if (!cb?.id || !data?.startsWith("idea:")) {
    return NextResponse.json({ ok: true, ignored: true })
  }

  const [, ideaId, decision] = data.split(":")
  if (!ideaId || !isDecision(decision)) {
    await answerCallback(cb.id, "Unrecognized action.")
    return NextResponse.json({ ok: true, ignored: true })
  }

  try {
    const reviewer = cb.from?.username ? `telegram:${cb.from.username}` : "telegram"
    const result = await applyIdeaDecision(ideaId, decision, reviewer)
    if (result.ok) {
      await answerCallback(cb.id, `Idea ${decision}.`)
      if (cb.message?.chat?.id && cb.message?.message_id) {
        await markMessageDecided(cb.message.chat.id, cb.message.message_id, `${decision === "approved" ? "✅" : "❌"} ${decision} via Telegram by ${reviewer}`)
      }
    } else {
      await answerCallback(cb.id, result.current ? `Already decided: ${result.current}.` : result.error)
    }
  } catch (err) {
    if (!(err instanceof DbNotConfiguredError)) console.error("[api/telegram/webhook]", err)
    await answerCallback(cb.id, "Studio database unavailable — decide in the app.")
  }
  return NextResponse.json({ ok: true })
}
