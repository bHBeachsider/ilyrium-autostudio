import { NextResponse } from "next/server"
import { DbNotConfiguredError } from "@/lib/db"
import { generateIdeas } from "@/lib/agents/idea-generator"
import { notifyIdeaProposed, telegramEnabled } from "@/lib/telegram"

export const runtime = "nodejs"
export const maxDuration = 120

// POST /api/ideas/generate { count?, prompt? } — on-demand run of the idea agent.
// New proposals land in the review queue as 'proposed'; nothing is produced.
export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}))
    const result = await generateIdeas({ count: body.count, prompt: body.prompt })
    if (telegramEnabled()) {
      // Mirror to Telegram best-effort; failures never block the queue.
      await Promise.allSettled(result.proposed.map((idea) => notifyIdeaProposed(idea)))
    }
    return NextResponse.json(result)
  } catch (err) {
    if (err instanceof DbNotConfiguredError) {
      return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
    }
    console.error("[api/ideas/generate]", err)
    return NextResponse.json({ error: "Idea generation failed." }, { status: 500 })
  }
}
