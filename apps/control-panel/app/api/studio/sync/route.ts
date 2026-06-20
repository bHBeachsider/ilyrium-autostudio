import { NextResponse } from "next/server";
import studioDb from "../../../../lib/studio-db";
import { getOrCreateProject } from "../../../../lib/studio-writes";

// POST /api/studio/sync
// Registers/updates a project + mirrors its scene/shot structure in the REAL tables.
// project get-or-create by title; the idealized scene title/synopsis/orderIndex and shot
// prompt fields are mapped to the real columns scenes(scene_number, description) and
// shots(shot_number, description). Idempotent: replaces the project's scenes/shots.
//
// Body: { externalId|title, type?, status?,
//         scenes: [{ number?, title?, synopsis?, shots: [{ number?, prompt?, description? }] }] }
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { externalId, title, type, status, scenes } = body;
    const projectTitle = title ?? externalId;
    if (!projectTitle) return NextResponse.json({ error: "externalId or title is required." }, { status: 400 });

    const project = await getOrCreateProject({ id: body.projectId, title: projectTitle, type });
    if (!project) return NextResponse.json({ error: "Could not resolve a project." }, { status: 400 });
    if (status) await studioDb.project.update({ where: { id: project.id }, data: { status } });

    if (Array.isArray(scenes)) {
      // Replace the scene/shot structure (shots first — FK to scenes).
      await studioDb.shot.deleteMany({ where: { projectId: project.id } });
      await studioDb.scene.deleteMany({ where: { projectId: project.id } });

      for (let i = 0; i < scenes.length; i++) {
        const sc = scenes[i];
        await studioDb.scene.create({
          data: {
            projectId: project.id,
            sceneNumber: sc.number ?? i + 1,
            description: sc.title ?? sc.synopsis ?? null,
            shots: {
              create: (sc.shots ?? []).map((sh: any, j: number) => ({
                projectId: project.id,
                shotNumber: sh.number ?? j + 1,
                description: sh.prompt ?? sh.description ?? `Shot ${sh.number ?? j + 1}`,
              })),
            },
          },
        });
      }
    }

    const sceneCount = await studioDb.scene.count({ where: { projectId: project.id } });
    return NextResponse.json({ ok: true, projectId: project.id, scenes: sceneCount }, { status: 200 });
  } catch (error) {
    console.error("studio/sync failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
