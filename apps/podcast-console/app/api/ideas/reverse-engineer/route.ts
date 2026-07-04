import { NextResponse } from "next/server"
import { DbNotConfiguredError } from "@/lib/db"
import { reverseEngineerArticle } from "@/lib/agents/article-analyst"

export const runtime = "nodejs"
export const maxDuration = 120

// POST /api/ideas/reverse-engineer { url } — deconstruct a competitor article
// and file a differentiated episode idea into the review queue as 'proposed'.
export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}))
    const url = (body.url ?? "").toString().trim()
    let parsed: URL
    try {
      parsed = new URL(url)
    } catch {
      return NextResponse.json({ error: "A valid article URL is required." }, { status: 400 })
    }
    if (!/^https?:$/.test(parsed.protocol)) {
      return NextResponse.json({ error: "Only http(s) URLs are supported." }, { status: 400 })
    }
    const result = await reverseEngineerArticle(url)
    return NextResponse.json(result, { status: 201 })
  } catch (err) {
    if (err instanceof DbNotConfiguredError) {
      return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
    }
    const message = err instanceof Error ? err.message : "Analysis failed."
    console.error("[api/ideas/reverse-engineer]", message)
    // Fetch/extraction problems are the caller's to see (bad URL, paywall).
    const status = /fetch failed|extract readable/i.test(message) ? 422 : 500
    return NextResponse.json({ error: message.slice(0, 300) }, { status })
  }
}
