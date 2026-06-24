# Relay Worker Drain — sub-slice design (scheduled → published mechanics; DESIGN ONLY)

> **Status:** approved (Brad, 2026-06-24). **DESIGN ONLY** — implementation is a separate slice
> (design → failing test → code). First sub-slice of the deferred "distribution worker." Builds on
> `DISTRIBUTION_DESIGN.md` (the spine writes `scheduled` rows and stops) and **reuses** the
> `Connector` seam (`lib/relay/connector.ts`). **No schema change** — `releases.status` is free-text
> (`scheduled`/`published`/`failed` are all valid); the `(master_asset_id, platform)` partial unique
> is already live.

## Scope
Build the **drain mechanics** that transition `releases` rows `scheduled → published`: a library
function `drainScheduled(deps)` that claims `scheduled` rows concurrency-safe, invokes the connector
seam, and on success marks `published` (+ `published_at`), on connector failure marks `failed`.
**Library-only** — *how* it is triggered (cron / worker / endpoint) and *where* it runs is a
SEPARATE later slice. v1 uses the **stub** connector (no real external publish).

## 1. Contract
```ts
drainScheduled(deps: DrainDeps): Promise<DrainResult>

DrainDeps = {
  db: DrainDb                            // Prisma client ($transaction + $queryRaw + release.update)
  connectors: Record<Target, Connector> // v1: STUB_CONNECTORS (lib/relay/connector.ts)
  now: () => Date
  batchSize?: number                     // default 100
}

DrainResult = {
  claimed: number
  published: number
  failed: number
  results: { id: string; platform: string; status: "published" | "failed" }[]
}
```

## 2. Flow (one transaction per batch)
1. **Claim** a batch, concurrency-safe:
   ```sql
   SELECT id, master_asset_id, project_id, platform
   FROM releases WHERE status = 'scheduled'
   ORDER BY created_at LIMIT :batchSize
   FOR UPDATE SKIP LOCKED
   ```
   `FOR UPDATE SKIP LOCKED` → a concurrent drain skips rows another drain has locked (no
   double-process). Run via `$queryRaw` inside `$transaction` (Prisma `findMany` cannot row-lock).
2. **Per claimed row:** `connector = connectors[row.platform]` (`platform` = target verbatim);
   `result = await connector.publish({ id, masterAssetId, projectId, platform })`.
   - `ok`  → `UPDATE releases SET status='published', published_at=:now WHERE id=:id`
   - `!ok` → `UPDATE releases SET status='failed' WHERE id=:id`
3. **COMMIT** (releases the locks). Return `{ claimed, published, failed, results }`.

## 3. Connector seam (reused; v1 = stub)
Reuses `lib/relay/connector.ts` (`Connector`, `STUB_CONNECTORS`). In v1 the drain **invokes** the
stub (the spine *defined* the seam but did not invoke it); the stub returns `{ ok: true }` → the row
goes `published`.

**Honest `published` semantics (v1):** the stub performs **no real external publish**, so a v1
`published` row means *"drained + stub acked,"* not *"live on a platform."* The mechanics are real;
real external publishing arrives when a real connector replaces the stub for that target. Documented
here so `published` is not misread.

## 4. Failure & idempotency
- Connector failure → `status='failed'`, **terminal in v1**: a re-drain claims **only**
  `status='scheduled'`, never `failed`. Retry/backoff is a later slice. (With the stub this never
  fires in production; it is defined + tested via an injected failing connector.)
- A row whose `platform` has **no registered connector** → `status='failed'` (the drain never
  crashes on a missing connector). In v1 this cannot happen — the spine only writes the three known
  targets, all present in `STUB_CONNECTORS` — but the drain handles it defensively.
- **Idempotent + concurrency-safe:** the drain only ever claims `scheduled`; `published`/`failed`
  rows are never re-touched; `SKIP LOCKED` prevents two concurrent drains double-processing. A crash
  mid-transaction rolls back → rows stay `scheduled`, re-claimed on the next run.

## 5. Concurrency model (v1 + the deferred refinement)
v1 holds the row lock **during** `publish()` (BEGIN → claim → publish → update → COMMIT) — clean for
the **instant stub**. For *slow real connectors* this would hold locks across a network call; the
refinement (deferred) is a **claim-marker**: `UPDATE releases SET status='publishing' WHERE id IN
(SELECT … FOR UPDATE SKIP LOCKED) RETURNING …`, then `publish()` *outside* the lock, then mark
`published`/`failed`. **Deferred to the real-connector slice** (YAGNI for the instant stub).

## 6. Components (new)
- `lib/relay/drain.ts` — `drainScheduled(deps)`. Depends on the Prisma client (via `deps.db`) + the
  connector registry. The claim is raw SQL (`$queryRaw`, `FOR UPDATE SKIP LOCKED`) inside one
  `$transaction` per batch.
- Reuses `lib/relay/connector.ts`. `lib/relay/drain.test.ts` — integration tests against a Neon dev
  branch (same harness as the spine's `distribute.test.ts`).

## 7. Test sketch (TDD — integration against a DB branch; NOT authored here)
- seed N `scheduled` rows → `drainScheduled` → all `published`, `published_at` set; no `scheduled` left.
- injected **failing** connector → those rows `failed`, `published_at` null.
- a second drain claims **only** `scheduled` (existing `published`/`failed` rows untouched).
- `batchSize` respected (seed > batch → only `batchSize` claimed per run).
- the claim SQL uses `FOR UPDATE SKIP LOCKED` (a row locked in one txn is not claimed by another).

## Out of scope (later slices, each its own brainstorm-gated cycle)
The trigger + host (Graphile Worker / Vercel Cron / endpoint; the deployment-host decision); real
connectors (`public_web` / `discord` / `republic_archive`); retry/backoff of `failed` rows; the
claim-marker refinement for slow connectors; the paywall (`tier`).
