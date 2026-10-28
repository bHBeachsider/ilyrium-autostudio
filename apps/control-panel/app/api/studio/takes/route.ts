import { NextResponse } from "next/server";
import takesDb from "../../../../lib/takes-db";
import { appendLedgerEntry, verifyChain } from "../../../../lib/ledger";

// POST /api/studio/takes
// Registers one candidate take (image/video frame) for a shot.
// Takes are append-only: hidden=true is the only suppression mechanism.
//
// Body: { shotId, songId, sceneNumber, model?, publicUrl }
// Returns: { takeId, c2paStatus, chain_ok }
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { shotId, songId, sceneNumber, model, publicUrl } = body ?? {};

    if (!shotId || typeof shotId !== "string") {
      return NextResponse.json({ error: "shotId is required." }, { status: 400 });
    }
    if (!songId || typeof songId !== "string") {
      return NextResponse.json({ error: "songId is required." }, { status: 400 });
    }
    if (sceneNumber === undefined || sceneNumber === null || typeof sceneNumber !== "number") {
      return NextResponse.json({ error: "sceneNumber (number) is required." }, { status: 400 });
    }
    if (!publicUrl || typeof publicUrl !== "string") {
      return NextResponse.json({ error: "publicUrl is required." }, { status: 400 });
    }

    // c2paStatus: "valid" when a model is recorded (provenance traceable), else "missing"
    const c2paStatus = model ? "valid" : "missing";

    const take = await takesDb.take.create({
      data: { shotId, songId, sceneNumber, model: model ?? null, publicUrl, c2paStatus },
    });

    const entry = appendLedgerEntry(songId, "take_registered", {
      takeId: take.id,
      shotId,
      sceneNumber,
      model: model ?? null,
      c2paStatus,
    });

    const chain_ok = verifyChain(songId);

    return NextResponse.json(
      { takeId: take.id, c2paStatus, chain_ok, ledgerSeq: entry.seq },
      { status: 201 },
    );
  } catch (error) {
    console.error("studio/takes POST failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}

// GET /api/studio/takes?songId=<id>
// Returns all non-hidden takes for a songId, grouped by shotId.
export async function GET(request: Request) {
  try {
    const songId = new URL(request.url).searchParams.get("songId");
    if (!songId) {
      return NextResponse.json({ error: "songId query param is required." }, { status: 400 });
    }

    const rows = await takesDb.take.findMany({
      where: { songId, hidden: false },
      orderBy: { createdAt: "asc" },
    });

    // Group by shotId
    const byShot: Record<string, typeof rows> = {};
    for (const take of rows) {
      if (!byShot[take.shotId]) byShot[take.shotId] = [];
      byShot[take.shotId].push(take);
    }

    return NextResponse.json({ songId, count: rows.length, shots: byShot }, { status: 200 });
  } catch (error) {
    console.error("studio/takes GET failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
