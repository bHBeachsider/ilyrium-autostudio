# Relay Distribution — Slice 2 v1 "governed spine" (design; DESIGN ONLY)

> **Status:** v1 design — **DESIGN ONLY** (no code, no migration, no tests authored here).
> Implementation is a separate, approval-gated slice that builds from this doc (design →
> failing test → code). **This doc's approval is the gate to writing code.** Builds on
> `DECIDE_DESIGN.md` (slice 1, not re-opened).
>
> **Revision note (2026-06-22):** the `releases` column set below was reconciled against the
> **live `ilyrium` DB via `information_schema`** (dev branch), not assumed. This revision sets
> three decisions explicitly — **`scheduled` is v1-terminal** (no `scheduled→published`),
> **idempotency via `UNIQUE (master_asset_id, platform)` + upsert-or-skip** (the one v1
> migration, applied later), and **`tier` deferred / not stored** — superseding an earlier
> draft that had the stub connector drive rows to `published` and treated the UNIQUE as a
> post-v1 fast-follow.

## Scope (v1)
Wire the governed spine ONLY: `release-gate (allowed===true) → decide() → write `releases` rows
→ stub connector`. **No Graphile Worker, no external/platform APIs, no publishing.** v1 writes
governed *intent* (scheduled rows); it does not publish.

`decide()` is the upstream gate — pure, returns a `Decision` (eligible `targets[]` + `tier`), runs
only when release-gate returned `allowed===true`, already designed in `DECIDE_DESIGN.md`. Not
re-opened here.

## 1. The write contract (`decide()` → `releases`)
A design (not code) for the write function:
- **Input:** a release-approved asset (`id`) + the `Decision` returned by `decide()`.
- **Output:** N `releases` rows — one per `target` in `Decision.targets` — each with
  `platform = <target>` (verbatim), `status = "scheduled"`, and `master_asset_id` / `project_id`
  wired from the asset.
- **Return (in-memory):** a per-target summary (created vs. skipped). v1 returns governed *intent*,
  not a publish result.

## 2. Persistence model (settled) + verified column map
**One `releases` row per target; `platform = target` verbatim** — no translation layer (`platform`
is a free-text column with no vocabulary; storing the target id verbatim is the honest choice, and a
`target→platform` map is cheap to add later if values ever need to diverge). Each target is
independently schedulable (its own `published_at`/`status`) — for the deferred worker.

`public.releases` columns (live `information_schema`, `ilyrium`, 2026-06-22) and the v1 disposition
of each:

| column | type | nullable | v1 write |
|---|---|---|---|
| `id` | uuid | NO | DB default `gen_random_uuid()` |
| `project_id` | uuid | yes | **set** = `asset.project_id` |
| `master_asset_id` | uuid | yes | **set** = `asset.id` |
| `platform` | text | yes | **set** = `<target>` verbatim |
| `version_variant` | text | yes | null in v1 |
| `hook_variant` | text | yes | null in v1 |
| `scheduled_at` | timestamptz | yes | null in v1 (future-dating is the worker's slice) |
| `published_at` | timestamptz | yes | **null in v1** (the worker sets it on publish) |
| `status` | text | yes (default `'scheduled'`) | **set** = `"scheduled"` |
| `created_at` | timestamptz | NO | DB default `now()` |

Existing constraints (live): `PK(id)`, `FK project_id→projects`, `FK master_asset_id→assets`.
**No unique on `(master_asset_id, platform)`** — see §4.

## 3. `tier` — deferred, NOT stored in v1
`decide()` returns `tier` (`public`/`gated`), but **`releases` has no `tier` column** (confirmed via
`information_schema`) and `tier` governs the **paywall** — a later slice. v1 **does not persist
`tier`** and **adds no column for it** (no schema change for `tier`). The write function may surface
`tier` in its in-memory return for the caller; nothing is written. The paywall slice decides where
`tier` ultimately lives.

## 4. Idempotency — `UNIQUE (master_asset_id, platform)` + upsert-or-skip (the one v1 migration)
The write path WILL be re-invoked (retry / re-run). `releases` has no unique beyond `id`, so without
a guard a second run accumulates duplicate `discord` rows. **Rule:** "one release per asset per
platform" is a DB-level guarantee via **`UNIQUE (master_asset_id, platform)`**, and the write is
**upsert-or-skip** — on conflict, do nothing; the existing row stands (v1 neither re-publishes nor
mutates it).
- Column name confirmed **`master_asset_id`** (not `asset_id`) via `information_schema`.
- **`master_asset_id` is nullable, but the spine always writes a non-null `master_asset_id`** —
  `distribute()` runs only on a release-approved asset that has a real master (the `decide()`
  precondition), so every row it writes sets `master_asset_id`. A plain `UNIQUE (master_asset_id,
  platform)` would not constrain null rows (Postgres treats NULLs as distinct), so use a **partial**
  index `UNIQUE (master_asset_id, platform) WHERE master_asset_id IS NOT NULL`: it constrains exactly
  the rows the spine produces, and the nullable column is therefore **not a silent duplicate-row gap**.
- **This is the ONE schema change v1 implies.** It is **documented here and applied in the
  implementation slice** under the normal discipline (branch-first, paired down-migration,
  approval-gate). **NOT applied now.**

## 5. Connector boundary — defined seam, no publish in v1
v1 defines the `Connector` interface (the seam real connectors implement in a later slice) + a stub.
**The stub does not publish and does not transition status** — it exists to freeze the contract for
the deferred worker. The write path's structure includes the dispatch seam, but in v1 the observable
outcome is `scheduled` rows.

## 6. `scheduled` is v1-terminal (explicit boundary)
v1 writes `status="scheduled"` and **stops**. **Nothing transitions `scheduled → published`**, and
**`published_at` stays null.** That transition (and calling a real connector) is the deferred
**distribution-worker** slice. Naming this boundary keeps v1 honest: it writes governed *intent*, it
does not publish — a future reader must not read `scheduled` rows as "broken."

## 7. Entry point (settled)
**Library function only** in v1 — the testable unit and the spine's logic. No API route, no
approve-flow wiring (later integration steps).

## 8. Error handling (design-level)
- Not allowed (`deriveBlockers` non-empty) → return a blocked result; **`decide()` is not called**
  (it throws on `allowed!==true` by contract).
- Unrecognized `rating` → `decide()` fail-closes to `targets:[]` → zero rows.
- Idempotency conflict → on-conflict-do-nothing (skip) → never a duplicate, never a throw.
- DB errors propagate to the caller.

## 9. Test sketch (for the implementation slice — NOT authored here)
- `clean` / `mature` / `uncensored` → 3 / 2 / 1 `scheduled` rows; `platform` = the eligible targets;
  `published_at` null.
- not-allowed → 0 rows, blocked result.
- idempotent re-run → 0 new rows (on-conflict skip).
- unrecognized rating → 0 rows.

## Out of scope (deferred, each its own brainstorm-gated slice)
Graphile Worker (DIRECT non-pooled Neon host for LISTEN/NOTIFY); real platform/connector APIs; the
`scheduled → published` transition (and `published_at`); future-dated `scheduled_at`; the
paywall / entitlement / Stripe slice (where `tier` lands).
