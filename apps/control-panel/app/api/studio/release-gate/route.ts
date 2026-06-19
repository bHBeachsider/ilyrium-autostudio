import { NextResponse } from "next/server";
import studioDb from "../../../../lib/studio-db";
import { deriveBlockers } from "../../../../lib/release-gate";

// POST /api/studio/release-gate
// Evaluates the ENFORCED release gate (Phase A step 5) for a project's
// release-candidate (MASTER) asset. This is the single source of truth the
// export/publish path consults before anything leaves the vault.
//
// Body: { externalId, checksum? }  — checksum picks a specific master; omitted
//        => the most recent MASTER asset for the project.
// Returns: { allowed, blockers[], rights, asset }.
//
// Gate rule: a master is releasable iff its RightsRecord.approvedForRelease is
// true. That flag is only set true by /api/studio/approve when the no-likeness
// legal gate + QA pass and no applicable rights state is blocking — OR via an
// explicit, logged human override. The gate here re-derives the blockers so the
// caller (and console) can see exactly what's outstanding. Fail-closed: an
// unknown/absent record is NOT allowed.

export async function POST(request: Request) {
  try {
    const { externalId, checksum } = await request.json();
    if (!externalId) {
      return NextResponse.json({ error: "externalId is required." }, { status: 400 });
    }

    const project = await studioDb.project.findUnique({ where: { externalId } });
    if (!project) {
      return NextResponse.json(
        { allowed: false, blockers: ["Project not found in the asset graph."], asset: null },
        { status: 200 },
      );
    }

    const asset = await studioDb.asset.findFirst({
      where: { projectId: project.id, type: "MASTER", ...(checksum ? { checksum } : {}) },
      orderBy: { createdAt: "desc" },
      include: { rightsRecord: true },
    });
    if (!asset) {
      return NextResponse.json(
        { allowed: false, blockers: ["No master (release-candidate) asset recorded yet."], asset: null },
        { status: 200 },
      );
    }

    const blockers = deriveBlockers(asset.rightsRecord);
    // Fail-closed: allowed requires the persisted flag AND zero derived blockers.
    const allowed = !!asset.rightsRecord?.approvedForRelease && blockers.length === 0;

    return NextResponse.json(
      {
        allowed,
        blockers,
        asset: { id: asset.id, checksum: asset.checksum, uri: asset.uri, type: asset.type },
        rights: asset.rightsRecord ?? null,
      },
      { status: 200 },
    );
  } catch (error) {
    console.error("studio/release-gate failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
