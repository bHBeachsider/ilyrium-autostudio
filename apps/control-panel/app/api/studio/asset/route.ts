import { NextResponse } from "next/server";
import studioDb from "../../../../lib/studio-db";

// POST /api/studio/asset
// Records one rendered asset + its provenance in the asset graph. Content-addressed:
// idempotent on (project, checksum). Self-sufficient — upserts the project so it works
// even before a full /api/studio/sync. This is the provenance backbone (Phase A step 4).
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const {
      externalId, type, uri, checksum, storageProvider, sizeBytes, mimeType,
      provider, model, seed, prompt, sceneNumber, costCents,
    } = body;

    if (!externalId || !uri || !checksum) {
      return NextResponse.json({ error: "externalId, uri and checksum are required." }, { status: 400 });
    }

    // Ensure the project node exists.
    const project = await studioDb.project.upsert({
      where: { externalId },
      update: {},
      create: { externalId, title: externalId, type: "AD" },
    });

    // Dedupe by checksum within the project (idempotent re-runs don't duplicate assets).
    const existing = await studioDb.asset.findFirst({
      where: { projectId: project.id, checksum },
    });
    if (existing) {
      return NextResponse.json({ ok: true, assetId: existing.id, deduped: true }, { status: 200 });
    }

    const assetType = type ?? "VIDEO";
    // Release candidates (the master cut) get a RightsRecord up front, defaulting
    // to approvedForRelease=false. This is the row the enforced release gate
    // (Phase A step 5) checks before any export/publish. Non-master assets don't
    // need one (rights on takes are tracked on Take.rightsStatus).
    const isReleaseCandidate = assetType === "MASTER";

    const asset = await studioDb.asset.create({
      data: {
        project: { connect: { id: project.id } },
        type: assetType,
        uri,
        checksum,
        storageProvider: storageProvider ?? "local",
        sizeBytes: sizeBytes != null ? BigInt(sizeBytes) : undefined,
        mimeType: mimeType ?? undefined,
        provenance: {
          create: {
            modelProvider: provider ?? null,
            modelName: model ?? null,
            seed: seed ?? null,
            generationParams: {
              prompt: prompt ?? null,
              sceneNumber: sceneNumber ?? null,
              costCents: costCents ?? null,
            },
          },
        },
        ...(isReleaseCandidate
          ? { rightsRecord: { create: { approvedForRelease: false } } }
          : {}),
      },
    });

    return NextResponse.json(
      { ok: true, assetId: asset.id, deduped: false, releaseCandidate: isReleaseCandidate },
      { status: 201 },
    );
  } catch (error) {
    console.error("studio/asset failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
