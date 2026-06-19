import { NextResponse } from "next/server";
import studioDb from "../../../../lib/studio-db";

// POST /api/studio/archive  — build/refresh the preservation package for a project
// and score its completeness (matrix P4: "a project cannot close until archive
// passes"). Graph-based check; creates an ArchivePackage snapshot.
//
// Body: { externalId, retentionPolicy? }
// Returns: { ok, completenessScore, checks, status }
const WEIGHTS: [string, number][] = [
  ["master_present", 2], ["checksums", 1], ["provenance", 1], ["c2pa", 2],
  ["rights_approved", 2], ["has_takes", 1], ["captions", 1], ["otio_or_projectfile", 1],
];

export async function POST(request: Request) {
  try {
    const { externalId, retentionPolicy } = await request.json();
    if (!externalId) return NextResponse.json({ error: "externalId is required." }, { status: 400 });

    const project = await studioDb.project.findUnique({
      where: { externalId },
      include: { assets: { include: { provenance: true, rightsRecord: true } } },
    });
    if (!project) return NextResponse.json({ error: "Project not found." }, { status: 404 });

    const assets = project.assets;
    const master = assets.filter((a) => a.type === "MASTER").sort((a, b) => +new Date(b.createdAt) - +new Date(a.createdAt))[0];

    const checks: Record<string, boolean> = {
      master_present: !!master,
      checksums: assets.length > 0 && assets.every((a) => !!a.checksum),
      provenance: !!master?.provenance,
      c2pa: !!master?.provenance?.c2paManifestUri,
      rights_approved: !!master?.rightsRecord?.approvedForRelease,
      has_takes: assets.some((a) => a.type === "VIDEO"),
      captions: assets.some((a) => a.type === "SUBTITLE"),
      otio_or_projectfile: assets.some((a) => a.type === "PROJECT_FILE" || a.type === "ARCHIVE"),
    };
    const totalW = WEIGHTS.reduce((s, [, w]) => s + w, 0);
    const gotW = WEIGHTS.reduce((s, [k, w]) => s + (checks[k] ? w : 0), 0);
    const score = Math.round((gotW / totalW) * 1000) / 1000;
    const status = score >= 0.95 ? "APPROVED" : "DRAFT";

    const pkg = await studioDb.archivePackage.create({
      data: {
        project: { connect: { id: project.id } },
        masterAssetId: master?.id ?? null,
        includedAssetIds: assets.map((a) => a.id),
        rightsLedgerSnapshot: master?.rightsRecord ? (master.rightsRecord as any) : undefined,
        provenanceSnapshot: master?.provenance ? (master.provenance as any) : undefined,
        c2paManifestUri: master?.provenance?.c2paManifestUri ?? null,
        retentionPolicy: retentionPolicy ?? "keep 7y · open formats · no DRM",
        completenessScore: score,
        status,
        approval: status === "APPROVED" ? "APPROVED" : "PENDING",
      },
    });

    const missing = WEIGHTS.filter(([k]) => !checks[k]).map(([k]) => k);
    return NextResponse.json({ ok: true, archiveId: pkg.id, completenessScore: score, status, checks, missing }, { status: 201 });
  } catch (error) {
    console.error("studio/archive failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
