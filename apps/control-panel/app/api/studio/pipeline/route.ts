import { NextResponse } from "next/server";
import { getOrCreateProject, findProject } from "../../../../lib/studio-writes";

// /api/studio/pipeline — the real projects table has NO pipeline_state/pipeline_stage/
// autonomy_mode columns (those were idealized). Fork: dropped; a JSON side-table is future
// work. Phase 1 keeps the route functional for project resolution but does NOT persist
// pipeline state (persisted:false), rather than inventing a column outside the locked
// "add only rating" scope.
//
// POST { externalId|title } -> get-or-create project; ack (state not stored)
// GET  ?externalId=...      -> project basics + persisted:false
export async function POST(request: Request) {
  try {
    const { externalId, title } = await request.json();
    const project = await getOrCreateProject({ title: title ?? externalId });
    if (!project) return NextResponse.json({ error: "externalId or title is required." }, { status: 400 });
    return NextResponse.json(
      {
        ok: true,
        projectId: project.id,
        persisted: false,
        note: "Pipeline state is not persisted in Phase 1 (no projects column).",
      },
      { status: 200 },
    );
  } catch (error) {
    console.error("studio/pipeline POST failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}

export async function GET(request: Request) {
  try {
    const sp = new URL(request.url).searchParams;
    const project = await findProject({ title: sp.get("externalId") ?? sp.get("title") });
    if (!project) return NextResponse.json({ error: "Project not found." }, { status: 404 });
    return NextResponse.json(
      { ok: true, projectId: project.id, title: project.title, type: project.type, persisted: false, pipelineState: null },
      { status: 200 },
    );
  } catch (error) {
    console.error("studio/pipeline GET failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
