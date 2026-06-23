import { decide, type Decision, type Policy, type Rating } from "./decide";
import { deriveBlockers } from "../release-gate";

// The distribution spine (DISTRIBUTION_DESIGN.md). distribute()/writeReleases() take the DB via
// deps (no direct lib/studio-db import), and reuse decide() + deriveBlockers() (both pure). v1 is
// SCHEDULED-TERMINAL: it writes status="scheduled" rows and stops — nothing transitions to
// published, published_at stays null. The connector seam (lib/relay/connector.ts) is where the
// deferred worker slice will publish.

export type TargetIntent = { target: string; platform: string; action: "created" | "skipped" };
export type WriteResult = { rows: TargetIntent[] };

export type DistributeResult =
  | { distributed: false; allowed: false; blockers: string[] }
  | { distributed: true; allowed: true; tier: string; policyVersion: string; rows: TargetIntent[] };

/** Minimal Prisma surface for the write path. */
export interface WriteDb {
  release: {
    create(args: {
      data: { masterAssetId: string; projectId: string | null; platform: string; status: string };
    }): Promise<{ id: string }>;
  };
}

/** Minimal Prisma surface for the spine (load master asset + write). */
export interface SpineDb extends WriteDb {
  asset: {
    findUnique(args: { where: { id: string }; include: { rightsRecords: true } }): Promise<any>;
  };
}

const isUniqueViolation = (e: unknown): boolean =>
  typeof e === "object" && e !== null && (e as { code?: string }).code === "P2002";

/**
 * The write contract (§1): for a release-approved asset + its Decision, write one `releases` row
 * per target (`platform` = target verbatim, `status = "scheduled"`), upsert-or-skip on the
 * `(master_asset_id, platform)` partial unique index. v1 is scheduled-terminal (no publish;
 * `published_at` stays null). Returns per-target intent (created vs. skipped).
 */
export async function writeReleases(
  asset: { id: string; projectId: string | null },
  decision: Decision,
  deps: { db: WriteDb },
): Promise<WriteResult> {
  // The partial unique index assumes a non-null master_asset_id; the spine guarantees it (§4).
  if (!asset.id) throw new Error("writeReleases requires a non-null master asset id");

  const rows: TargetIntent[] = [];
  for (const target of decision.targets) {
    const platform = target; // verbatim — no translation layer
    try {
      await deps.db.release.create({
        data: { masterAssetId: asset.id, projectId: asset.projectId ?? null, platform, status: "scheduled" },
      });
      rows.push({ target, platform, action: "created" });
    } catch (e) {
      if (isUniqueViolation(e)) {
        rows.push({ target, platform, action: "skipped" }); // upsert-or-skip: the existing row stands
      } else {
        throw e;
      }
    }
  }
  return { rows };
}

/**
 * The governed spine: load the release-candidate master + its rights, gate (fail-closed), and on
 * `allowed === true` decide() then writeReleases(). Library-only (no route, no worker).
 */
export async function distribute(
  assetId: string,
  deps: { db: SpineDb; policy: Policy },
): Promise<DistributeResult> {
  const asset = await deps.db.asset.findUnique({ where: { id: assetId }, include: { rightsRecords: true } });
  const rights = asset?.rightsRecords?.[0] ?? null;
  const blockers = deriveBlockers(rights);
  if (blockers.length > 0) {
    // Not release-approved → blocked. decide() is NOT called (it throws on allowed!==true).
    return { distributed: false, allowed: false, blockers };
  }

  const decision = decide({ assetId, rating: asset.rating as Rating, allowed: true }, deps.policy);
  const { rows } = await writeReleases({ id: asset.id, projectId: asset.projectId ?? null }, decision, {
    db: deps.db,
  });
  return { distributed: true, allowed: true, tier: decision.tier, policyVersion: decision.policyVersion, rows };
}
