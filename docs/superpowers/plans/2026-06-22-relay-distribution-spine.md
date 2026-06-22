# Relay Distribution Spine (Slice 2 v1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the governed distribution spine — for a release-approved asset, compose release-gate → `decide()` → persist `releases` rows → dispatch through a `Connector` boundary (stub), driving each row `scheduled → published/failed`.

**Architecture:** One new pure-orchestration function `distribute(assetId, deps)` plus a `Connector` boundary. `deps` injects the DB, policy, connectors, and a clock, so the whole thing is unit-testable with zero network/DB. Reuses `decide()` (pure) and `deriveBlockers()` (pure) unchanged. The `releases` table — today dead schema — becomes live; real connectors / a worker / scheduling / the paywall are out of scope.

**Tech Stack:** TypeScript, Next 14.2.3, Prisma 7.8 (`studioDb` client), Vitest (already configured; `npm test` → `vitest run`).

**Design source:** `apps/control-panel/docs/relay/DISTRIBUTION_DESIGN.md` (approved 2026-06-22).

## Global Constraints

- All new files live in `apps/control-panel/lib/relay/`. Run all commands from `apps/control-panel/`.
- Reuse UNCHANGED: `lib/relay/decide.ts`, `lib/relay/policy.ts` (`RELAY_POLICY_V1`), `lib/release-gate.ts` (`deriveBlockers`).
- **`distribute.ts` must NOT import from `lib/studio-writes.ts` or `lib/studio-db.ts`** — those eagerly instantiate the Prisma singleton (`studio-db.ts` throws without `DATABASE_URL`). Inline the trivial `rightsOf` (`asset?.rightsRecords?.[0] ?? null`); take the DB via the injected `deps.db`.
- `platform` column = the `Target` id **verbatim** (`public_web` / `discord` / `republic_archive`). No translation layer.
- Idempotent by `(master_asset_id, platform)` — advisory check-then-insert; **no schema change** in v1 (the `UNIQUE` index is a documented fast-follow).
- **Library-only**: no API route, no approve-flow wiring in v1.
- Out of scope: real connectors, Graphile Worker, `scheduled_at` future-dating, retries, paywall.
- Tests are DB-free (injected fake `db`); prefix test commands with `unset DATABASE_URL NODE_ENV` for a clean shell.

---

### Task 1: Connector boundary (`connector.ts`)

The frozen contract every distribution target implements, plus the v1 stub. Independently reviewable — later slices depend on this interface.

**Files:**
- Create: `apps/control-panel/lib/relay/connector.ts`
- Test: `apps/control-panel/lib/relay/connector.test.ts`

**Interfaces:**
- Consumes: `Target` (type) from `./decide`.
- Produces (later tasks rely on these exact names):
  - `type PublishResult = { ok: true; externalRef?: string } | { ok: false; error: string }`
  - `interface ReleaseRow { id: string; masterAssetId: string; projectId: string | null; platform: string }`
  - `interface Connector { readonly target: Target; publish(release: ReleaseRow): Promise<PublishResult> }`
  - `function stubConnector(target: Target): Connector`
  - `const STUB_CONNECTORS: Record<Target, Connector>`

- [ ] **Step 1: Write the failing test**

Create `apps/control-panel/lib/relay/connector.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { stubConnector, STUB_CONNECTORS } from "./connector";

describe("stubConnector", () => {
  it("carries its target and succeeds without I/O", async () => {
    const c = stubConnector("discord");
    expect(c.target).toBe("discord");
    const r = await c.publish({ id: "r1", masterAssetId: "a1", projectId: "p1", platform: "discord" });
    expect(r).toEqual({ ok: true });
  });

  it("STUB_CONNECTORS has exactly one connector per target", () => {
    expect(Object.keys(STUB_CONNECTORS).sort()).toEqual(["discord", "public_web", "republic_archive"]);
    expect(STUB_CONNECTORS.public_web.target).toBe("public_web");
    expect(STUB_CONNECTORS.republic_archive.target).toBe("republic_archive");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `unset DATABASE_URL NODE_ENV && npx vitest run lib/relay/connector.test.ts`
Expected: FAIL — cannot resolve `./connector` (module not found).

- [ ] **Step 3: Write minimal implementation**

Create `apps/control-panel/lib/relay/connector.ts`:

```ts
import type { Target } from "./decide";

/** What a target's publisher returns. */
export type PublishResult = { ok: true; externalRef?: string } | { ok: false; error: string };

/** The minimal persisted-release shape a connector receives. */
export interface ReleaseRow {
  id: string;
  masterAssetId: string;
  projectId: string | null;
  platform: string;
}

/** How a single distribution target receives content. Real connectors implement this in a later slice. */
export interface Connector {
  readonly target: Target;
  publish(release: ReleaseRow): Promise<PublishResult>;
}

/** v1 stub: logs intent, performs no I/O, always succeeds. */
export function stubConnector(target: Target): Connector {
  return {
    target,
    async publish(release: ReleaseRow): Promise<PublishResult> {
      console.log(`[relay/distribute] would publish asset ${release.masterAssetId} -> ${release.platform}`);
      return { ok: true };
    },
  };
}

/** v1 registry: every target maps to the stub. */
export const STUB_CONNECTORS: Record<Target, Connector> = {
  public_web: stubConnector("public_web"),
  discord: stubConnector("discord"),
  republic_archive: stubConnector("republic_archive"),
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `unset DATABASE_URL NODE_ENV && npx vitest run lib/relay/connector.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/control-panel/lib/relay/connector.ts apps/control-panel/lib/relay/connector.test.ts
git commit -m "feat(relay): Connector boundary + v1 stub connector"
```

---

### Task 2: `distribute()` orchestration (`distribute.ts`)

The spine: load+gate → decide → per-target idempotent persist → dispatch → drive status.

**Files:**
- Create: `apps/control-panel/lib/relay/distribute.ts`
- Test: `apps/control-panel/lib/relay/distribute.test.ts`

**Interfaces:**
- Consumes: `decide`, `Policy`, `Target`, `Tier` from `./decide`; `RELAY_POLICY_V1` from `./policy`; `deriveBlockers` from `../release-gate`; `Connector`, `ReleaseRow`, `STUB_CONNECTORS` from `./connector`.
- Produces:
  - `interface DistributeDb` — the minimal Prisma surface (`asset.findUnique`, `release.findFirst/create/update`).
  - `interface DistributeDeps { db: DistributeDb; policy: Policy; connectors: Record<Target, Connector>; now: () => Date }`
  - `type TargetResult` / `type DistributeResult`
  - `async function distribute(assetId: string, deps: DistributeDeps): Promise<DistributeResult>`

- [ ] **Step 1: Write the failing test**

Create `apps/control-panel/lib/relay/distribute.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { distribute, type DistributeDb } from "./distribute";
import { RELAY_POLICY_V1 } from "./policy";
import { STUB_CONNECTORS } from "./connector";
import type { Connector } from "./connector";

const NOW = new Date("2026-06-22T00:00:00Z");
const now = () => NOW;

// In-memory fake of the minimal Prisma surface distribute() uses.
function fakeDb(asset: any): { db: DistributeDb; rows: any[] } {
  const rows: any[] = [];
  let seq = 0;
  const db: DistributeDb = {
    asset: { findUnique: async () => asset },
    release: {
      findFirst: async ({ where }) =>
        rows.find((r) => r.masterAssetId === where.masterAssetId && r.platform === where.platform) ?? null,
      create: async ({ data }) => {
        const row = { id: `rel-${++seq}`, ...data };
        rows.push(row);
        return row;
      },
      update: async ({ where, data }) => {
        const row = rows.find((r) => r.id === where.id);
        Object.assign(row, data);
        return row;
      },
    },
  };
  return { db, rows };
}

const approvedRights = [{ approvedForRelease: true, riskLevel: "low", releaseRequired: false }];
const assetOf = (rating: string) => ({ id: "asset-1", projectId: "proj-1", rating, rightsRecords: approvedRights });

describe("distribute()", () => {
  it("clean -> all 3 targets, published, tier public", async () => {
    const { db, rows } = fakeDb(assetOf("clean"));
    const res = await distribute("asset-1", { db, policy: RELAY_POLICY_V1, connectors: STUB_CONNECTORS, now });
    if (!res.distributed) throw new Error("expected distributed");
    expect(res.tier).toBe("public");
    expect(res.policyVersion).toBe("relay-policy-v1");
    expect(res.results.map((r) => r.platform).sort()).toEqual(["discord", "public_web", "republic_archive"]);
    expect(res.results.every((r) => r.status === "published" && r.action === "created")).toBe(true);
    expect(rows.length).toBe(3);
    expect(rows.every((r) => r.status === "published" && r.publishedAt === NOW)).toBe(true);
  });

  it("mature -> 2 targets gated; uncensored -> 1 target gated", async () => {
    const mature = fakeDb(assetOf("mature"));
    const rm = await distribute("asset-1", { db: mature.db, policy: RELAY_POLICY_V1, connectors: STUB_CONNECTORS, now });
    if (!rm.distributed) throw new Error("distributed");
    expect(rm.tier).toBe("gated");
    expect(rm.results.map((r) => r.platform).sort()).toEqual(["discord", "republic_archive"]);

    const unc = fakeDb(assetOf("uncensored"));
    const ru = await distribute("asset-1", { db: unc.db, policy: RELAY_POLICY_V1, connectors: STUB_CONNECTORS, now });
    if (!ru.distributed) throw new Error("distributed");
    expect(ru.results.map((r) => r.platform)).toEqual(["republic_archive"]);
  });

  it("not allowed -> blocked, no rows written, decide not reached", async () => {
    const blockedAsset = { id: "asset-1", projectId: "proj-1", rating: "clean", rightsRecords: [{ approvedForRelease: false }] };
    const { db, rows } = fakeDb(blockedAsset);
    const res = await distribute("asset-1", { db, policy: RELAY_POLICY_V1, connectors: STUB_CONNECTORS, now });
    expect(res.distributed).toBe(false);
    if (res.distributed) throw new Error("expected blocked");
    expect(res.blockers).toContain("Not approved for release.");
    expect(rows.length).toBe(0);
  });

  it("is idempotent by (asset, platform) — second run writes 0 rows", async () => {
    const { db, rows } = fakeDb(assetOf("clean"));
    const deps = { db, policy: RELAY_POLICY_V1, connectors: STUB_CONNECTORS, now };
    await distribute("asset-1", deps);
    const res2 = await distribute("asset-1", deps);
    if (!res2.distributed) throw new Error("distributed");
    expect(res2.results.every((r) => r.action === "skipped")).toBe(true);
    expect(rows.length).toBe(3); // still 3, no duplicates
  });

  it("a failed target does not block the others and does not throw", async () => {
    const failingDiscord: Connector = {
      target: "discord",
      publish: async () => ({ ok: false, error: "boom" }),
    };
    const { db, rows } = fakeDb(assetOf("clean"));
    const connectors = { ...STUB_CONNECTORS, discord: failingDiscord };
    const res = await distribute("asset-1", { db, policy: RELAY_POLICY_V1, connectors, now });
    if (!res.distributed) throw new Error("distributed");
    const discord = res.results.find((r) => r.platform === "discord")!;
    expect(discord.status).toBe("failed");
    expect(discord.error).toBe("boom");
    expect(res.results.filter((r) => r.status === "published").length).toBe(2);
    const failedRow = rows.find((r) => r.platform === "discord");
    expect(failedRow.status).toBe("failed");
    expect(failedRow.publishedAt).toBeUndefined();
  });

  it("re-run after a failed target still writes 0 new rows (failed not retried in v1)", async () => {
    const failingDiscord: Connector = { target: "discord", publish: async () => ({ ok: false, error: "boom" }) };
    const { db, rows } = fakeDb(assetOf("clean"));
    const deps = { db, policy: RELAY_POLICY_V1, connectors: { ...STUB_CONNECTORS, discord: failingDiscord }, now };
    await distribute("asset-1", deps);
    const res2 = await distribute("asset-1", deps);
    if (!res2.distributed) throw new Error("distributed");
    expect(res2.results.every((r) => r.action === "skipped")).toBe(true);
    expect(rows.length).toBe(3);
  });

  it("unrecognized rating fail-closes to 0 targets, 0 rows", async () => {
    const { db, rows } = fakeDb(assetOf("weird"));
    const res = await distribute("asset-1", { db, policy: RELAY_POLICY_V1, connectors: STUB_CONNECTORS, now });
    if (!res.distributed) throw new Error("distributed");
    expect(res.results.length).toBe(0);
    expect(rows.length).toBe(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `unset DATABASE_URL NODE_ENV && npx vitest run lib/relay/distribute.test.ts`
Expected: FAIL — cannot resolve `./distribute` (module not found).

- [ ] **Step 3: Write minimal implementation**

Create `apps/control-panel/lib/relay/distribute.ts`:

```ts
import { decide, type Policy, type Rating, type Target, type Tier } from "./decide";
import { deriveBlockers } from "../release-gate";
import type { Connector, ReleaseRow } from "./connector";

// rightsOf is inlined (not imported from lib/studio-writes) so this module never pulls in
// lib/studio-db's Prisma singleton — keeps distribute() and its unit tests DB-free.

/** The minimal Prisma surface distribute() needs (injected for testability). */
export interface DistributeDb {
  asset: {
    findUnique(args: { where: { id: string }; include: { rightsRecords: true } }): Promise<any>;
  };
  release: {
    findFirst(args: {
      where: { masterAssetId: string; platform: string };
    }): Promise<{ id: string; status: string } | null>;
    create(args: {
      data: { masterAssetId: string; projectId: string | null; platform: string; status: string };
    }): Promise<{ id: string }>;
    update(args: { where: { id: string }; data: { status: string; publishedAt?: Date } }): Promise<unknown>;
  };
}

export interface DistributeDeps {
  db: DistributeDb;
  policy: Policy;
  connectors: Record<Target, Connector>;
  now: () => Date;
}

export type TargetResult = {
  target: Target;
  platform: string;
  status: "published" | "failed" | "scheduled";
  action: "created" | "skipped";
  externalRef?: string;
  error?: string;
};

export type DistributeResult =
  | { distributed: false; allowed: false; blockers: string[] }
  | { distributed: true; allowed: true; tier: Tier; policyVersion: string; results: TargetResult[] };

export async function distribute(assetId: string, deps: DistributeDeps): Promise<DistributeResult> {
  const { db, policy, connectors, now } = deps;

  // 1. Load the release-candidate master + its rights. 2. Gate (fail-closed).
  const asset = await db.asset.findUnique({ where: { id: assetId }, include: { rightsRecords: true } });
  const rights = asset?.rightsRecords?.[0] ?? null;
  const blockers = deriveBlockers(rights);
  if (blockers.length > 0) {
    return { distributed: false, allowed: false, blockers };
  }

  // 3. Decide (allowed === true is guaranteed here, so decide() never throws).
  const decision = decide({ assetId, rating: asset.rating as Rating, allowed: true }, policy);

  // 4. Per target: idempotency -> persist scheduled -> dispatch -> drive status.
  const results: TargetResult[] = [];
  for (const target of decision.targets) {
    const platform = target; // verbatim
    const existing = await db.release.findFirst({ where: { masterAssetId: assetId, platform } });
    if (existing) {
      results.push({ target, platform, status: existing.status as TargetResult["status"], action: "skipped" });
      continue;
    }
    const row = await db.release.create({
      data: { masterAssetId: assetId, projectId: asset.projectId ?? null, platform, status: "scheduled" },
    });
    const releaseRow: ReleaseRow = {
      id: row.id,
      masterAssetId: assetId,
      projectId: asset.projectId ?? null,
      platform,
    };
    const result = await connectors[target].publish(releaseRow);
    if (result.ok) {
      await db.release.update({ where: { id: row.id }, data: { status: "published", publishedAt: now() } });
      results.push({ target, platform, status: "published", action: "created", externalRef: result.externalRef });
    } else {
      await db.release.update({ where: { id: row.id }, data: { status: "failed" } });
      results.push({ target, platform, status: "failed", action: "created", error: result.error });
    }
  }

  return { distributed: true, allowed: true, tier: decision.tier, policyVersion: decision.policyVersion, results };
}
```

- [ ] **Step 4: Run tests + full relay suite to verify pass and no regressions**

Run: `unset DATABASE_URL NODE_ENV && npx vitest run lib/relay/distribute.test.ts && npm test`
Expected: distribute suite PASS (7 tests); `npm test` PASS (full relay suite green — decide + connector + distribute, no regressions).

- [ ] **Step 5: Commit**

```bash
git add apps/control-panel/lib/relay/distribute.ts apps/control-panel/lib/relay/distribute.test.ts
git commit -m "feat(relay): distribute() governed spine — gate -> decide -> persist -> dispatch"
```

---

## Self-Review

**1. Spec coverage** (`DISTRIBUTION_DESIGN.md` → task):
- §1 Contract (`distribute`, `DistributeDeps`, `DistributeResult`, `TargetResult`) → Task 2.
- §2 Flow (load → gate → decide → per-target persist/dispatch/status) → Task 2 Step 3.
- §3 Persistence (one row per target, `platform`=target verbatim) → Task 2 (`platform = target`).
- §4 Connector boundary + stub → Task 1.
- §5 Idempotency (advisory, any existing row → skip; failed not retried) → Task 2 (idempotent + failed-rerun tests).
- §6 Library-only entry point → no route task. ✓
- §7 Error handling (not-allowed, per-target failure no-throw, unrecognized rating, DB errors propagate) → Task 2 tests.
- §8 Module layout → Tasks 1 & 2 files. ✓
- §9 Test matrix → Task 2 Step 1 (all 7 cases present incl. failed-rerun + publishedAt).
- Out-of-scope items (real connectors, worker, scheduling, retries, paywall, UNIQUE index) → not built. ✓

**2. Placeholder scan:** no TBD/TODO; every code/command step is concrete. ✓

**3. Type consistency:** `Target`/`Tier`/`Policy`/`Rating` sourced from `./decide`; `Connector`/`ReleaseRow`/`PublishResult`/`STUB_CONNECTORS`/`stubConnector` defined in Task 1 and consumed verbatim in Task 2; `DistributeDb`/`DistributeDeps`/`DistributeResult`/`TargetResult`/`distribute` consistent between the test (Task 2 Step 1) and impl (Step 3). `db.release.findFirst/create/update` and `db.asset.findUnique` signatures match between `DistributeDb` and `fakeDb`. ✓
