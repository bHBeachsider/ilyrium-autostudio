import { NextResponse } from "next/server";
import studioDb from "../../../../lib/studio-db";
import { findProject, rightsOf } from "../../../../lib/studio-writes";
import { scoreRights } from "../../../../lib/risk";

// GET /api/studio/queue
// The risk-scored approval queue (Phase B), on the REAL assets/rights_records tables.
// Lists release-candidate (master) assets + their rights state with a computed risk
// score + autonomy tier, so a human can triage the non-delegable A4 release decision.
//
// Query: ?status=pending(default)|all  ?externalId/title  ?projectId  ?limit=50
export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const status = url.searchParams.get("status") ?? "pending";
    const externalId = url.searchParams.get("externalId") ?? url.searchParams.get("title");
    const projectId = url.searchParams.get("projectId");
    const limit = Math.min(parseInt(url.searchParams.get("limit") ?? "50", 10) || 50, 200);

    let project = null;
    if (projectId || externalId) {
      project = await findProject({ id: projectId, title: externalId });
      if (!project) return NextResponse.json({ count: 0, summary: { pending: 0, high: 0 }, queue: [] }, { status: 200 });
    }

    const masters = await studioDb.asset.findMany({
      where: { assetType: "master", ...(project ? { projectId: project.id } : {}) },
      orderBy: { createdAt: "desc" },
      take: 500,
      include: { rightsRecords: true, project: { select: { id: true, title: true, type: true } } },
    });

    let items = masters.map((a: any) => {
      const r = rightsOf(a);
      const risk = scoreRights(r);
      const approved = !!r?.approvedForRelease;
      return {
        assetId: a.id,
        uri: a.uri,
        rating: a.rating,
        projectId: a.project?.id,
        projectTitle: a.project?.title,
        projectType: a.project?.type,
        createdAt: a.createdAt,
        approvedForRelease: approved,
        releaseStatus: r?.releaseStatus ?? null,
        riskLevel: r?.riskLevel ?? null,
        risk: risk.score,
        tier: risk.tier,
        severity: risk.severity,
        factors: risk.factors,
        action: approved ? "released" : "needs A4 release decision",
      };
    });

    if (status === "pending") items = items.filter((i) => !i.approvedForRelease);
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
