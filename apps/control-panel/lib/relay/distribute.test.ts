import { describe, it, expect, beforeAll } from "vitest";
import studioDb from "../studio-db";
import { distribute, writeReleases } from "./distribute";
import { RELAY_POLICY_V1 } from "./policy";
import { decide } from "./decide";

// INTEGRATION TEST — runs against a Neon DEV branch (DATABASE_URL must point at the
// throwaway `relay-dist-test` branch) with the partial unique index
// `releases_master_asset_platform_uniq` applied. The branch is disposable (deleted at the
// end of the slice), so the test seeds freely and does not tear down.
//
// v1 is SCHEDULED-TERMINAL: distribute() writes `status="scheduled"` rows and stops; nothing
// transitions scheduled->published, so `published_at` stays null. Idempotency is the real DB
// UNIQUE (master_asset_id, platform) exercised via upsert-or-skip.

const rid = () => Math.random().toString(36).slice(2);

const approvedRights = {
  sourceType: "generated",
  licenseType: "pending-review",
  likenessRisk: "none",
  musicRisk: "none",
  trademarkRisk: "none",
  syntheticPerformerFlag: false,
  digitalReplicaFlag: false,
  trainingDataOutboundFlag: false,
  riskLevel: "low",
  releaseRequired: false,
  releaseStatus: "approved",
  approvedForRelease: true,
};
const blockedRights = { ...approvedRights, releaseRequired: true, releaseStatus: "pending", approvedForRelease: false };

let projectId: string;

async function seedAsset(rating: string, approved: boolean): Promise<string> {
  const asset = await studioDb.asset.create({
    data: {
      projectId,
      assetType: "master",
      uri: `test://relay-dist/${rid()}`,
      version: 1,
      rating,
      rightsRecords: { create: approved ? approvedRights : blockedRights },
    },
  });
  return asset.id;
}

async function releasesFor(assetId: string) {
  return studioDb.release.findMany({ where: { masterAssetId: assetId }, orderBy: { platform: "asc" } });
}

beforeAll(async () => {
  const p = await studioDb.project.create({
    data: { title: `relay-dist-test ${rid()}`, type: "short", status: "active", greenlightLevel: "G0" },
  });
  projectId = p.id;
});

describe("distribute spine (v1, scheduled-terminal) — integration", () => {
  it("clean+approved -> 3 scheduled rows, one per target, platform=target, published_at null", async () => {
    const assetId = await seedAsset("clean", true);
    const res = await distribute(assetId, { db: studioDb, policy: RELAY_POLICY_V1 });
    expect(res.distributed).toBe(true);
    if (!res.distributed) return;
    expect(res.tier).toBe("public");
    expect(res.policyVersion).toBe("relay-policy-v1");
    expect(res.rows.map((r) => r.platform).sort()).toEqual(["discord", "public_web", "republic_archive"]);
    expect(res.rows.every((r) => r.action === "created")).toBe(true);

    const rows = await releasesFor(assetId);
    expect(rows.length).toBe(3);
    expect(rows.map((r) => r.platform).sort()).toEqual(["discord", "public_web", "republic_archive"]);
    expect(rows.every((r) => r.status === "scheduled" && r.publishedAt === null)).toBe(true);
    expect(rows.every((r) => r.masterAssetId === assetId && r.projectId === projectId)).toBe(true);
  });

  it("idempotent: re-running writes no duplicate rows (all skipped)", async () => {
    const assetId = await seedAsset("clean", true);
    await distribute(assetId, { db: studioDb, policy: RELAY_POLICY_V1 });
    const res2 = await distribute(assetId, { db: studioDb, policy: RELAY_POLICY_V1 });
    if (!res2.distributed) throw new Error("expected distributed");
    expect(res2.rows.every((r) => r.action === "skipped")).toBe(true);
    expect((await releasesFor(assetId)).length).toBe(3);
  });

  it("not approved -> blocked, decide() not reached, zero rows", async () => {
    const assetId = await seedAsset("clean", false);
    const res = await distribute(assetId, { db: studioDb, policy: RELAY_POLICY_V1 });
    expect(res.distributed).toBe(false);
    if (res.distributed) return;
    expect(res.blockers.length).toBeGreaterThan(0);
    expect((await releasesFor(assetId)).length).toBe(0);
  });
});

describe("writeReleases write contract — integration", () => {
  it("mature -> 2 rows; uncensored -> 1 row (one per target, scheduled)", async () => {
    const matureId = await seedAsset("mature", true);
    const mr = await writeReleases(
      { id: matureId, projectId },
      decide({ assetId: matureId, rating: "mature", allowed: true }, RELAY_POLICY_V1),
      { db: studioDb },
    );
    expect(mr.rows.map((r) => r.platform).sort()).toEqual(["discord", "republic_archive"]);
    expect((await releasesFor(matureId)).length).toBe(2);

    const uncId = await seedAsset("uncensored", true);
    const ur = await writeReleases(
      { id: uncId, projectId },
      decide({ assetId: uncId, rating: "uncensored", allowed: true }, RELAY_POLICY_V1),
      { db: studioDb },
    );
    expect(ur.rows.map((r) => r.platform)).toEqual(["republic_archive"]);
    expect((await releasesFor(uncId)).length).toBe(1);
  });

  it("requires a non-null master asset id (the partial-index assumption)", async () => {
    await expect(
      writeReleases(
        { id: "", projectId },
        decide({ assetId: "x", rating: "clean", allowed: true }, RELAY_POLICY_V1),
        { db: studioDb },
      ),
    ).rejects.toThrow(/non-null|master/i);
  });
});
