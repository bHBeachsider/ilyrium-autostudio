import { NextResponse } from "next/server";
import studioDb from "../../../../lib/studio-db";
import { findProject, findMaster, rightsOf, validUserId } from "../../../../lib/studio-writes";
import { deriveBlockers, riskBlockers } from "../../../../lib/release-gate";

// POST /api/studio/approve
// The non-delegable HITL release approval, rewritten onto the REAL governance tables.
// Updates the master's rights_records risk fields from the submitted review, sets
// approvedForRelease ONLY if the substantive risk blockers are clear (or via an explicit,
// logged override), and writes a gate_approvals row (gate_type='release') + an agent_runs
// trace row. Drops the project-level approval/rightsStatus writes (no such columns).
//
// Body: {
//   externalId|title|projectId, uri?, reviewerId?,
//   likenessRisk?, musicRisk?, trademarkRisk?,   // none|low|medium|high
//   riskLevel?,                                  // low|medium|high
//   releaseRequired?, syntheticPerformerFlag?, sagAftraNoticeFiledAt?, legalNotes?,
//   override?, overrideReason?
// }
const RISK = new Set(["none", "low", "medium", "high"]);
const LEVEL = new Set(["low", "medium", "high"]);

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { externalId, title, projectId, uri, reviewerId, override, overrideReason } = body;
    if (override && !overrideReason) {
      return NextResponse.json({ error: "overrideReason is required when override=true." }, { status: 400 });
    }

    const project = await findProject({ id: projectId, title: title ?? externalId });
    if (!project) return NextResponse.json({ error: "Project not found." }, { status: 404 });

    const asset = await findMaster(project.id, uri);
    if (!asset) return NextResponse.json({ error: "No master (release-candidate) asset to approve." }, { status: 404 });

    const cur = rightsOf(asset);

    // Merge submitted risk fields onto the current record (only set provided + CHECK-valid).
    const pick = (v: any, valid: Set<string> | null, fallback: any) =>
      v !== undefined && v !== null && (!valid || valid.has(v)) ? v : fallback;
    const merged: Record<string, any> = {
      likenessRisk: pick(body.likenessRisk, RISK, cur?.likenessRisk ?? "none"),
      musicRisk: pick(body.musicRisk, RISK, cur?.musicRisk ?? "none"),
      trademarkRisk: pick(body.trademarkRisk, RISK, cur?.trademarkRisk ?? "none"),
      riskLevel: pick(body.riskLevel, LEVEL, cur?.riskLevel ?? "low"),
      releaseRequired: body.releaseRequired ?? cur?.releaseRequired ?? true,
      syntheticPerformerFlag: body.syntheticPerformerFlag ?? cur?.syntheticPerformerFlag ?? false,
      sagAftraNoticeFiledAt:
        body.sagAftraNoticeFiledAt !== undefined
          ? body.sagAftraNoticeFiledAt
            ? new Date(body.sagAftraNoticeFiledAt)
            : null
          : cur?.sagAftraNoticeFiledAt ?? null,
      legalNotes: body.legalNotes ?? cur?.legalNotes ?? null,
    };

    // Approve only if the substantive (non-flag) risk blockers are clear — or explicit override.
    const pre = riskBlockers(merged);
    const approvedForRelease = override === true ? true : pre.length === 0;
    const approvedBy = await validUserId(reviewerId);

    const persisted = {
      ...merged,
      approvedForRelease,
      releaseStatus: approvedForRelease ? "approved" : "pending",
      approvedBy,
      approvedAt: approvedForRelease ? new Date() : null,
    };

    // rights_records.asset_id is NOT unique (1:many) — update the existing row, else create one.
    const rights = cur
      ? await studioDb.rightsRecord.update({ where: { id: cur.id }, data: persisted })
      : await studioDb.rightsRecord.create({
          data: { assetId: asset.id, sourceType: "generated", licenseType: "pending-review", ...persisted },
        });

    // Trace the decision: agent_runs row + gate_approvals row (gate_type='release').
    const run = await studioDb.run.create({
      data: {
        agentName: "release-gate",
        plane: "rights",
        humanGateStatus: approvedForRelease ? "approved" : "pending",
        completedAt: new Date(),
      },
    });
    await studioDb.gateApproval.create({
      data: {
        agentRunId: run.id,
        gateType: "release",
        entityType: "asset",
        entityId: asset.id,
        requiredRole: "rights_advisor",
        state: approvedForRelease ? "approved" : "pending",
        resolvedBy: approvedBy,
        resolvedAt: approvedForRelease ? new Date() : null,
        resolutionNote: override ? `override: ${overrideReason}` : null,
        traceReviewed: true,
      },
    });

    return NextResponse.json(
      {
        ok: true,
        approvedForRelease,
        blockers: deriveBlockers(rights),
        overridden: !!override,
        rightsId: rights.id,
        runId: run.id,
      },
      { status: 200 },
    );
  } catch (error) {
    console.error("studio/approve failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
