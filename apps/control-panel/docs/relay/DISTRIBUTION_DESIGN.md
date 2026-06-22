# Relay Distribution — Slice 2 v1 "governed spine" (design; APPROVED)

> **Status:** approved slice-2 v1 design (Brad, 2026-06-22). **Implementation is a
> separate step gated on this doc** — TDD, failing test first; no code before the
> tests. Builds on `DECIDE_DESIGN.md` (slice 1). Scope deliberately **excludes** real
> connectors, the Graphile Worker, scheduling, retries, and the paywall — those are
> later slices that *consume* this spine.

## Scope
v1 wires the **governed distribution spine**: for a release-approved asset, compose
release-gate → `decide()` → persist `releases` rows → dispatch through a `Connector`
boundary (a stub in v1) → drive the row status machine. **No external platform APIs,
no worker, no scheduling.**

Why this first: it settles the two previously-undecided pieces — the **target →
`releases` mapping** and the **connector contract** — turns the currently-orphaned
`decide()` into a wired path, and makes the `releases` table (today dead schema, never
read/written) live. Real delivery is a drop-in afterward.

## 1. Contract
```ts
distribute(assetId: string, deps: DistributeDeps): Promise<DistributeResult>

DistributeDeps = {
  db: StudioDb                          // Prisma client (lib/studio-db.ts)
  policy: Policy                        // RELAY_POLICY_V1 (lib/relay/policy.ts)
  connectors: Record<Target, Connector> // v1: stub for all three targets
  now: () => Date                       // injected → deterministic tests
}

DistributeResult =
  | { distributed: false; allowed: false; blockers: string[] }            // gate denied
  | { distributed: true;  allowed: true; tier: Tier; policyVersion: string;
      results: TargetResult[] }

TargetResult = {
  target: Target; platform: string;     // platform === target (verbatim)
  status: 'published' | 'failed' | 'scheduled';
  action: 'created' | 'skipped';        // skipped = idempotent no-op
  externalRef?: string; error?: string;
}
```

## 2. Flow (deterministic; routing table lives in `decide()`, not here)
1. **Load** the asset `assetId` (the release-candidate **master**) + its `rating` +
   first rights record (reuse `release-gate.ts` `rightsOf` / `deriveBlockers`; the
   asset's `project_id` is reused for the `releases` rows).
2. **Gate:** `allowed = deriveBlockers(rights).length === 0`. If not allowed → return
   `{ distributed:false, allowed:false, blockers }`. **`decide()` is NOT called** — it
   throws on `allowed !== true` by contract (`DECIDE_DESIGN` §1), so the spine guards it.
3. **Decide:** `decide({ assetId, rating, allowed:true }, policy) → { targets, tier, policyVersion }`.
4. **Per target** (in `decide()` order):
   - **Idempotency:** if **any** `releases` row already exists for
     `(master_asset_id, platform=target)` → `action:'skipped'`, leave it untouched (a
     non-`failed` row is already distributed; a `failed` row is **not retried in v1** —
     retry belongs to the worker slice).
   - else **persist** `{ masterAssetId, projectId, platform:target, status:'scheduled' }`,
     then **dispatch** `connectors[target].publish(row)`:
     - `ok` → update `status='published'`, `published_at=now()` → `action:'created'`.
     - `!ok` → update `status='failed'` → `action:'created', error`.
5. **Return** the summary. **Partial failure is a valid outcome** (per-target status),
   never a thrown error.

`decide()` and `RELAY_POLICY_V1` are reused **unchanged** — the mapping
(`clean`→3 targets/`public`, `mature`→2/`gated`, `uncensored`→1/`gated`, unrecognized→
`[]`/`gated`) stays there.

## 3. Persistence model (settled)
- **One `releases` row per target**, `platform` = the `Target` id **verbatim**
  (`public_web` / `discord` / `republic_archive`). The `platform` column is a free-form
  string (no enum/vocabulary), so storing the target id directly is the honest, YAGNI
  choice — **no translation layer**. Each target is independently schedulable/publishable
  (its own `published_at` / `status`).
- Columns written: `master_asset_id`, `project_id`, `platform`, `status`
  (`scheduled` → `published`/`failed`). `scheduled_at` / `hook_variant` /
  `version_variant` left null in v1 (future-dating is a later slice).

## 4. Connector boundary (the contract this slice freezes)
```ts
type PublishResult = { ok: true; externalRef?: string } | { ok: false; error: string };
interface Connector {
  readonly target: Target;
  publish(release: ReleaseRow): Promise<PublishResult>;
}
```
- v1 ships **one stub/log connector**, used for all three targets: logs
  `"would publish <assetId> → <platform>"`, returns `{ ok: true }`. No network.
- A real connector (web / discord / archive) drops into the `connectors` registry later
  with **zero changes to `distribute()`** — fixing this contract now is the point of the
  slice.

## 5. Idempotency (settled — advisory in v1)
- Re-running `distribute()` is safe: **any** existing row for
  `(master_asset_id, platform)` is **skipped** (no duplicate, no re-publish) — a
  non-`failed` row is already distributed, and a `failed` row is **not retried in v1**
  (retry belongs to the worker slice).
- **Known limitation:** the check-then-insert is **advisory** — two concurrent
  `distribute()` calls for the same `(asset, platform)` could double-insert.
- **Fast-follow (NOT v1):** add a `UNIQUE (master_asset_id, platform)` index to make
  idempotency atomic. v1 deliberately ships **no schema change**.

## 6. Entry point (settled)
- v1 delivers the **library function `distribute()` only** — it is the testable unit and
  the spine's logic. **No API route in v1.** Wiring `POST /api/studio/distribute`, or
  calling `distribute()` from the approve flow, is a later integration step.

## 7. Error handling
- Not-allowed → graceful blocked result (no `decide()` call).
- Per-target connector failure → that row `failed`; other targets unaffected;
  `distribute()` does **not** throw.
- Unrecognized rating → `decide()` fail-closes to `targets:[]` → zero rows.
- DB errors propagate to the caller (no swallowing).

## 8. Module layout (new files in `apps/control-panel/lib/relay/`)
- `connector.ts` — `Connector` interface + `stubConnector(target)` + the registry. One
  purpose: how a target receives content.
- `distribute.ts` — `distribute()` orchestration only; depends on `decide` (pure),
  `deriveBlockers` (gate), `db`, `connectors`. No I/O beyond `db` + connector.
- `distribute.test.ts` — the TDD matrix (§9).
- Reused **unchanged:** `decide.ts`, `policy.ts`, `release-gate.ts`, `studio-db.ts`.

## 9. Test matrix (TDD — write first; injected fake `db` + stub connectors + fixed `now`)
- `clean` → 3 rows (`public_web`, `discord`, `republic_archive`) all `published`,
  `tier:'public'`, all `action:'created'`.
- `mature` → 2 rows (`discord`, `republic_archive`), `tier:'gated'`.
  `uncensored` → 1 (`republic_archive`), `gated`.
- not-allowed (non-empty blockers) → `{ distributed:false }`, **0 rows**, `decide()` not called.
- **idempotent:** run twice → 2nd run writes 0 rows, all `action:'skipped'`.
- connector failure on one target → that row `status:'failed'`, others `published`, **no throw**.
- re-run after a `failed` target → still 0 new rows (the `failed` row is `skipped`, not retried in v1).
- unrecognized rating (forced invalid) → 0 rows (fail-closed).
- `published_at` set from the injected `now` on success; absent on `failed`.

## Out of scope (later slices that consume this spine)
Real connectors (web / discord / republic_archive); the **Graphile Worker** (direct,
non-pooler Neon host — see `NEON_TOPOLOGY.md`); future-dated scheduling (`scheduled_at`);
retries; the **paywall** (`tier → entitlement → Stripe`); the
`UNIQUE (master_asset_id, platform)` index; an API route / approve-flow integration.
