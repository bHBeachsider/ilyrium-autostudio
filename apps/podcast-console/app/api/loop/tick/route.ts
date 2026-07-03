import { NextResponse } from "next/server"
import { DbNotConfiguredError } from "@/lib/db"
import { runLoopTick } from "@/lib/loop"

export const runtime = "nodejs"
export const maxDuration = 300

// The continuous idea loop's entry point, driven by a scheduler (Vercel cron,
// scripts/loop.mjs, or manual curl). Guardrails, in order:
//   1. Kill switch: STUDIO_LOOP_ENABLED must be exactly 'true' (default OFF).
//   2. Auth: if LOOP_SECRET is set, require it as a Bearer token (Vercel cron's
//      CRON_SECRET convention uses the same Authorization header).
//   3. The tick itself stops at 'proposed' — it can never produce or publish.
async function handle(req: Request) {
  if (process.env.STUDIO_LOOP_ENABLED !== "true") {
    return NextResponse.json({ skipped: "disabled", hint: "Set STUDIO_LOOP_ENABLED=true to enable the loop." })
  }
  const secret = process.env.LOOP_SECRET
  if (secret && req.headers.get("authorization") !== `Bearer ${secret}`) {
    return NextResponse.json({ error: "Unauthorized." }, { status: 401 })
  }
  try {
    const summary = await runLoopTick()
    return NextResponse.json(summary)
  } catch (err) {
    if (err instanceof DbNotConfiguredError) {
      return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
    }
    console.error("[api/loop/tick]", err)
    return NextResponse.json({ error: err instanceof Error ? err.message : "Tick failed." }, { status: 500 })
  }
}

export async function POST(req: Request) {
  return handle(req)
}

// Vercel cron invokes with GET.
export async function GET(req: Request) {
  return handle(req)
}
