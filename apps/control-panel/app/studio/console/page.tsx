import studioDb from "../../../lib/studio-db";
import { scoreRights } from "../../../lib/risk";
import Workspace from "./Workspace";

// Ilyrium Studio OS — premium film-production console (Phase C+). Server component:
// queries the canonical asset graph once, serializes it (plain JSON — no Date/BigInt/
// Prisma objects), and hands it to the client Workspace, which presents four
// functional domains (Scripting · Generation · Assembly · Analytics) in a fixed,
// workspace-driven layout. Always renders fresh.
export const dynamic = "force-dynamic";

export default async function ConsolePage() {
  const [projects, assetsRecent, rights, runs,
    totalAssets, provCount, c2paCount, masterCount, pendingCount, allAssets,
    renderRuns, archivesRaw] = await Promise.all([
    studioDb.project.findMany({
      orderBy: { updatedAt: "desc" }, take: 60,
      include: {
        _count: { select: { scenes: true, shots: true, assets: true } },
        scenes: { orderBy: { orderIndex: "asc" }, include: { shots: { orderBy: { shotNumber: "asc" } } } },
      },
    }),
    studioDb.asset.findMany({ orderBy: { createdAt: "desc" }, take: 120,
      include: { provenance: true, project: { select: { externalId: true, title: true } } } }),
    studioDb.rightsRecord.findMany({ take: 80,
      include: { asset: { include: { project: { select: { externalId: true, title: true } } } } } }),
    studioDb.run.findMany({ orderBy: { createdAt: "desc" }, take: 40, include: { project: { select: { externalId: true } } } }),
    studioDb.asset.count(),
    studioDb.provenanceRecord.count(),
    studioDb.provenanceRecord.count({ where: { c2paManifestUri: { not: null } } }),
    studioDb.asset.count({ where: { type: "MASTER" } }),
    studioDb.rightsRecord.count({ where: { approvedForRelease: false } }),
    studioDb.asset.findMany({ take: 2000, select: { id: true, checksum: true, type: true, provenance: { select: { modelName: true } } } }),
    studioDb.run.findMany({ where: { entityType: { in: ["render", "assemble"] } }, take: 5000,
      select: { entityType: true, agentName: true, status: true, costCents: true, latencyMs: true,
                project: { select: { externalId: true } } } }),
    studioDb.archivePackage.findMany({ orderBy: { createdAt: "desc" }, take: 80,
      select: { completenessScore: true, status: true, approval: true, project: { select: { externalId: true } } } }),
  ]);

  // Cost telemetry / Control Plane aggregates (matrix §8).
  const engine: Record<string, { count: number; cost: number }> = {};
  let estCost = 0, runOk = 0, runFail = 0, renderSeconds = 0;
  const SEC = Number(process.env.ILYRIUM_SHOT_DURATION_SEC ?? 8);
  for (const r of renderRuns) {
    estCost += r.costCents ?? 0;
    if (r.status === "SUCCEEDED") runOk++; else if (r.status === "FAILED") runFail++;
    if (r.entityType === "render") {
      renderSeconds += SEC;
      const k = r.agentName ?? "—";
      engine[k] = engine[k] || { count: 0, cost: 0 };
      engine[k].count++; engine[k].cost += r.costCents ?? 0;
    }
  }
  const engineMix = Object.entries(engine).map(([model, v]) => ({ model, ...v })).sort((a, b) => b.cost - a.cost);
  const costPerRenderSec = renderSeconds ? estCost / renderSeconds : 0;
  // Archive completeness by project externalId (latest package wins; list is newest-first).
  const archiveByProject: Record<string, number> = {};
  for (const a of archivesRaw) { const e = a.project?.externalId; if (e && !(e in archiveByProject)) archiveByProject[e] = a.completenessScore ?? 0; }

  const assetMap: Record<string, { checksum: string | null; type: string; model: string | null }> = {};
  for (const a of allAssets) assetMap[a.id] = { checksum: a.checksum, type: a.type, model: a.provenance?.modelName ?? null };

  const projectsOut = projects.map((p) => ({
    id: p.id, externalId: p.externalId, title: p.title, type: p.type, status: p.status,
    rightsStatus: p.rightsStatus, approval: p.approval,
    counts: { scenes: p._count.scenes, shots: p._count.shots, assets: p._count.assets },
    kernel: (p.styleKernel as any)?.name ?? null,
    scenes: p.scenes.map((s) => ({
      number: s.orderIndex, title: s.title,
      shots: s.shots.map((sh) => ({ shotNumber: sh.shotNumber, prompt: sh.prompt })),
    })),
  }));

  const assets = assetsRecent.map((a) => ({
    id: a.id, type: a.type, checksum: a.checksum,
    projectExternalId: a.project?.externalId ?? null,
    projectTitle: a.project?.title ?? a.project?.externalId ?? "—",
    model: a.provenance?.modelName ?? null, provider: a.provenance?.modelProvider ?? null,
    seed: a.provenance?.seed ?? null,
    prompt: (a.provenance?.generationParams as any)?.prompt ?? null,
    sceneNumber: (a.provenance?.generationParams as any)?.sceneNumber ?? null,
    upstreamIds: a.provenance?.upstreamAssetIds ?? [],
    c2pa: !!a.provenance?.c2paManifestUri,
    createdAt: a.createdAt.toISOString(),
  }));

  const queue = rights
    .map((r) => ({ r, risk: scoreRights(r) }))
    .sort((a, b) => Number(a.r.approvedForRelease) - Number(b.r.approvedForRelease) || b.risk.score - a.risk.score)
    .map(({ r, risk }) => ({
      rightsId: r.id, assetChecksum: r.asset?.checksum ?? null,
      projectExternalId: r.asset?.project?.externalId ?? null,
      projectTitle: r.asset?.project?.title ?? "—",
      approvedForRelease: r.approvedForRelease, reviewerId: r.reviewerId,
      qaPassed: r.qaPassed, noLikenessConfirmed: r.noLikenessConfirmed, risk,
    }));

  const runRows = runs.map((run) => ({
    id: run.id, when: run.createdAt.toISOString(), status: run.status,
    agentName: run.agentName, entityType: run.entityType, approvedBy: run.approvedBy,
    costCents: run.costCents ?? null, projectExternalId: run.project?.externalId ?? null,
  }));

  const kpis = {
    totalAssets, provCount, c2paCount, masterCount, pendingCount, projects: projects.length,
    estCostCents: estCost, runOk, runFail, renderRuns: renderRuns.length,
    costPerRenderSecCents: Math.round(costPerRenderSec * 100) / 100,
  };

  return (
    <Workspace projects={projectsOut} assets={assets} queue={queue} runs={runRows} assetMap={assetMap}
      kpis={kpis} engineMix={engineMix} archiveByProject={archiveByProject} />
  );
}
