# RUNBOOK — Phase 1: `ilyrium` Schema Reconciliation (Direction 0-A) — EXECUTED

> Status: EXECUTED on branch `feat/relay-schema-reconcile` off `feat/creative-loop-v1`,
> against a fresh protected Neon branch of `studio-os/production` (DB `ilyrium`, endpoint
> `ep-morning-frost-apbgxh31`, direct host). Production `ilyrium` was NOT touched —
> promotion is a separate, explicit human gate. Spec: `DETERMINATION_path_forward.md`.

## Outcome
The Relay precondition is met: this repo's Prisma client now reads the REAL `ilyrium`
`public` tables, `assets.rating` exists, the `/api/studio/*` routes run against the real
risk-based governance model, and the dead Campaign track is retired. `next build` is green
and every previously-broken route was HTTP-verified.

## Ground-truth env traps (re-encountered)
- The shell carries a stale `DATABASE_URL` (PermitHub `ep-plain-haze/neondb`) from the
  active `.venv-feas`. Prisma's dotenv does NOT override an existing env var, so EVERY
  CLI/DB command was run with `unset DATABASE_URL` so `.env` wins. Verified target with
  `SELECT current_database()` = `ilyrium` + the 19-table list before any write.
- The shell also carries `NODE_ENV=development`. `next build` under a leaked
  `NODE_ENV=development` loads React's dev runtime in the prod prerender and crashes every
  page (incl. Next's built-in `/404`/`/500`) with `useContext` null. Fix: `unset NODE_ENV`
  before `next build`.
- `.env` is the DIRECT (non-pooler) host. Verified it works for BOTH the Prisma CLI native
  connector AND the runtime `@prisma/adapter-neon` + `ws` WebSocket driver, so one string
  serves both. `sslmode=require`, no `channel_binding`.

## Steps executed (with outcomes)
0. **Connection gate (re-verified).** `current_database()=ilyrium`, 19 snake_case tables.
1. **Baseline commit** (`0d59f70`). The untracked `apps/control-panel/` committed as the
   recoverable baseline; `.gitignore` excludes `.env` (secret stays out — triple-verified),
   `node_modules/`, `.next/`, `prisma/generated/`, `lib/generated/`.
2. **Preflight reads.** Live `asset_type` vocab = `reference/master/image` (all lowercase,
   all in the 8-value CHECK, no UPPERCASE stragglers, no `subtitle`); `vector` ext present
   (`text_embedding` → `Unsupported`); non-real tables (takes/provenance_records/
   archive_packages/...) all absent; zero pg enums; `_prisma_migrations` null.
3. **Campaign retired + idealized schema archived** (`dafcb52`). Deleted
   `app/api/campaigns`, `app/api/webhooks/video-render`, `lib/agents/{assembly,
   production-dispatcher,script-doctor}.ts`, `lib/db.ts` (campaign client),
   `prisma/schema.prisma`. Archived `studio.prisma` + the never-applied init migration →
   `docs/relay/reference/`.
4–6. **Prisma adoption + baseline + drift** (`8ca4fec`). Introspected the 19 tables into
   `prisma/ilyrium.prisma` (PascalCase models + camelCase fields via `@map`/`@@map`,
   `AgentRun`→`Run`, `text_embedding` kept `Unsupported("vector")`); repointed
   `prisma.config.ts`. Baseline-adopted: `migrate diff --from-empty --to-schema` → pure
   CREATE (19 tables / 31 indexes / 23 FKs, zero DROP/CHECK), `migrate resolve --applied
   0_init` (records baseline, never executes; `_prisma_migrations` = 1 row, data untouched).
   Drift check (`migrate diff --from-config-datasource --to-schema --exit-code`) = **empty**.
7. **`rating` migration** (`4879fb1`). Single additive
   `ALTER TABLE assets ADD COLUMN rating text NOT NULL DEFAULT 'clean'
   CHECK (rating IN ('clean','mature','uncensored'))` via `migrate deploy`. Verified:
   text/NOT NULL/default clean; CHECK rejects `'bogus'`, accepts the 3 valid values; 7
   existing rows backfilled to `'clean'`; drift still empty; client regenerated.
8. **App rewrite onto the real tables.**
   - `lib/studio-writes.ts` (new): asset_type 422 validation, project get-or-create/find by
     title (Fork A), paired asset+rights writer (Fork B, uri dedup), master finder, user-FK
     guard.
   - `lib/release-gate.ts` + `lib/risk.ts`: rewritten onto the real risk fields
     (approvedForRelease, releaseRequired/releaseStatus, `*_risk`, riskLevel,
     syntheticPerformerFlag/sagAftraNoticeFiledAt).
   - 10 routes: `asset` (uri dedup + 422), `release-gate`/`approve`/`qa` (risk-based onto
     `rights_records` + `gate_approvals`, 1:many-aware), `queue`/`run`/`sync` (real
     columns), `pipeline` (no-op — no DB column), `c2pa`/`archive` (→ 501, no backing table).
   - `lib/adapter-bus.ts`: the generate path wired onto the real asset graph (asset + rights
     + agent_runs trace); broken `./db`/`./storage` mocks removed.
   - Console (`page.tsx`/`Workspace.tsx`/`Pipeline.tsx`/`ConsolePanels.tsx`): full remap to
     the real shapes (assetType/uri/rating, risk-based rights, provenance/archive panels
     removed).
   - Python sync: `producer.py` ×3 + `graph_sync.py` default lowercased
     (`VIDEO`→`video`, `MASTER`→`master`); `studio_pipeline_service.py` `SUBTITLE` left
     deferred (not in the asset_type vocab; the route 422s it fail-closed).
9. **Verification.** Prisma client read 2 projects + 3 assets (assetType/rating via `@map`,
   1:many rights); write path proven CHECK-valid via a rolled-back paired insert (count
   7→7). `tsc --noEmit` clean; `next build` green (all routes dynamic, console + pages
   build). HTTP smoke: release-gate→200 (`allowed:false`, 2 blockers, real rights), asset
   bad-type→422, queue→200 (3 risk-scored masters), c2pa→501.

## Pre-existing build fixes (unrelated to the reconciliation; needed for the green build)
- `css.d.ts`: ambient `declare module "*.css"` (the `import "./globals.css"` side-effect
  import couldn't be type-resolved under `moduleResolution: "node"`).
- `tsconfig.json`: `"ignoreDeprecations": "6.0"` (silences the `node10` TS5107 that Next's
  type-check treated as fatal).
- Deleted `lib/agents/scene-breakdown.ts` (dead — no importers — and imported uninstalled
  `@anthropic-ai/sdk`/`zod`).
- Gitignored `tsconfig.tsbuildinfo` (tsc cache; was tracked from the baseline).

## Phase-1 limitations (for follow-up)
- `c2pa`/`archive` routes are 501 (no `provenance_records`/`archive_packages` tables).
- `pipeline` does not persist state (no projects column; JSON side-table is future work).
- Console: asset→scene highlighting and run→project attribution are inert (no scene_number
  on assets; `agent_runs` has no project FK); upstream-lineage pane dropped (no provenance).
- `subtitle` is not in the `asset_type` vocab (captions deferred out of `assets`).

## Promotion (NOT done — separate human gate)
Open a PR from `feat/relay-schema-reconcile`. Promoting the verified branch migrations
(`0_init` + `add_asset_rating`) to production `ilyrium` is a separate, explicit STOP.

---

# Phase 1 CLOSE — retroactive reconciliation + close-out

> Branch `feat/relay-schema-reconcile`, **merged via PR #2 → `feat/creative-loop-v1`**
> (merge `2780bc24`). All DB work on the Neon branch `studio_os_branch1`
> (`ep-morning-frost-apbgxh31`). Production `ilyrium` untouched. Step 9 deferred.

## Status: ✅ Phase 1 CLOSED at the branch
Steps 0–8 done, committed, and merged: `0d59f70` (baseline) · `dafcb52` (Campaign retire) ·
`8ca4fec` (schema adopt) · `4879fb1` (rating) · `24792f5` (route/console/adapter rewrite +
verify) → merge `2780bc24`. **Step 9 (production promotion) is a separate human gate**, not
done here.

## Premise reconciliation (account error in an interim brief, not an execution divergence)
An interim corrective brief stated Steps 5–8 were skipped and the two migrations applied
without being surfaced. The session record contradicts that and it was classified as a
history mis-statement (nothing was redone). Evidence:
- The `0_init` baseline (DROP-scan + empty drift) was surfaced before `migrate resolve`
  ("go run the baseline resolve"); the exact `rating` ALTER was surfaced before
  `migrate deploy` ("yes. go.").
- The Step-1 preflight reads were surfaced and the three forks decided (baseline-first;
  fail-closed defer subtitle; Brad pastes the prod string).
- Steps 5–8 (asset_type normalization, route/console rewrite, Campaign retire, verification)
  are committed at `24792f5`/`dafcb52` and merged at `2780bc24`; HTTP smoke passed
  (release-gate 200 / asset 422 / queue 200 / c2pa 501).

## Step A — applied migrations re-verified (read-only)
- `0_init`: pure adopt baseline — **0** DROP/TRUNCATE/ALTER..DROP/DELETE; **0** CHECK clauses
  (live CHECKs stay in the DB); 19 CREATE / 31 INDEX / 23 FK; `prompts.text_embedding`
  emitted as raw `vector` (a baseline marker, never executed).
- `add_asset_rating`: exactly `ALTER TABLE assets ADD COLUMN rating text NOT NULL DEFAULT
  'clean' CHECK (rating IN ('clean','mature','uncensored'))` and nothing else.
- `migrate status`: both applied on the branch, no drift.

## Step B — preflight reads (read-only, branch)
- **asset_type vocab:** `reference`(3), `master`(3), `image`(1) — all lowercase, no UPPERCASE
  rows, no `subtitle` in real data (no normalization UPDATE needed).
- **20 domain CHECKs** surfaced, incl. `assets_asset_type_check` =
  `image|video|voice|music|still|master|reference|board` (no `subtitle`) and
  `assets_rating_check` = `clean|mature|uncensored`. The route rewrites validate against
  these exact sets.
- **pgvector:** `vector` 0.8.0 installed.
- **non-real tables:** `takes`/`provenance_records`/`archive_packages`/`sequences`/
  `audio_elements`/`cuts` all absent — confirming Take/ProvenanceRecord/ArchivePackage are
  rewrites, not `@map`s.

## Decisions recorded
- **subtitle → DEFER (Option 1).** Do NOT widen the `asset_type` CHECK; no `DROP CONSTRAINT
  assets_asset_type_check`; no DDL beyond the applied `rating` column. The asset route's 422
  on `subtitle` stands; the Python `SUBTITLE` line stays deferred (not normalized).
  Rationale: no product reason to admit `subtitle` has surfaced; widening is a
  destructive-shaped (DROP + re-add) second schema change on a production-bound migration;
  fail-closed is reversible later on its own merits, admitting bad data now is not.
  Reaffirms "add only what Relay needs."
- **pgvector extension declaration → DEFERRED.** The canonical schema does not declare
  `extensions = [vector]`; drift is empty only because Prisma does not track extensions
  without the `postgresqlExtensions` preview. Do NOT enable extension tracking now (it would
  change future diffs and could complicate the Phase 2 `relay.prisma` migrations). Decide on
  its own merits later.

## Credential hygiene
`apps/control-panel/.env` confirmed **never committed** across all history
(`git log --all --full-history -- apps/control-panel/.env` empty; `*.env` sweep empty). The
branch credential (`ep-morning-frost-apbgxh31` role) is not exposed in git.

## Phase 2 precondition (satisfied — Phase 2 is a separate session, not started here)
Prisma reads the real `ilyrium`; `assets.rating` present; `/api/studio/*` governance on the
real risk-based tables (`rights_records` + `gate_approvals` + `releases`); Campaign retired.
Open gates handed to Brad: (1) Step-9 production promotion (credential path TBD — prefer a
one-time Vercel MCP pull); (2) start of Phase 2.

---

# Endpoint record correction + Step-9 promotion plan (2026-06-20)

## Endpoint record CORRECTION
The earlier "never-connect endpoint" blocklist was STALE. Root cause: Neon **`ep-...`
compute ids drift** (a branch's primary compute can change id), while **`br-...` branch ids
are stable**. Safety must key on branch identity + console status, never on endpoint-id
strings — keying on `ep-...` is what produced the false "ep-young-voice is archived" alarm.

### Branch → endpoint → status map
| branch id | branch name | current primary compute | status | database | source |
|---|---|---|---|---|---|
| `br-spring-rain-ap81nd7m` | `production` (Default) | **`ep-young-voice-apndapaf`** | Idle/active (normal) | `ilyrium` | Brad's Neon console (Connect panel) |
| `studio_os_branch1` | `studio_os_branch1` | `ep-morning-frost-apbgxh31` | active | `ilyrium` | this session's `.env` |
| (memory branch) | — | `ep-purple-shape` | not re-verified | **`ilyrium_memory`** (pgvector) | prior determination evidence |

- `ep-young-voice-apndapaf` is **production's current primary compute** (Idle = normal, not
  archived). The read-only gate that connected to it woke production-idle normally (not an
  archival/billing event).
- `ep-purple-shape` = the **`ilyrium_memory`** pgvector DB's endpoint — a SEPARATE, unrelated
  database. Out of scope regardless of its status; do NOT touch (wrong database, not because
  archived). Its live status was NOT re-verified this pass (no Neon console/API access here,
  and connecting-to-identify is prohibited) — identify from the console if ever needed.

### Corrected gate logic (replaces the endpoint-id blocklist)
Before connecting to any Neon endpoint:
1. Resolve the intended **branch id** (`br-...`) and confirm it is the one you mean
   (production = `br-spring-rain-ap81nd7m`).
2. Confirm the console shows that branch **active/idle** (not archived). Never wake a
   **console-archived** branch (keyed on STATUS, not endpoint name).
3. Verify the live connection with `SELECT current_database()` = `ilyrium` (never `/neondb`,
   never `patient-resonance`). Endpoint-id strings are descriptive only, never the safety key.

## Vercel `DATABASE_URL` (advisory — Brad's dashboard action, not a CC write)
Vercel production `DATABASE_URL` was found **empty** (write-only/Sensitive or unset). For
serverless it should be the **POOLED** production string:
`postgresql://neondb_owner:<pw>@ep-young-voice-apndapaf-pooler.c-7.us-east-1.aws.neon.tech/ilyrium?sslmode=require`
— Branch `production`, DB `ilyrium`, **connection pooling ON** (the `-pooler` host),
`sslmode=require`, and **drop `channel_binding=require`**. (The screenshot showed pooling OFF
/ the direct host — wrong for Vercel; the direct host is for the Prisma CLI only.) Brad sets
this in the Vercel dashboard; the credential is never entered to Claude Code.

## Step-9 promotion plan (read-only preflight DONE; production write AWAITING Brad's explicit go)
Mechanism (additive, non-destructive) against production (`br-spring-rain` / `ilyrium`,
**direct** host `ep-young-voice` with `channel_binding` dropped):
1. `prisma migrate resolve --applied 0_init` — creates `_prisma_migrations` on production and
   marks `0_init` applied **without running it** (the 19 tables already exist; metadata only).
2. `prisma migrate deploy` — applies only `add_asset_rating`.

### Read-only preflight result (2026-06-20, against production)
- `current_database()` = `ilyrium`; host `ep-young-voice-apndapaf`; **`_prisma_migrations`
  NULL, `assets.rating` absent, 19 base tables** — the exact state `resolve --applied 0_init`
  expects. `assets=7`, `projects=2`.
- **Drift check** (`migrate diff --from-config-datasource --to-schema ilyrium.prisma`) =
  **exactly one change**: `ALTER TABLE "assets" ADD COLUMN "rating" TEXT NOT NULL DEFAULT
  'clean';` — no other drift, destructive scan clean. Production = canonical minus `rating`.

### Exact production deploy SQL (`add_asset_rating`)
```sql
ALTER TABLE "public"."assets" ADD COLUMN "rating" TEXT NOT NULL DEFAULT 'clean'
  CHECK ("rating" IN ('clean', 'mature', 'uncensored'));
```
Additive; safe on the populated table (7 rows backfill to `'clean'`). No `DROP`/data-loss.

### STATUS: ⛔ AWAITING Brad's explicit in-session approval before any production write.
On approval only: point `.env` at the production direct string, re-verify `current_database()`
= `ilyrium` + branch = production, run `resolve --applied 0_init` then `migrate deploy`, STOP
on anything beyond the metadata mark + the additive `rating` column, verify
(`_prisma_migrations` 2 rows, `rating` + CHECK present, row counts unchanged), then **repoint
`.env` off production** back to `studio_os_branch1`.
