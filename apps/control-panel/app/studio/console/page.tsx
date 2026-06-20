import studioDb from "../../../lib/studio-db";
import { scoreRights } from "../../../lib/risk";
import Workspace from "./Workspace";

// Ilyrium Studio OS — premium film-production console (Phase 1 reconcile). Server
// component: queries the REAL canonical asset graph once (projects/assets/rights_records/
// agent_runs/scenes/shots — no provenance_records/archive_packages, which don't exist),
// serializes it (plain JSON — no Date/BigInt/Prisma objects), and hands it to the client
// Workspace. Assets are addressed by uri (no checksum); asset_type is the lowercase CHECK
// vocab; rights are the risk-based model. Always renders fresh.
export const dynamic = "force-dynamic";

export default async function ConsolePage() {
  const [projects, assetsRecent, rights, runs,
    totalAssets, masterCount, pendingCount, allAssets, renderRuns] = await Promise.all([
    studioDb.project.findMany({
      orderBy: { createdAt: "desc" }, take: 60,
      include: {
        _count: { select: { scenes: true, shots: true, assets: true } },
        scenes: { orderBy: { sceneNumber: "asc" }, include: { shots: { orderBy: { shotNumber: "asc" } } } },
      },
    }),
    studioDb.asset.findMany({ orderBy: { createdAt: "desc" }, take: 120,
      include: { project: { select: { id: true, title: true } } } }),
    studioDb.rightsRecord.findMany({ take: 80,
      include: { asset: { include: { project: { select: { id: true, title: true } } } } } }),
    studioDb.run.findMany({ orderBy: { startedAt: "desc" }, take: 40 }),
    studioDb.asset.count(),
    studioDb.asset.count({ where: { assetType: "master" } }),
    studioDb.rightsRecord.count({ where: { approvedForRelease: false } }),
    studioDb.asset.findMany({ take: 2000, select: { id: true, uri: true, assetType: true, modelId: true } }),
    studioDb.run.findMany({ take: 5000,
      select: { agentName: true, plane: true, humanGateStatus: true, costCents: true, latencyMs: true } }),
  ]);

  // Cost telemetry / Control Plane aggregates (matrix §8). agent_runs is a flat trace row
  // — no entity_type/status/project linkage. Treat completed render/assembly agents as
  // render runs by agentName; humanGateStatus stands in for run health.
  const engine: Record<string, { count: number; cost: number }> = {};
  let estCost = 0, runOk = 0, runFail = 0, renderSeconds = 0, renderCount = 0;
  const SEC = Number(process.env.ILYRIUM_SHOT_DURATION_SEC ?? 8);
  const isRender = (name: string | null) => !!name && /render|assemble|i2v|t2v|video|master/i.test(name);
  for (const r of renderRuns) {
    estCost += r.costCents ?? 0;
    if (r.humanGateStatus === "rejected") runFail++;
    else if (r.humanGateStatus === "approved" || r.humanGateStatus === "auto_approved") runOk++;
    if (isRender(r.agentName)) {
      renderCount++;
      renderSeconds += SEC;
      const k = r.agentName ?? "—";
      engine[k] = engine[k] || { count: 0, cost: 0 };
      engine[k].count++; engine[k].cost += r.costCents ?? 0;
    }
  }
  const engineMix = Object.entries(engine).map(([model, v]) => ({ model, ...v })).sort((a, b) => b.cost - a.cost);
  const costPerRenderSec = renderSeconds ? estCost / renderSeconds : 0;

  // uri-addressed asset map for lineage drill-down (no checksum/provenance graph).
  const assetMap: Record<string, { uri: string; assetType: string | null; model: string | null }> = {};
  for (const a of allAssets) assetMap[a.id] = { uri: a.uri, assetType: a.assetType, model: a.modelId ?? null };

  const projectsOut = projects.map((p) => ({
    id: p.id, title: p.title, type: p.type, status: p.status,
    greenlightLevel: p.greenlightLevel ?? null,
    counts: { scenes: p._count.scenes, shots: p._count.shots, assets: p._count.assets },
    scenes: p.scenes.map((s) => ({
      number: s.sceneNumber ?? 0, title: s.description,
      shots: s.shots.map((sh) => ({ shotNumber: sh.shotNumber, prompt: sh.description })),
    })),
  }));

  const assets = assetsRecent.map((a) => ({
    id: a.id, assetType: a.assetType, uri: a.uri, rating: a.rating,
    projectId: a.project?.id ?? null,
    projectTitle: a.project?.title ?? "—",
    model: a.modelId ?? null,
    sceneNumber: null as number | null,
    createdAt: a.createdAt.toISOString(),
  }));

  const queue = rights
    .map((r) => ({ r, risk: scoreRights(r) }))
    .sort((a, b) => Number(a.r.approvedForRelease) - Number(b.r.approvedForRelease) || b.risk.score - a.risk.score)
    .map(({ r, risk }) => ({
      rightsId: r.id,
      assetId: r.asset?.id ?? null,
      assetUri: r.asset?.uri ?? null,
      projectId: r.asset?.project?.id ?? null,
      projectTitle: r.asset?.project?.title ?? "—",
      approvedForRelease: !!r.approvedForRelease,
      releaseStatus: r.releaseStatus ?? null,
      riskLevel: r.riskLevel ?? null,
      risk,
    }));

  const runRows = runs.map((run) => ({
    id: run.id,
    when: (run.startedAt ?? run.completedAt ?? new Date()).toISOString(),
    humanGateStatus: run.humanGateStatus ?? null,
    agentName: run.agentName, plane: run.plane,
    costCents: run.costCents ?? null,
  }));

  const kpis = {
    totalAssets, masterCount, pendingCount, projects: projects.length,
    estCostCents: estCost, runOk, runFail, renderRuns: renderCount,
    costPerRenderSecCents: Math.round(costPerRenderSec * 100) / 100,
  };

  return (
    <Workspace projects={projectsOut} assets={assets} queue={queue} runs={runRows} assetMap={assetMap}
      kpis={kpis} engineMix={engineMix} />
  );
}
