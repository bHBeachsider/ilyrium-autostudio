import { NextResponse } from "next/server";
import studioDb from "../../../../lib/studio-db";
import { findProject, findMaster } from "../../../../lib/studio-writes";

// POST /api/studio/qa
// Records the automated QA result for the master asset as a gate_approvals row
// (gate_type='qa') + an agent_runs trace row. The real rights_records has no
// qa_passed/qa_report columns — QA lives in the gate ledger. Never flips
// approvedForRelease (that is the human, non-delegable /approve step).
//
// Body: { externalId|title|projectId, uri?, passed, report? }
export async function POST(request: Request) {
  try {
    const { externalId, title, projectId, uri, passed, report } = await request.json();

    const project = await findProject({ id: projectId, title: title ?? externalId });
    if (!project) return NextResponse.json({ error: "Project not found." }, { status: 404 });

    const asset = await findMaster(project.id, uri);
    if (!asset) return NextResponse.json({ error: "No master asset to attach QA to." }, { status: 404 });

    const state = passed ? "approved" : "rejected";
    const run = await studioDb.run.create({
      data: { agentName: "qa", plane: "production", humanGateStatus: "auto_approved", completedAt: new Date() },
    });
    const gate = await studioDb.gateApproval.create({
      data: {
        agentRunId: run.id,
        gateType: "qa",
        entityType: "asset",
        entityId: asset.id,
        requiredRole: "editor",
        state,
        resolutionNote: typeof report === "string" ? report : report ? JSON.stringify(report) : null,
        resolvedAt: new Date(),
        traceReviewed: true,
      },
    });
    return NextResponse.json({ ok: true, qaState: state, gateId: gate.id }, { status: 200 });
  } catch (error) {
    console.error("studio/qa failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
