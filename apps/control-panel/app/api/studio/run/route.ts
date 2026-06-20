import { NextResponse } from "next/server";
import studioDb from "../../../../lib/studio-db";
import { validPlane } from "../../../../lib/studio-writes";

// POST /api/studio/run
// Records an agent_runs trace row for a render/assembly/agent action. Maps onto the REAL
// agent_runs columns (agent_name, plane, model_used, tokens, cost/latency,
// human_gate_status, started/completed). The idealized project_id/entity/inputs/outputs
// are dropped — agent_runs is a flat trace row; entity linkage lives in gate_approvals.
//
// Body: { agentName|model, plane?, model?, tokensIn?, tokensOut?, costCents?, latencyMs?,
//         humanGateStatus?, inputRef?, outputRef? }
const GATE = new Set(["pending", "approved", "rejected", "auto_approved", "timeout", "revision_requested"]);

export async function POST(request: Request) {
  try {
    const b = await request.json();
    const agentName = b.agentName ?? b.model ?? b.agent;
    if (!agentName) return NextResponse.json({ error: "agentName is required." }, { status: 400 });

    const run = await studioDb.run.create({
      data: {
        agentName,
        plane: validPlane(b.plane),
        modelUsed: b.model ?? null,
        inputRef: b.inputRef ?? null,
        outputRef: b.outputRef ?? null,
        tokensIn: b.tokensIn != null ? Math.round(b.tokensIn) : null,
        tokensOut: b.tokensOut != null ? Math.round(b.tokensOut) : null,
        costCents: b.costCents != null ? Math.round(b.costCents) : null,
        latencyMs: b.latencyMs != null ? Math.round(b.latencyMs) : null,
        humanGateStatus: GATE.has(b.humanGateStatus) ? b.humanGateStatus : null,
        completedAt: new Date(),
      },
    });
    return NextResponse.json({ ok: true, runId: run.id }, { status: 201 });
  } catch (error) {
    console.error("studio/run failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
