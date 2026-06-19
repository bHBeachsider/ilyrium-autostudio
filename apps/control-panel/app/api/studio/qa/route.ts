import { NextResponse } from "next/server";
import studioDb from "../../../../lib/studio-db";
import { deriveBlockers } from "../../../../lib/release-gate";

// POST /api/studio/qa
// Records the AUTOMATED QA-checklist result on the master asset's RightsRecord
// (Phase A step 5). Sets qaPassed + qaReport + gateEvaluatedAt only — it never
// flips approvedForRelease (that is the human, non-delegable /approve step).
// Creates the RightsRecord if the master predates the auto-create path.
//
// Body: { externalId, checksum?, qaPassed, qaReport }
export async function POST(request: Request) {
  try {
    const { externalId, checksum, qaPassed, qaReport } = await request.json();
    if (!externalId) return NextResponse.json({ error: "externalId is required." }, { status: 400 });

    const project = await studioDb.project.findUnique({ where: { externalId } });
    if (!project) return NextResponse.json({ error: "Project not found." }, { status: 404 });

    const asset = await studioDb.asset.findFirst({
      where: { projectId: project.id, type: "MASTER", ...(checksum ? { checksum } : {}) },
      orderBy: { createdAt: "desc" },
    });
    if (!asset) return NextResponse.json({ error: "No master asset to attach QA to." }, { status: 404 });

    const rights = await studioDb.rightsRecord.upsert({
      where: { assetId: asset.id },
      update: { qaPassed: !!qaPassed, qaReport: qaReport ?? undefined, gateEvaluatedAt: new Date() },
      create: {
        asset: { connect: { id: asset.id } },
        qaPassed: !!qaPassed, qaReport: qaReport ?? undefined, gateEvaluatedAt: new Date(),
        approvedForRelease: false,
      },
    });

    return NextResponse.json(
      { ok: true, qaPassed: rights.qaPassed, blockers: deriveBlockers(rights) },
      { status: 200 },
    );
  } catch (error) {
    console.error("studio/qa failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
