import { NextResponse } from "next/server";
import studioDb from "../../../../lib/studio-db";

// POST /api/studio/c2pa
// Records the content-credentials (C2PA) manifest URI on the master asset's
// ProvenanceRecord (Phase A step 6). Called at export/publish once the manifest
// has been generated (embedded into the master, or written as a sidecar).
//
// Body: { externalId, checksum?, c2paManifestUri, manifest? }
//  - checksum picks a specific master; omitted => most recent MASTER.
//  - manifest (optional) is stashed into generationParams.c2paManifest for audit.
export async function POST(request: Request) {
  try {
    const { externalId, checksum, c2paManifestUri, manifest } = await request.json();
    if (!externalId || !c2paManifestUri) {
      return NextResponse.json({ error: "externalId and c2paManifestUri are required." }, { status: 400 });
    }

    const project = await studioDb.project.findUnique({ where: { externalId } });
    if (!project) return NextResponse.json({ error: "Project not found." }, { status: 404 });

    const asset = await studioDb.asset.findFirst({
      where: { projectId: project.id, type: "MASTER", ...(checksum ? { checksum } : {}) },
      orderBy: { createdAt: "desc" },
      include: { provenance: true },
    });
    if (!asset) return NextResponse.json({ error: "No master asset to attach C2PA to." }, { status: 404 });

    if (asset.provenance) {
      const params = (asset.provenance.generationParams as any) ?? {};
      await studioDb.provenanceRecord.update({
        where: { assetId: asset.id },
        data: {
          c2paManifestUri,
          generationParams: manifest ? { ...params, c2paManifest: manifest } : params,
        },
      });
    } else {
      // Master predates the provenance auto-create path — create it now.
      await studioDb.provenanceRecord.create({
        data: {
          asset: { connect: { id: asset.id } },
          c2paManifestUri,
          generationParams: manifest ? { c2paManifest: manifest } : undefined,
        },
      });
    }

    return NextResponse.json({ ok: true, assetId: asset.id, c2paManifestUri }, { status: 200 });
  } catch (error) {
    console.error("studio/c2pa failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
