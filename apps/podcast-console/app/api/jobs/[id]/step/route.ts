import { NextResponse } from "next/server"
import { DbNotConfiguredError } from "@/lib/db"
import { advanceJobStep } from "@/lib/jobs"

export const runtime = "nodejs"
export const maxDuration = 300

// POST /api/jobs/:id/step — run exactly one production step. The client (or a
// worker) keeps calling until job.step === 'done'. Failed steps are retried by
// calling again; completed artifacts are reused from R2.
export async function POST(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await ctx.params
    const result = await advanceJobStep(id)
    if (!result.ok) {
      return NextResponse.json({ error: result.error, job: result.job ?? null }, { status: result.status })
    }
    return NextResponse.json({ job: result.job })
  } catch (err) {
    if (err instanceof DbNotConfiguredError) {
      return NextResponse.json({ error: err.message, dbUnconfigured: true }, { status: 503 })
    }
    console.error("[api/jobs/step]", err)
    return NextResponse.json({ error: "Step execution failed." }, { status: 500 })
  }
}
