import { NextResponse } from "next/server"
import { DbNotConfiguredError, type DistributionChannel } from "@/lib/db"
import { distributeEpisode } from "@/lib/publish"

export const runtime = "nodejs"
export const maxDuration = 300

const CHANNELS: DistributionChannel[] = ["transistor", "sitebox", "youtube", "clips"]

// POST /api/episodes/:id/distribute { channels?: string[] }
// Runs every requested (default: all) enabled channel; per-channel outcomes are
// recorded in podcast_distributions and returned — failures never cascade.
export async function POST(req: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await ctx.params
    const body = await req.json().catch(() => ({}))
    let channels: DistributionChannel[] | undefined
    if (Array.isArray(body.channels)) {
      const requested = (body.channels as string[]).filter((c): c is DistributionChannel =>
        CHANNELS.includes(c as DistributionChannel),
      )
      if (requested.length === 0) {
        return NextResponse.json({ error: `channels must be a subset of ${CHANNELS.join(", ")}` }, { status: 400 })
      }
      channels = requested
    }
    const result = await distributeEpisode(id, channels)
    if (!result.ok) return NextResponse.json({ error: result.error }, { status: result.status })
    return NextResponse.json(result)
  } catch (err) {
    if (err instanceof DbNotConfiguredError) {
      return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
    }
    console.error("[api/episodes/distribute]", err)
    return NextResponse.json({ error: "Distribution failed." }, { status: 500 })
  }
}
