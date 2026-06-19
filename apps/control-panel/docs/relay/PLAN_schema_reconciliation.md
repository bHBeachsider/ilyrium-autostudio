# PLAN: Control-Panel <-> ilyrium DB Schema Reconciliation + Asset `rating`

> Status: PLAN ONLY. This document was produced by a read-only investigation
> session. Nothing in it has been executed: no `db pull`, no migrations, no
> `ALTER`, no Neon branch, no client regeneration. The reconciliation is for a
> FUTURE session and is laid out in ordered, reversible steps (Section 9).

---

## 1. Context (why this change)

The control-panel Next.js app's Prisma layer and the live `ilyrium` Postgres
database were built independently and have never been connected. Two parallel
tracks exist:

- **The data (real, authoritative).** Neon project `studio-os`, endpoint
  `ep-gentle-fire`, database `ilyrium`, schema `public`: 19 snake_case tables
  populated by the Python auto-studio pipeline. `public._prisma_migrations` is
  null -> Prisma has never owned `public`. The real `assets` table is lean:
  `id uuid, project_id uuid, shot_id uuid, asset_type text, model_id text,
  prompt_id uuid, uri text, version int, created_at timestamptz`. There is NO
  `rating`, and NO `checksum / storage_provider / size_bytes / mime_type`.

- **The code (broken against the real DB).** The app ships an idealized studio
  asset graph in `prisma/studio.prisma` that was NEVER deployed to any database
  (every model carries `@@schema("studio")` and there are zero `@@map`
  directives, so it expects a `studio` Postgres schema with PascalCase tables
  that does not exist). Ten `/api/studio/*` routes + the studio console call this
  client's MODELS and throw at runtime against `ilyrium`. A second, separate
  Campaign/Scene track (`prisma/schema.prisma`) is likewise broken (its init
  migration was never applied).

The goal: make the app's typed Prisma client read the REAL `public` tables, add a
content `rating` to `assets`, and thereby unblock Ilyrium Relay (which routes
distribution and gates the paywall on `rating` via a single `decide()` gate).
Building Relay is OUT OF SCOPE; only its precondition (correct client over real
data + `rating` column) is in scope.

This is a RECONCILIATION, not a rename. The routes assume a data model materially
richer than reality (extra columns, a `provenance` relation, an `archivePackage`
table) that do not exist. Direction decided with Brad: the real DB wins; routes
are rewritten down to the lean real model.

---

## 2. Recon findings

### 2a. Live `public` column map (recon 0a) -- NOT YET CAPTURED; required
A direct read-only `psql` attempt against `ep-gentle-fire/ilyrium` FAILED with
`password authentication failed for user 'neondb_owner'` -- the `.env` credential
is STALE, and `.env` `DATABASE_URL` points at `/neondb` (the empty default), not
`/ilyrium`. The real `public` schema has NO source-of-truth in the repo (grep
found no `CREATE TABLE` DDL for these tables; it exists only in the live DB).
Therefore the authoritative column map MUST be pulled live -- either by Brad in
the Neon SQL editor or by `prisma db pull` once a fresh `ilyrium` connection
string is in hand. The exact `SELECT` queries are in Appendix A. Until 0a is run,
all per-column resolutions for non-`assets` tables below are marked `[confirm 0a]`.

### 2b. Prisma model-call surface (recon 0b) -- COMPLETE
17 files call Prisma models. Consumers: 10 studio routes
(`pipeline, archive, run, queue, c2pa, qa, approve, release-gate, asset, sync`),
`app/studio/console/page.tsx` (studio client); `app/api/campaigns/route.ts`,
`app/api/webhooks/video-render/route.ts`, `lib/agents/assembly.ts`,
`lib/agents/production-dispatcher.ts` (campaign client). No raw SQL anywhere.
Extra broken consumer found: `lib/agents/script-doctor.ts` imports
`getConcept / updateConceptTreatment / createGateApproval / logAgentRun` from
`../db` -- none are defined (stub imports).

### 2c. Live enum check (recon 0c) -- expected NONE; confirm live
Real type fields are plain `text` (e.g. `assets.asset_type`). The idealized
schema uses 7 pg enums but those live only in `studio.prisma`. Confirm zero
enums in `public` via the Appendix A query. Locked: keep `rating` as `text`,
not a pg enum.

### 2d. Per-entity field-access inventory (recon 0d) -- COMPLETE
Union of fields the code touches per entity (studio client unless noted):
- **Project**: externalId(unique), title, type, status, pipelineStage,
  pipelineState, autonomyMode, styleKernel, scaffoldPath, rightsStatus, approval,
  updatedAt, id; relations assets/scenes/shots/_count.
- **Asset**: id, projectId, type, uri, checksum, storageProvider, sizeBytes,
  mimeType, createdAt; relations provenance, rightsRecord, project.
- **Scene**: projectId, title, synopsis, orderIndex; nested shots; relation project.
- **Shot**: projectId, shotNumber, prompt.
- **RightsRecord**: assetId(unique), qaPassed, qaReport, noLikenessConfirmed,
  sourceMaterialState, likenessState, voiceState, musicLicenseState,
  vendorTermsState, consentDocumentUri, overrideReason, gateEvaluatedAt,
  approvedForRelease, reviewerId, reviewedAt, notes; relation asset.
- **Run**: projectId, entityType, entityId, agentName, status, costCents,
  latencyMs, inputs, outputs, approvalRequired, approvedBy, createdAt.
- **ProvenanceRecord**: assetId(unique), modelProvider, modelName, seed,
  generationParams, c2paManifestUri.  (NO real table.)
- **ArchivePackage**: projectId, masterAssetId, includedAssetIds, snapshots,
  c2paManifestUri, retentionPolicy, completenessScore, status, approval.
  (NO real table.)
- **Campaign / Scene (campaign client)**: campaign create + scene render-status
  updates. (NO real tables -- deferred track.)

### 2e. Critical state findings
1. `.env` DATABASE_URL -> `/neondb` (empty) and the password is stale. Execution
   step 0 MUST refresh the `ilyrium` connection string from the Neon console.
2. `studio.prisma` is a never-deployed greenfield design (no `studio` schema
   exists in the DB; no `@@map`).
3. Idealized models with NO real backing table: `Sequence, Take, AudioElement,
   Cut, ProvenanceRecord, ArchivePackage` (none appear in the 19-table list).
4. Real governance tables the routes IGNORE but should use:
   `rights_records, gate_approvals, greenlight_scores, releases`.
5. Orphan client `lib/generated/prisma/` is imported by nobody.
6. Prisma 7.8.0 with `@prisma/adapter-neon`; both clients use
   `new PrismaNeon({ connectionString: process.env.DATABASE_URL })`.

---

## 3. Decisions

| # | Decision | Resolution |
|---|----------|------------|
| 1 | Schema topology | SINGLE canonical client introspected from real `public` for the studio/asset graph (recommended/accepted). Campaign client kept as a separate, deferred generated client. |
| 2 | Missing columns/relations | REAL DB WINS. Rewrite routes to the lean real tables; map rights/QA/approve onto the real governance tables; ADD only `rating` to `assets`; DEFER provenance + archive routes. (Chosen by Brad.) |
| 3 | Campaign/video track | DEFER -- leave Campaign client + routes + its init migration untouched and out of scope. (Chosen by Brad.) Non-destructive. |
| 4 | `rating` type | `text NOT NULL DEFAULT 'clean' CHECK (rating IN ('clean','mature','uncensored'))`. Domain enforced primarily in the TS `decide()` layer; CHECK is belt-and-suspenders. NOT a pg enum. (Locked.) |

---

## 4. Entity reconciliation diff (centerpiece)

`type-as-enum -> asset_type-as-text` and `studio schema -> public schema` apply
to every studio entity. Real columns for non-`assets` tables are `[confirm 0a]`.

### Asset  (real `public.assets` is GROUND TRUTH)
| Code assumes | Real column | Resolution |
|---|---|---|
| id | id (uuid) | as-is |
| projectId | project_id | `@map("project_id")` |
| type (AssetType enum) | asset_type (text) | rename to assetType `@map`; route logic must use real text values (see gap below) |
| uri | uri | as-is |
| checksum | (none) | REMOVE from routes; replace dedup/addressing key (see gap) |
| storageProvider | (none) | REMOVE from routes |
| sizeBytes | (none) | REMOVE from routes |
| mimeType | (none) | REMOVE from routes |
| createdAt | created_at | `@map("created_at")` |
| (none) | shot_id, model_id, prompt_id, version | EXPOSE in canonical model (new, useful) |
| (none) | **rating** | ADD COLUMN (this plan) |
| relation provenance -> ProvenanceRecord | NO TABLE | DROP relation; defer c2pa/provenance routes |
| relation rightsRecord -> RightsRecord | rights_records (real) | KEEP relation; verify FK + columns `[confirm 0a]` |

**Semantic gaps (not mechanical):**
- `checksum` is used to dedup assets and to address a specific MASTER. Real
  `assets` has no checksum. New identity/dedup key must be chosen from real
  columns (candidates: `uri`, or `model_id + prompt_id + version`). `[decide + 0a]`
- Routes filter `asset_type = "MASTER" | "VIDEO" | "IMAGE"`. Real `asset_type` is
  free text with an unknown vocabulary; the "MASTER" release-candidate concept may
  not exist in real data. Run `SELECT DISTINCT asset_type` (Appendix A) and map
  the release-candidate concept to whatever the pipeline actually writes. `[0a]`

### Project -> projects (real)
externalId is the idempotency key for EVERY studio route's `upsert`. Whether real
`projects` has a unique `external_id` (or `campaign_id` / slug) is the single
highest-risk unknown. `[confirm 0a]` If absent, the upsert-by-externalId strategy
must change (e.g. upsert on a different unique key, or add an `external_id`
column). `pipelineState/pipelineStage/autonomyMode/styleKernel/scaffoldPath/
approval/rightsStatus` likewise `[confirm 0a]`; any not present are dropped from
routes or added as columns -- decide per column after 0a.

### Scene -> scenes (real), Shot -> shots (real)
`sync` route does `deleteMany` + nested `create` of scenes/shots using
projectId/title/synopsis/orderIndex and shotNumber/prompt. Real column names and
the scenes<->shots FK shape `[confirm 0a]`. Remap field names; adjust if real
columns differ.

### RightsRecord -> rights_records (real)
Heavily used by qa/approve/release-gate and `deriveBlockers` (lib/release-gate.ts
reads camelCase qaPassed/noLikenessConfirmed/approvedForRelease/<state> fields).
If real `rights_records` exposes equivalent columns -> `@map` them and keep the
gate logic. If the real shape differs (likely simpler) -> adapt `deriveBlockers`
field reads and the upsert payloads to real columns. `[confirm 0a -- decisive for
qa/approve/release-gate rewrite size]`

### Run -> agent_runs (real)
`run`/`approve` routes create run records. Map model `Run @@map("agent_runs")`;
field set `[confirm 0a]`.

### ProvenanceRecord, ArchivePackage -- NO REAL TABLE
Drop from the canonical client. The routes that depend on them (`c2pa`,
`archive`, the provenance nested-create in `asset`, console provenance/archive
panels) are DEFERRED (Decision 2). Not on the Relay critical path.

### Campaign / Scene (campaign client) -- DEFERRED
No real tables; untouched this effort (Decision 3).

---

## 5. Adopt-existing-DB procedure (Option B)

All Prisma commands run with `DATABASE_URL` = the fresh `ilyrium` BRANCH string.
Before any Prisma command: ensure the Python venv is deactivated and
`echo $env:DATABASE_URL` shows ONLY the `ilyrium` branch string (the venv injects
a stale PermitHub `ep-plain-haze` var that shadows `.env`).

1. **Introspect** the real `public` into a NEW canonical schema file
   `prisma/ilyrium.prisma` (do NOT overwrite the Campaign `schema.prisma`). Add a
   generator block (`output = "./generated/studio-client"` to keep
   `lib/studio-db.ts`'s import path stable). Point `prisma.config.ts` `schema` at
   `prisma/ilyrium.prisma`. Run `prisma db pull`.
2. **Review** introspected models: rename Prisma's auto names to match route usage
   where cheap (e.g. `AgentRun` -> `Run @@map("agent_runs")`); confirm `@map`
   keeps snake_case in the DB while exposing chosen TS names; add `rating String
   @default("clean")` to `Asset` only in the rating step (5), not here.
3. **Baseline (adopt)** -- this marks the schema applied WITHOUT recreating the
   existing tables:
   - `mkdir prisma/migrations/0_init`
   - generate the baseline SQL from empty -> canonical schema:
     `prisma migrate diff --from-empty --to-schema-datamodel prisma/ilyrium.prisma
     --script > prisma/migrations/0_init/migration.sql`
   - `prisma migrate resolve --applied 0_init`  (records it as applied; never runs it)
   - CONFIRM exact flag names first with `prisma migrate diff --help` and
     `prisma migrate resolve --help` (CLI 7.x differs from older runbooks; the
     drift-check in step 6 uses `--from-config-datasource` + `--to-schema`).
   This avoids "table already exists" because the create-SQL is recorded as
   already-applied, never executed against the populated DB.
4. **Verify no drift**: `prisma migrate diff --from-config-datasource
   prisma.config.ts --to-schema prisma/ilyrium.prisma --script` MUST print an
   empty migration. If it emits any `CREATE/ALTER`, STOP -- the introspection and
   DB disagree; reconcile before proceeding.
5. **`rating` as a SEPARATE migration AFTER the baseline** (keeps the baseline a
   faithful snapshot):
   - add `rating String @default("clean")` to the canonical `Asset` model;
   - hand-author `prisma/migrations/<ts>_add_asset_rating/migration.sql`:
     `ALTER TABLE public.assets ADD COLUMN rating text NOT NULL DEFAULT 'clean'
      CHECK (rating IN ('clean','mature','uncensored'));`
     (Prisma does not model CHECK constraints; the CHECK lives in raw SQL and the
     domain is enforced in `decide()` per Decision 4. Adding NOT NULL with a
     DEFAULT is safe on the populated table -- existing rows get `'clean'`.)
   - apply forward-only with `prisma migrate deploy` (NEVER `migrate dev`).
6. **Regenerate + repoint**: `prisma generate --schema prisma/ilyrium.prisma`.
   `lib/studio-db.ts` import path is unchanged (same output dir). Rewrite the
   studio routes/console to the canonical model + field names (Section 6).

---

## 6. Route reconciliation plan

| Route / file | Action | Notes |
|---|---|---|
| `api/studio/asset` | REWRITE | drop checksum/storageProvider/sizeBytes/mimeType + provenance nested-create; map type->asset_type; rights nested-create -> real rights_records; replace checksum dedup `[0a/decide]` |
| `api/studio/release-gate` | REWRITE | asset_type "MASTER" vocab `[0a]`; rights via real rights_records; keep `deriveBlockers` if fields `@map`, else adapt |
| `api/studio/approve` | REWRITE | rights_records upsert + project.approval/rights_status + agent_runs `[0a]` |
| `api/studio/qa` | REWRITE | rights_records upsert; drop checksum filter |
| `api/studio/queue` | REWRITE | asset.findMany type->asset_type; drop checksum read; rights include |
| `api/studio/run` | REMAP | Run -> agent_runs field set `[0a]` |
| `api/studio/pipeline` | REMAP | project pipeline columns `[0a]`; drop/add per 0a |
| `api/studio/sync` | REWRITE | scenes/shots real columns + FK `[0a]` |
| `api/studio/c2pa` | DEFER | provenance has no real table |
| `api/studio/archive` | DEFER | archive_packages + provenance have no real tables |
| `app/studio/console/page.tsx` | REMAP + STUB | remap project/asset/run/rights reads; stub provenance + archivePackage panels |
| `lib/release-gate.ts` | ADAPT IF NEEDED | only if real rights_records field names cannot be `@map`-ed to the camelCase the gate reads |
| `lib/agents/script-doctor.ts` | OUT OF SCOPE | broken stub imports; flag, do not fix here |

Where `rating` plugs in: `decide(asset)` (Relay, out of scope) layers
distribution-routing + paywall on top of the existing release gate
(`deriveBlockers` + `approvedForRelease`). This plan only guarantees the column +
typed client exist; note the integration point, build nothing.

---

## 7. Disposition of dead artifacts

| Artifact | Disposition | Reason |
|---|---|---|
| `lib/generated/prisma/` | DELETE | orphan; imported by nobody |
| `prisma/studio.prisma` (idealized) | ARCHIVE -> `docs/relay/reference/studio.prisma.idealized` | superseded by canonical; preserves the rich provenance/archive/rights design for the deferred phase |
| `prisma/generated/studio-client/` | REGENERATE | overwritten from canonical schema |
| `prisma/schema.prisma` (Campaign) | KEEP | Campaign track deferred (Decision 3) |
| `prisma/generated/client/` (Campaign) | KEEP | campaign routes still import it |
| `prisma/migrations/20260531182246_init` | ARCHIVE out of active migrations path | Campaign migration was never applied + references nonexistent tables; would otherwise pollute the canonical history. Non-destructive (move, do not delete the record of it). |
| canonical schema | CREATE `prisma/ilyrium.prisma` | new source of truth over real `public` |

---

## 8. Verification plan

1. **Client reads real rows**: on the branch, `studioDb.project.findMany({take:3})`
   and `studioDb.asset.findMany({take:3})` return real populated rows (not empty,
   not a throw). Quick `tsx` script or a temporary route.
2. **`rating` exists + constrains**: `psql ... -c "\d+ public.assets"` shows the
   `rating` column + CHECK; an `INSERT ... rating='bogus'` is REJECTED; valid
   `'clean'|'mature'|'uncensored'` succeed; existing rows read back `'clean'`.
3. **Drift-free**: the Section 5.4 `migrate diff` prints an empty migration.
4. **Previously-broken route runs**: `POST /api/studio/release-gate` with a real
   `externalId` returns 200 with real data (previously threw at runtime).
5. **No regression to Campaign track build**: `prisma generate --schema
   prisma/schema.prisma` + `next build` still succeed (campaign client intact).

---

## 9. Ordered, reversible execution steps (FUTURE session)

Branch-first throughout. R=read, W=write. Each W on the BRANCH unless noted.

0. (R, console) Refresh the `ilyrium` connection string from the Neon console.
   Create a FRESH Neon branch off `ilyrium`; pull ITS connection string. Never
   reuse old strings; never connect to archived `ep-young-voice`/`ep-purple-shape`.
   Set `DATABASE_URL` to the branch string; deactivate venv; verify
   `echo $env:DATABASE_URL`.  STOP/HITL: confirm the branch string before any write.
1. (R, branch) Run Appendix A queries (0a/0c + asset_type distinct + projects
   keys + rights_records columns). Fill every `[confirm 0a]` in Sections 4/6.
   STOP/HITL: review the column map with Brad before rewriting routes.
2. (W, branch) `git checkout -b feat/relay-schema-reconcile` (off
   `feat/creative-loop-v1`). Delete `lib/generated/prisma/`; archive
   `studio.prisma` -> `docs/relay/reference/`; archive the Campaign init
   migration out of `prisma/migrations`.
3. (W, branch) Create `prisma/ilyrium.prisma` (generator block); point
   `prisma.config.ts` schema at it; `prisma db pull`.
4. (W, branch) Review + rename introspected models/`@map`s (Section 5.2).
5. (W, branch) Baseline: `migrate diff --from-empty ... > 0_init/migration.sql`;
   `migrate resolve --applied 0_init`. STOP if the SQL contains any `DROP` /
   `ALTER ... DROP` / data-loss -- show it, do not apply.
6. (R, branch) Drift check (Section 5.4) -> must be empty. STOP if not.
7. (W, branch) Add `rating` to Asset; hand-author the rating migration SQL;
   `prisma migrate deploy`. STOP if the authored SQL is anything other than the
   single additive `ALTER TABLE ... ADD COLUMN rating`.
8. (W, branch) `prisma generate --schema prisma/ilyrium.prisma`.
9. (W, branch) Rewrite/remap routes + console per Section 6; defer c2pa/archive.
10. (R, branch) Run the Section 8 verification suite.
11. (W) Commit; open a PR from the feature branch. PROD (the `ilyrium` DB) is
    touched ONLY when the verified branch migrations are promoted -- a separate,
    explicit STOP/HITL gate, never as part of this branch work.

Reversibility: all DB work happens on a throwaway Neon branch; deletions in
step 2 are moves/archives (recoverable from git); the rating ALTER is additive.

---

## 10. Hard rules (binding on every step)

- NEVER `migrate dev`, `migrate reset`, `--accept-data-loss`, or bare `db push`
  without `--schema`.
- Any generated/authored SQL containing `DROP`, `ALTER ... DROP`, or data-loss:
  STOP and show it; do not apply.
- Fresh Neon branch off `ilyrium` BEFORE touching production; connection string
  from the console; database `ilyrium`, never `neondb`.
- NEVER connect to archived endpoints `ep-young-voice` or `ep-purple-shape`
  (connecting unarchives + resumes billing). The vector/memory DB
  (`ep-purple-shape/ilyrium_memory`) is unrelated -- do not touch it.
- Deactivate the Python venv before any Prisma command; verify `DATABASE_URL`.
- Prisma 7 CLI: `db execute --url` is gone; `migrate diff` drift-check uses
  `--from-config-datasource` + `--to-schema`. Confirm all flags with `--help`
  before running.

---

## Appendix A -- Read-only recon SQL (run against database `ilyrium`)

```sql
-- 0a: full public column map
SELECT table_name, column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;

-- 0c: confirm zero enums
SELECT n.nspname AS schema, t.typname AS enum_type,
       string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) AS labels
FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid
JOIN pg_namespace n ON n.oid = t.typnamespace
GROUP BY 1, 2 ORDER BY 1, 2;

-- asset_type vocabulary (find the release-candidate / MASTER concept)
SELECT asset_type, count(*) FROM public.assets GROUP BY 1 ORDER BY 2 DESC;

-- projects idempotency key (does an external_id / campaign_id / slug exist?)
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema='public' AND table_name='projects' ORDER BY ordinal_position;
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint WHERE conrelid = 'public.projects'::regclass;

-- rights_records shape + assets<->rights linkage (decisive for qa/approve/gate)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='rights_records'
ORDER BY ordinal_position;
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
WHERE conrelid = 'public.rights_records'::regclass;

-- confirm Prisma has never owned public + only public schema exists
SELECT to_regclass('public._prisma_migrations');
SELECT schema_name FROM information_schema.schemata
WHERE schema_name NOT LIKE 'pg_%' AND schema_name <> 'information_schema'
ORDER BY 1;
```
