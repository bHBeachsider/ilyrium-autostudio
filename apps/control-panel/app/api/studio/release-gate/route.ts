import { NextResponse } from "next/server";
import { findProject, findMaster, rightsOf } from "../../../../lib/studio-writes";
import { deriveBlockers } from "../../../../lib/release-gate";

// POST /api/studio/release-gate
// The enforced release gate for a project's release-candidate (master) asset, on the
// REAL risk-based rights_records model. Single source of truth the export/publish path
// consults before anything leaves the vault.
//
// Body: { externalId|title|projectId, uri? } — uri picks a specific master; omitted =>
//        the latest master for the project.
// Returns: { allowed, blockers[], asset, rights }.
//
// Gate rule (fail-closed): allowed iff deriveBlockers() is empty — i.e. the rights
// record exists, approvedForRelease is true, the release status is approved/released
// (when release is required), no *_risk is high, and any synthetic performer has a
// SAG-AFTRA notice on file. approvedForRelease is only set by /api/studio/approve.
export async function POST(request: Request) {
  try {
    const { externalId, title, projectId, uri } = await request.json();

    const project = await findProject({ id: projectId, title: title ?? externalId });
    if (!project) {
      return NextResponse.json(
        { allowed: false, blockers: ["Project not found in the asset graph."], asset: null },
        { status: 200 },
      );
    }

    const asset = await findMaster(project.id, uri);
    if (!asset) {
      return NextResponse.json(
        { allowed: false, blockers: ["No master (release-candidate) asset recorded yet."], asset: null },
        { status: 200 },
      );
    }

    const rights = rightsOf(asset);
    const blockers = deriveBlockers(rights);
    const allowed = blockers.length === 0;

    return NextResponse.json(
      {
        allowed,
        blockers,
        asset: { id: asset.id, uri: asset.uri, assetType: asset.assetType, rating: asset.rating },
        rights: rights ?? null,
      },
      { status: 200 },
    );
  } catch (error) {
    console.error("studio/release-gate failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
