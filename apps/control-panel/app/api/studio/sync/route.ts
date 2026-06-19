import { NextResponse } from "next/server";
// Studio asset-graph client (separate from the campaign client). Four levels up to lib/.
import studioDb from "../../../../lib/studio-db";

// POST /api/studio/sync
// Registers/updates a project in the canonical asset graph (the `studio` Postgres schema).
// Idempotent on `externalId` (auto-studio campaign_id or scaffold slug). Mirrors the
// project's scene/shot structure (a non-destructive cache of project.json). Takes,
// assets, and provenance are written at render time (Phase A step 4), not here.
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { externalId, title, type, styleKernel, scaffoldPath, status, scenes } = body;

    if (!externalId || !title) {
      return NextResponse.json({ error: "externalId and title are required." }, { status: 400 });
    }

    const project = await studioDb.project.upsert({
      where: { externalId },
      update: {
        title,
        type: type ?? undefined,
        styleKernel: styleKernel ?? undefined,
        scaffoldPath: scaffoldPath ?? undefined,
        status: status ?? undefined,
      },
      create: {
        externalId,
        title,
        type: type ?? "AD",
        styleKernel: styleKernel ?? undefined,
        scaffoldPath: scaffoldPath ?? undefined,
      },
    });

    // Replace the scene/shot structure to mirror the current project.json (idempotent).
    if (Array.isArray(scenes)) {
      await studioDb.shot.deleteMany({ where: { projectId: project.id } });
      await studioDb.scene.deleteMany({ where: { projectId: project.id } });

      for (const sc of scenes) {
        await studioDb.scene.create({
          data: {
            project: { connect: { id: project.id } },
            title: sc.title ?? null,
            synopsis: sc.synopsis ?? null,
            orderIndex: sc.number ?? 0,
            shots: {
              create: (sc.shots ?? []).map((sh: any) => ({
                project: { connect: { id: project.id } },
                shotNumber: sh.number ?? 0,
                prompt: sh.prompt ?? null,
              })),
            },
          },
        });
      }
    }

    const sceneCount = await studioDb.scene.count({ where: { projectId: project.id } });
    return NextResponse.json(
      { ok: true, projectId: project.id, externalId, scenes: sceneCount },
      { status: 200 },
    );
  } catch (error) {
    console.error("studio/sync failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
