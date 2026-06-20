import { NextResponse } from "next/server";
import { getOrCreateProject, normalizeAssetType, createAssetWithRights } from "../../../../lib/studio-writes";

// POST /api/studio/asset
// Records one generated asset (+ paired rights_records) in the REAL asset graph,
// conforming to the Ilyrium raw-SQL writer: project get-or-create by title, asset_type
// normalized to the lowercase CHECK vocab (422 on anything outside the 8 values), dedup
// by uri. The idealized checksum/storageProvider/sizeBytes/mimeType/provenance fields
// are dropped (no such columns); provenance is normalized via model_id/prompt_id.
//
// Body: { externalId|title|projectId, type, uri, model?, provider? }
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { externalId, title, projectId, type, uri, model, provider } = body;

    if (!uri) return NextResponse.json({ error: "uri is required." }, { status: 400 });

    const assetType = normalizeAssetType(type);
    if (!assetType) {
      return NextResponse.json(
        { error: `asset_type '${type}' is not one of image|video|voice|music|still|master|reference|board.` },
        { status: 422 },
      );
    }

    const project = await getOrCreateProject({ id: projectId, title: title ?? externalId, type: body.projectType });
    if (!project) {
      return NextResponse.json(
        { error: "Could not resolve a project (provide projectId, or externalId/title)." },
        { status: 400 },
      );
    }

    const { asset, deduped } = await createAssetWithRights({
      projectId: project.id,
      assetType,
      uri,
      modelId: model ?? provider ?? null,
    });

    return NextResponse.json(
      {
        ok: true,
        assetId: asset.id,
        projectId: project.id,
        assetType,
        deduped,
        releaseCandidate: assetType === "master",
      },
      { status: deduped ? 200 : 201 },
    );
  } catch (error) {
    console.error("studio/asset failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
