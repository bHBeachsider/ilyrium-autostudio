// Shared studio write helpers — conform every /api/studio/* write to the REAL
// public.* tables and the Ilyrium raw-SQL writer conventions (Phase 1 reconcile).
//
// Identity: projects by id, else get-or-create by title (Fork A); assets dedup by
// uri (Fork B). Every generated asset gets a paired rights_records row, mirroring
// Ilyrium/apps/control-panel/app/api/generate/route.ts. asset_type is normalized to
// the real 8-value lowercase CHECK vocabulary; project.type to its 5-value CHECK.

import studioDb from "./studio-db";

// Real CHECK vocabularies (DB-enforced; we validate here to fail fast with 422/clean defaults).
export const ASSET_TYPES = new Set([
  "image", "video", "voice", "music", "still", "master", "reference", "board",
]);
export const PROJECT_TYPES = new Set(["short", "pilot", "series", "commercial", "feature"]);
export const PLANES = new Set(["concept", "production", "rights", "distribution", "studio_os"]);

/** Lowercase + validate asset_type against the real CHECK vocab. Returns null if invalid. */
export function normalizeAssetType(input: unknown): string | null {
  if (typeof input !== "string") return null;
  const v = input.trim().toLowerCase();
  return ASSET_TYPES.has(v) ? v : null;
}

/** Coerce to a valid project.type (CHECK), defaulting to 'short' (the legacy 'AD' is invalid). */
export function validProjectType(input: unknown): string {
  return typeof input === "string" && PROJECT_TYPES.has(input) ? input : "short";
}

/** Coerce to a valid agent_runs.plane (CHECK), defaulting to 'studio_os'. */
export function validPlane(input: unknown): string {
  return typeof input === "string" && PLANES.has(input) ? input : "studio_os";
}

/**
 * Resolve a project by id, else get-or-create by title (app-level convention — title
 * is not unique — matching Ilyrium's seed-baseline.mjs). Returns null if neither an
 * existing id nor a usable title is provided.
 */
export async function getOrCreateProject(opts: { id?: string | null; title?: string | null; type?: unknown }) {
  if (opts.id) {
    return studioDb.project.findUnique({ where: { id: opts.id } });
  }
  const title = (opts.title ?? "").trim();
  if (!title) return null;
  const existing = await studioDb.project.findFirst({ where: { title } });
  if (existing) return existing;
  return studioDb.project.create({
    data: { title, type: validProjectType(opts.type), status: "active", greenlightLevel: "G0" },
  });
}

/** Resolve a project by id, else by title — WITHOUT creating (for read/decision routes). */
export async function findProject(opts: { id?: string | null; title?: string | null }) {
  if (opts.id) return studioDb.project.findUnique({ where: { id: opts.id } });
  const title = (opts.title ?? "").trim();
  if (!title) return null;
  return studioDb.project.findFirst({ where: { title } });
}

/** Conservative, CHECK-valid default rights for a freshly recorded generated asset (auto-quarantined). */
export function defaultGeneratedRights(modelId?: string | null) {
  return {
    sourceType: "generated",
    modelUsed: modelId ?? null,
    licenseType: "pending-review",
    likenessRisk: "none",
    musicRisk: "none",
    trademarkRisk: "none",
    syntheticPerformerFlag: false,
    digitalReplicaFlag: false,
    trainingDataOutboundFlag: false,
    riskLevel: "medium",
    releaseRequired: true,
    releaseStatus: "pending",
    approvedForRelease: false,
  };
}

/**
 * Create an asset + its paired rights_records row (mirrors the Ilyrium generate route).
 * Dedup is by uri (Fork B): a re-run on the same uri returns the existing asset.
 */
export async function createAssetWithRights(opts: {
  projectId: string;
  assetType: string;
  uri: string;
  modelId?: string | null;
  promptId?: string | null;
  rights?: Record<string, unknown>;
}): Promise<{ asset: any; deduped: boolean }> {
  const existing = await studioDb.asset.findFirst({ where: { uri: opts.uri }, include: { rightsRecords: true } });
  if (existing) return { asset: existing, deduped: true };
  const asset = await studioDb.asset.create({
    data: {
      projectId: opts.projectId,
      assetType: opts.assetType,
      modelId: opts.modelId ?? null,
      promptId: opts.promptId ?? null,
      uri: opts.uri,
      version: 1,
      rightsRecords: { create: { ...defaultGeneratedRights(opts.modelId), ...(opts.rights ?? {}) } },
    },
    include: { rightsRecords: true },
  });
  return { asset, deduped: false };
}

/** The latest release-candidate (master) asset for a project, with its rights record(s). */
export async function findMaster(projectId: string, uri?: string | null) {
  return studioDb.asset.findFirst({
    where: { projectId, assetType: "master", ...(uri ? { uri } : {}) },
    orderBy: { createdAt: "desc" },
    include: { rightsRecords: true },
  });
}

/**
 * The governing rights record for an asset. rights_records.asset_id is NOT unique
 * (1:many), but the writers create exactly one per asset — so take the first.
 */
export function rightsOf(asset: any) {
  return asset?.rightsRecords?.[0] ?? null;
}

/** Return the id only if it is a real users row (approved_by/resolved_by are FKs); else null. */
export async function validUserId(id?: string | null): Promise<string | null> {
  if (!id) return null;
  try {
    const u = await studioDb.user.findUnique({ where: { id } });
    return u ? id : null;
  } catch {
    return null;
  }
}
