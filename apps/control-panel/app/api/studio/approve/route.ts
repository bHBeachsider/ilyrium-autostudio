import { NextResponse } from "next/server";
import studioDb from "../../../../lib/studio-db";
import { deriveBlockers } from "../../../../lib/release-gate";

// POST /api/studio/approve
// The non-delegable HITL release approval (Phase A step 5). Records the QA
// result + the no-likeness legal confirmation + rights states against the
// master asset's RightsRecord, then sets approvedForRelease ONLY if the gate
// rule is satisfied — or via an explicit, logged override. Writes a Run row so
// every release decision is traceable (KPI: approvals with stored trace).
//
// Body: {
//   externalId, checksum?,
//   reviewerId,
//   qaPassed?, qaReport?,            // from run_release_qa
//   noLikenessConfirmed?,            // the legal gate (human-confirmed)
//   sourceMaterialState?, likenessState?, voiceState?, musicLicenseState?, vendorTermsState?,
//   consentDocumentUri?, notes?,
//   override?, overrideReason?       // explicit human override (logged)
// }
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const {
      externalId, checksum, reviewerId,
      qaPassed, qaReport, noLikenessConfirmed,
      sourceMaterialState, likenessState, voiceState, musicLicenseState, vendorTermsState,
      consentDocumentUri, notes, override, overrideReason,
    } = body;

    if (!externalId) return NextResponse.json({ error: "externalId is required." }, { status: 400 });
    if (!reviewerId) return NextResponse.json({ error: "reviewerId is required (non-delegable HITL gate)." }, { status: 400 });
    if (override && !overrideReason) {
      return NextResponse.json({ error: "overrideReason is required when override=true." }, { status: 400 });
    }

    const project = await studioDb.project.findUnique({ where: { externalId } });
    if (!project) return NextResponse.json({ error: "Project not found." }, { status: 404 });

    const asset = await studioDb.asset.findFirst({
      where: { projectId: project.id, type: "MASTER", ...(checksum ? { checksum } : {}) },
      orderBy: { createdAt: "desc" },
      include: { rightsRecord: true },
    });
    if (!asset) return NextResponse.json({ error: "No master (release-candidate) asset to approve." }, { status: 404 });

    // Merge the submitted review onto the existing record (only set provided fields).
    const set = (v: any, cur: any) => (v !== undefined && v !== null ? v : cur);
    const cur = asset.rightsRecord;
    const merged = {
      qaPassed: set(qaPassed, cur?.qaPassed ?? false),
      qaReport: set(qaReport, cur?.qaReport ?? undefined),
      noLikenessConfirmed: set(noLikenessConfirmed, cur?.noLikenessConfirmed ?? false),
      sourceMaterialState: set(sourceMaterialState, cur?.sourceMaterialState ?? "UNREVIEWED"),
      likenessState: set(likenessState, cur?.likenessState ?? "UNREVIEWED"),
      voiceState: set(voiceState, cur?.voiceState ?? "UNREVIEWED"),
      musicLicenseState: set(musicLicenseState, cur?.musicLicenseState ?? "UNREVIEWED"),
      vendorTermsState: set(vendorTermsState, cur?.vendorTermsState ?? "UNREVIEWED"),
      consentDocumentUri: set(consentDocumentUri, cur?.consentDocumentUri ?? undefined),
      overrideReason: override ? overrideReason : (cur?.overrideReason ?? null),
      notes: set(notes, cur?.notes ?? undefined),
    };

    // Re-derive blockers from the MERGED state; approve only if clear (or override).
    const blockers = deriveBlockers(merged);
    const approvedForRelease = override === true ? true : blockers.length === 0;

    const rights = await studioDb.rightsRecord.upsert({
      where: { assetId: asset.id },
      update: {
        ...merged, approvedForRelease, reviewerId, reviewedAt: new Date(), gateEvaluatedAt: new Date(),
      },
      create: {
        asset: { connect: { id: asset.id } },
        ...merged, approvedForRelease, reviewerId, reviewedAt: new Date(), gateEvaluatedAt: new Date(),
      },
    });

    // Trace the decision.
    await studioDb.run.create({
      data: {
        project: { connect: { id: project.id } },
        entityType: "release_gate",
        entityId: asset.id,
        agentName: "release-gate",
        status: "SUCCEEDED",
        approvalRequired: true,
        approvedBy: reviewerId,
        inputs: { checksum: asset.checksum, override: !!override, overrideReason: overrideReason ?? null },
        outputs: { approvedForRelease, blockers },
      },
    });

    // Reflect onto the project for console at-a-glance status.
    await studioDb.project.update({
      where: { id: project.id },
      data: {
        approval: approvedForRelease ? "APPROVED" : "PENDING",
        rightsStatus: approvedForRelease ? "CLEARED" : "PENDING",
      },
    });

    return NextResponse.json(
      { ok: true, approvedForRelease, blockers, overridden: !!override, rightsId: rights.id },
      { status: 200 },
    );
  } catch (error) {
    console.error("studio/approve failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
