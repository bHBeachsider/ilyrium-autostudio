import { NextResponse } from "next/server"
import { DbNotConfiguredError } from "@/lib/db"
import { createProductionJob } from "@/lib/jobs"

export const runtime = "nodejs"

// POST /api/ideas/:id/produce — create (or resume) the production job for an
// APPROVED idea. The approval gate lives in createProductionJob, in code.
// The actual work happens step-by-step via POST /api/jobs/:id/step.
export async function POST(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await ctx.params
    const result = await createProductionJob(id)
    if (!result.ok) return NextResponse.json({ error: result.error }, { status: result.status })
    return NextResponse.json({ job: result.job, existing: result.existing }, { status: result.existing ? 200 : 201 })
  } catch (err) {
    if (err instanceof DbNotConfiguredError) {
      return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
    }
    console.error("[api/ideas/produce]", err)
    return NextResponse.json({ error: "Failed to start production." }, { status: 500 })
  }
}
