import { NextResponse } from "next/server";
import studioDb from "../../../../lib/studio-db";
import { scoreRights } from "../../../../lib/risk";

// GET /api/studio/queue
// The risk-scored approval queue (Phase B). Lists release-candidate (MASTER)
// assets and their rights state, with a computed risk score + autonomy tier, so
// a human can triage what needs the non-delegable A4 release decision first.
//
// Query params:
//   ?status=pending (default) | all   — pending hides already-approved masters
//   ?externalId=<project>             — restrict to one project
//   ?limit=50
export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const status = url.searchParams.get("status") ?? "pending";
    const externalId = url.searchParams.get("externalId");
    const limit = Math.min(parseInt(url.searchParams.get("limit") ?? "50", 10) || 50, 200);

    const project = externalId
      ? await studioDb.project.findUnique({ where: { externalId } })
      : null;
    if (externalId && !project) {
      return NextResponse.json({ queue: [], count: 0 }, { status: 200 });
    }

    const masters = await studioDb.asset.findMany({
      where: { type: "MASTER", ...(project ? { projectId: project.id } : {}) },
      orderBy: { createdAt: "desc" },
      take: 500,
      include: { rightsRecord: true, project: { select: { externalId: true, title: true, type: true } } },
    });

    let items = masters.map((a) => {
      const risk = scoreRights(a.rightsRecord);
      const approved = !!a.rightsRecord?.approvedForRelease;
      return {
        assetId: a.id,
        checksum: a.checksum,
        project: a.project?.externalId,
        projectTitle: a.project?.title,
        projectType: a.project?.type,
        createdAt: a.createdAt,
        approvedForRelease: approved,
        qaPassed: !!a.rightsRecord?.qaPassed,
        noLikenessConfirmed: !!a.rightsRecord?.noLikenessConfirmed,
        risk: risk.score,
        tier: risk.tier,
        severity: risk.severity,
        factors: risk.factors,
        // What to do next.
        action: approved ? "released" : "needs A4 release decision",
      };
    });

    if (status === "pending") items = items.filter((i) => !i.approvedForRelease);

    // Highest risk first; ties broken by oldest (waiting longest).
    items.sort((a, b) => b.risk - a.risk || +new Date(a.createdAt) - +new Date(b.createdAt));
    items = items.slice(0, limit);

    const summary = {
      pending: items.filter((i) => !i.approvedForRelease).length,
      high: items.filter((i) => i.severity === "high").length,
    };
    return NextResponse.json({ count: items.length, summary, queue: items }, { status: 200 });
  } catch (error) {
    console.error("studio/queue failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
