import { NextResponse } from "next/server";
import studioDb from "../../../../lib/studio-db";

// POST /api/studio/run
// Records a Run/Trace row for a render, assembly, or agent action (matrix P1:
// render-time trace rows). Feeds the Control Plane (cost-per-finished-second,
// provider mix, run health) and the trace timeline. Self-sufficient: upserts the
// project so it works alongside /api/studio/asset.
//
// Body: { externalId, entityType, entityId?, agentName?, provider?, model?, seed?,
//         status?, costCents?, latencyMs?, durationSec?, inputs?, outputs? }
export async function POST(request: Request) {
  try {
    const b = await request.json();
    const { externalId, entityType, entityId, agentName, provider, model, seed,
      status, costCents, latencyMs, durationSec, inputs, outputs } = b;
    if (!externalId || !entityType) {
      return NextResponse.json({ error: "externalId and entityType are required." }, { status: 400 });
    }
    const project = await studioDb.project.upsert({
      where: { externalId }, update: {},
      create: { externalId, title: externalId, type: "AD" },
    });

    const STATUS = new Set(["QUEUED", "RUNNING", "SUCCEEDED", "FAILED"]);
    const run = await studioDb.run.create({
      data: {
        project: { connect: { id: project.id } },
        entityType, entityId: entityId ?? null,
        agentName: agentName ?? model ?? null,
        status: STATUS.has(status) ? status : "SUCCEEDED",
        costCents: costCents != null ? Math.round(costCents) : null,
        latencyMs: latencyMs != null ? Math.round(latencyMs) : null,
        inputs: { provider: provider ?? null, model: model ?? null, seed: seed ?? null,
                  durationSec: durationSec ?? null, ...(inputs ?? {}) },
        outputs: outputs ?? null,
      },
    });
    return NextResponse.json({ ok: true, runId: run.id }, { status: 201 });
  } catch (error) {
    console.error("studio/run failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
