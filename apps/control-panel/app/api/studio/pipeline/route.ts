import { NextResponse } from "next/server";
import studioDb from "../../../../lib/studio-db";

// /api/studio/pipeline — persist & read the resumable 8-stage pipeline run state
// (full build). The Python engine (studio_pipeline.py) owns the state object; this
// route just stores it on the Project so runs survive restarts and the console can
// read current stage / autonomy / per-stage status.
//
// POST { externalId, pipelineState, pipelineStage?, autonomyMode? }  -> save
// GET  ?externalId=...                                               -> read
export async function POST(request: Request) {
  try {
    const { externalId, pipelineState, pipelineStage, autonomyMode } = await request.json();
    if (!externalId) return NextResponse.json({ error: "externalId is required." }, { status: 400 });

    const project = await studioDb.project.upsert({
      where: { externalId },
      update: {
        pipelineState: pipelineState ?? undefined,
        pipelineStage: pipelineStage ?? undefined,
        autonomyMode: autonomyMode ?? undefined,
      },
      create: {
        externalId, title: externalId, type: "AD",
        pipelineState: pipelineState ?? undefined,
        pipelineStage: pipelineStage ?? undefined,
        autonomyMode: autonomyMode ?? undefined,
      },
    });
    return NextResponse.json({ ok: true, projectId: project.id }, { status: 200 });
  } catch (error) {
    console.error("studio/pipeline POST failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}

export async function GET(request: Request) {
  try {
    const externalId = new URL(request.url).searchParams.get("externalId");
    if (!externalId) return NextResponse.json({ error: "externalId is required." }, { status: 400 });
    const p = await studioDb.project.findUnique({
      where: { externalId },
      select: { pipelineState: true, pipelineStage: true, autonomyMode: true, title: true, type: true },
    });
    if (!p) return NextResponse.json({ error: "Project not found." }, { status: 404 });
    return NextResponse.json({ ok: true, ...p }, { status: 200 });
  } catch (error) {
    console.error("studio/pipeline GET failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
