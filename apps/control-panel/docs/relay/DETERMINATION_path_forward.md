# DETERMINATION: Path Forward for the ilyrium Schema Reconciliation

> Status: DETERMINATION ONLY (read-only investigation). Nothing executed: no
> db pull, no migrations, no ALTER, no Neon branch, no prisma generate. Forks
> resolved from the REAL writer code + DDL, with adversarial verification.
> This document supersedes Section 0 of `PLAN_schema_reconciliation.md` and adds
> a premise correction (Section 0 below) that the plan did not account for.

> **ENDPOINT RECORD CORRECTION (2026-06-20):** The Neon endpoint-id blocklist in this doc
> is STALE. `ep-...` compute ids drift; `br-...` branch ids are stable — so safety must key
> on BRANCH identity + console status, NOT endpoint-id strings. Production = branch
> **`br-spring-rain-ap81nd7m`**, whose CURRENT primary compute is **`ep-young-voice-apndapaf`**
> (console: production (Default) / Primary / Idle — normal, NOT archived). The old
> "never-connect `ep-young-voice`/`ep-purple-shape`" rule is superseded. `ep-purple-shape` =
> the separate **`ilyrium_memory`** (pgvector) DB — out of scope regardless (different
> database, do not touch). Full corrected map + gate logic + the Step-9 promotion plan:
> see `RUNBOOK_phase1.md` → "Endpoint record correction + Step-9 promotion plan."
> **Definitive, load-bearing Neon map (project/branch ids + re-verify commands + anti-patterns):
> `docs/relay/NEON_TOPOLOGY.md`.** (NB: this doc's `br-spring-rain-ap81nd7m` is STALE — the real
> production branch is `br-odd-surf-ap2vfh9b`, project `patient-star-32154915`.)

---

## 0. PREMISE CORRECTION (read this first) -- there are TWO control-panels

The investigation found the real writer of the `ilyrium` database is NOT the
Python pipeline and NOT `ilyrium-autostudio/apps/control-panel`. It is a SEPARATE,
git-tracked, Vercel-deployed app:

| Repo / app | Tracked? | DB role | Stack | API surface | UI |
|---|---|---|---|---|---|
| `C:\Users\bradu\Documents\Ilyrium\apps\control-panel` | YES (git, 4 commits to 2026-06-18) | **OWNS + WRITES the `ilyrium` DB** | raw SQL via `@neondatabase/serverless` | `/api/generate`, `/api/asset`, `/api/gates` | partly stubbed ("sample data until orchestrator API is wired") |
| `C:\Users\bradu\Documents\ilyrium-autostudio\apps\control-panel` (this repo) | NO (`?? apps/control-panel/`, untracked) | broken vs real DB | Prisma 7 + PrismaNeon | the 10 `/api/studio/*` routes + Campaign | rich studio console (~50 fetch calls to `/api/studio/*`) |

These are two halves of one product that were never joined:
- `Ilyrium` holds the **schema (DDL) + the working writers** but a stubbed UI.
- `ilyrium-autostudio/control-panel` holds the **studio console UI + the
  `/api/studio/*` surface the Python pipeline targets**, but its DB layer
  (`studio.prisma`) was never deployed and never worked.

Evidence the Python pipeline targets THIS repo's studio API (not Ilyrium):
`ilyrium-autostudio/apps/auto-studio/graph_sync.py` POSTs assets to
`http://127.0.0.1:3000/api/studio/asset` -- an endpoint that exists ONLY in
`ilyrium-autostudio/apps/control-panel` (Ilyrium has no `/api/studio/*`). So this
repo's studio routes were built to be the Python sync backend; they just never
had a working DB layer.

### Decision 0 (STRATEGIC -- for Brad; does NOT block the per-entity work)
Because `Ilyrium/apps/control-panel` already reads/writes the real DB correctly,
its raw-SQL writers are the **reference implementation** the reconciled routes
must conform to. Two coherent go-forward shapes:

- **0-A (recommended): Reconcile this repo's `/api/studio/*` to the real DB AND
  conform to Ilyrium's writer conventions.** Keep the studio console + Python-sync
  surface here; make its writes byte-compatible with Ilyrium's (lowercase
  `asset_type`, project-by-id, `uri` dedup, real `rights_records` shape). Two apps
  coexist on one DB. This preserves the UI + Python-sync investment and matches the
  locked plan -- the only change is that Ilyrium's SQL becomes the conformance spec.
- **0-B: Consolidate onto `Ilyrium/apps/control-panel`.** Port the `/api/studio/*`
  surface + console into Ilyrium (raw SQL, no Prisma) and retire this repo's
  control-panel. Cleaner single-app architecture, but discards the Prisma work and
  moves the UI.

Recommendation: **0-A** -- it keeps the locked plan valid and is lower-churn; the
"real DB wins" direction already forces conformance to Ilyrium's conventions, so
the two apps stay write-compatible. Flagging 0-B as the alternative if a single
codebase is preferred. The forks below are resolved identically under either
choice (the column-level truth is the same); only the mechanism differs
(Prisma-client rewrite under 0-A vs raw-SQL port under 0-B).

---

## 1. Fork C -- connection target + corrected runbook (replaces plan Section 0)

### Confirmed canonical target
- Neon project **`studio-os`** (Ilyrium.io org), branch **`production`**
  (`br-spring-rain-ap81nd7m`), database **`ilyrium`**, role `neondb_owner`.
- `ep-gentle-fire` is **STRUCK** -- both apps' configs wrongly reference it.
  `ilyrium-autostudio/apps/control-panel/.env` currently reads (credential redacted):
  `DATABASE_URL=postgresql://neondb_owner:<REDACTED>@ep-gentle-fire-ap8c0f9o-pooler.c-7.us-east-1.aws.neon.tech/ilyrium?sslmode=require=require`
  -- note it is BOTH the wrong endpoint AND malformed (`sslmode=require=require`,
  a duplicated token). A `psql` probe of that host returned
  `password authentication failed` (stale cred). Remove it.
- **The authoritative correct string is whatever `Ilyrium/apps/control-panel`
  uses in its Vercel env** -- that app provably writes the real data, so its
  `DATABASE_URL` resolves to studio-os/production/ilyrium. Pull it from the Ilyrium
  Vercel project (or the studio-os console). `Ilyrium/lib/db.ts` reads
  `process.env.DATABASE_URL` via `neon(...)`; there is no committed `.env`.

### Verification gate (the connection trap)
A wrong-project string, or `/neondb` instead of `/ilyrium`, CONNECTS and shows
plausible-but-wrong Campaign/Scene data instead of erroring. Every string MUST be
verified before use:
- `SELECT current_database();` returns `ilyrium`, AND
- a table-list check shows the 19 snake_case tables (assets, projects,
  rights_records, releases, gate_approvals, greenlight_scores, ...).

### Write-work runbook
- For db pull / baseline / rating migration / route rewrites: branch off
  **`production` in `studio-os`** -> a FRESH, protected (non-expiring) branch.
  NOT `relay-test`/`ep-nameless-star` (expires ~Jun 20 2026), NOT `production`
  directly, NOT `ep-young-voice`/`ep-purple-shape` (archived -> unarchive bills).
- Pull the branch string from the studio-os console; `/ilyrium` path; **direct
  (non-`-pooler`) host** for the Prisma CLI native connector; `sslmode=require`;
  **drop `channel_binding=require`** (it produced P1000 with the native connector).
  Runtime (the Neon driver-adapter / `@neondatabase/serverless`) uses WebSockets
  and the pooled host is fine; only the CLI needs the direct host.
- Start in a CLEAN shell: `echo $env:DATABASE_URL` must be empty so `.env` is
  authoritative (a manually-set var shadows `.env` under Prisma's dotenv loader --
  prior churn). `deactivate` any Python venv first (stale PermitHub
  `ep-plain-haze` var).
- Both `lib/db.ts` and `lib/studio-db.ts` in this repo read `DATABASE_URL`; fix
  `.env` to the correct studio-os/production/ilyrium string (and the malformed
  `sslmode`). The Python pipeline's `NEON_DATABASE_URL` (vector_store.py) points
  at a DIFFERENT db (`ilyrium_memory`, pgvector) -- leave it alone.

---

## 2. Fork A -- projects identity key  =>  RESOLVED: A2 (id-only, no external key)

**Verdict: A2.** Do NOT add `external_id`. Rewrite the routes' `upsert by
externalId` to resolve/create projects by `id`, mirroring the real app.

Evidence (real writer + DDL):
- DDL: `projects` has only the `id` PK; no external_id/slug/unique.
  `Ilyrium/.../db/migrations/0001_studio_os_spine.sql:36-45`:
  `create table if not exists projects ( id uuid primary key default
  gen_random_uuid(), title text not null, type text not null check (type in
  ('short','pilot','series','commercial','feature')), status text not null default
  'active', owner_id uuid references users(id), budget_cents integer not null
  default 0, greenlight_level text check (greenlight_level in
  ('G0'..'G7')) default 'G0', created_at timestamptz not null default now() );`
- Writer resolves by `title` (application-level, not a DB unique):
  `Ilyrium/.../scripts/seed-baseline.mjs:29-41` `getOrCreateProject({title,type})`
  does `select id from projects where title = ${title} limit 1` then INSERT.
- `Ilyrium/.../app/api/generate/route.ts:109-120` looks up the project by title
  and 404s if absent ("Seed it first").
- The Python pipeline uses `externalId` (a campaign_id / scaffold slug) only as
  local directory naming + HTTP transport metadata, never as a DB key
  (`auto-studio/graph_sync.py:55-66`, `studio_pipeline_service.py:100-108`).

Route implication: `/api/studio/{sync,asset,run,pipeline}` should accept
`externalId` in the payload for workflow tracking only, resolve the project by
`id` (or, to match Ilyrium, get-or-create by `title`), and return `{id}` so
callers learn the UUID. The studio routes' pipeline columns
(`pipelineState/pipelineStage/autonomyMode/scaffoldPath/styleKernel`) have NO real
`projects` columns -> drop them or relocate to a JSON/side table later; they are
not required for the Relay precondition.

---

## 3. Fork B -- asset identity + "master" + metadata  =>  RESOLVED

Verdict per sub-item, grounded in the DDL + both writers:

**B-master (CASE + concept): use lowercase `master`; address the candidate via
`releases.master_asset_id`.**
- DDL `assets.asset_type` is `text` with a CHECK:
  `Ilyrium/.../0001_studio_os_spine.sql:162`
  `asset_type text check (asset_type in
  ('image','video','voice','music','still','master','reference','board'))`.
  So `master` IS a valid value; there is NO `MASTER`/`VIDEO`/`IMAGE` (uppercase).
- The real writer assigns lowercase from the file path:
  `Ilyrium/.../scripts/ingest-assets.mjs:82-91` `inferAssetType()` returns
  `"master"` for `/07_delivery/masters/`, `"reference"`, `"board"`, `"image"`,
  `"video"`.
- WARNING -- writer case conflict: the Python sync sends UPPERCASE
  (`auto-studio/producer.py:254,314,382` -> `asset_type="VIDEO"`/`"MASTER"`;
  `graph_sync.py:55-66` default `asset_type="VIDEO"`). Those POST to the
  (broken) `/api/studio/asset`. When that route is rewritten it MUST normalize to
  lowercase before insert or the CHECK rejects the row. Document the
  normalization in the route.
- `releases.master_asset_id` exists and is FK-validated to `assets(id)`
  (`0001b_remaining_tables.sql:32-46`). The release gate should address the
  release candidate via `releases.master_asset_id` (or `asset_type='master'`,
  latest by `created_at`) -- NOT via a checksum lookup.

**B-checksum (identity/dedup): do NOT add checksum; dedup by `uri` (matches the
authoritative writer).**
- The authoritative writer dedups by URI, not content hash:
  `Ilyrium/.../scripts/ingest-assets.mjs:222-224`
  `const existing = await sql\`select id from assets where uri=${uri} limit 1\`;
  if (existing.length>0) { ...skip }`, then INSERT `(project_id, asset_type,
  model_id, uri, version)`.
- `assets` has no checksum/unique beyond `id` (DDL `:158-171`).
- Counter-signal (the tradeoff): the Python `graph_sync.file_checksum()` computes
  SHA-256 and intends checksum idempotency (`graph_sync.py:45-66`). But it is not
  the canonical DB writer (its endpoint is dead), and per the locked "real DB
  wins" direction the authoritative pattern is `uri` dedup. Recommendation: keep
  `uri` (or `(project_id, uri)`) as identity now; treat content-addressed checksum
  as a FUTURE enhancement only if cross-URI dedup becomes a real need. Not added.

**B-metadata (`storage_provider`/`size_bytes`/`mime_type`): add NONE now.**
- The authoritative writer stores none; `assets` carries only `uri` (r2://...).
  Relay can derive content-type from the URI extension or R2 object metadata at
  serve time, so `mime_type` is not required for the Relay precondition. Do not
  re-introduce the idealized columns. (`add only what Relay needs`.)

**`rating` reaffirmed:** `ALTER TABLE public.assets ADD COLUMN rating text NOT NULL
DEFAULT 'clean' CHECK (rating IN ('clean','mature','uncensored'));` -- this is
CONSISTENT with the DB convention: the DDL has zero pg enums; every enumerated
field is `text` + CHECK (`asset_type`, `type`, `greenlight_level`, the `*_risk`
columns). Domain enforced in `decide()`; CHECK is belt-and-suspenders. The ONLY
column added by this work.

Net: `assets` post-reconcile = the existing 9 real columns + `rating`. Asset
identity = `id`; dedup = `uri`. No checksum/storage/size/mime.

---

## 4. Fork D -- Campaign / two-project question  =>  RESOLVED: RETIRE

The Campaign/Scene video track in this repo is dead code: untracked, uncalled,
and unimplemented. Recommend retiring it (the locked plan said "defer"; the
evidence supports retire, but retire is still optional -- it blocks nothing).

Evidence:
- Untracked: git shows `?? apps/control-panel/` for the whole dir.
- Zero live callers: no UI `fetch('/api/campaigns')` or `/api/webhooks/video-render`;
  the studio console only calls `/api/studio/*`.
- Not implemented: `lib/agents/assembly.ts:41-57` ffmpeg pipeline is fully
  commented out; `lib/agents/production-dispatcher.ts:4-5` imports
  `@/lib/media/audio` + `@/lib/media/video` which do not exist.
- Superseded location: `Ilyrium/apps/control-panel` (the real app) has NO
  Campaign concept (no `/api/campaigns`, no `agents/` dir, `git ls-files |
  grep -i campaign` empty).
- Its tables live in `patient-resonance`/`neondb` via the never-applied
  `20260531182246_init` migration -- a different Neon project entirely.

Action (if retiring): remove `app/api/campaigns`, `app/api/webhooks/video-render`,
`lib/agents/assembly.ts`, `lib/agents/production-dispatcher.ts`,
`prisma/schema.prisma` (+ generated client), and archive the init migration with a
note. If keeping the option open, leave them untouched (still non-blocking). Note:
the `decide()`/Relay distribution layer should map onto the REAL `releases` table,
not the Campaign track.

---

## 5. Updated per-entity reconciliation (routes -> real columns/tables)

Conform every write to the `Ilyrium` raw-SQL reference implementation. Identity:
projects by `id` (Fork A), assets by `id`/`uri` (Fork B).

### Asset (real `public.assets`, ground truth)
id (uuid) | project_id | shot_id | asset_type text CHECK(8 lowercase) | model_id
text | prompt_id | uri text NOT NULL | version int default 1 | created_at | +rating.
Route fixes: drop `checksum/storageProvider/sizeBytes/mimeType`; map
`type` -> `asset_type` (lowercase, normalize incoming UPPERCASE); drop the
`provenance` nested write (no table -- provenance is normalized via
`model_id`/`prompt_id`/`adapter_calls`/`prompts`); `MASTER` -> `master`.

### Rights / approve / qa / release-gate -> REAL governance tables (a REWRITE, not a remap)
The idealized `RightsRecord` (qaPassed/noLikenessConfirmed/<state> in
UNREVIEWED/PENDING/CLEARED/BLOCKED) does NOT match the real risk-based model. Real:
- `rights_records` (`0001_studio_os_spine.sql:176-204`): `asset_id` FK,
  `approved_for_release boolean default false`, `approved_by uuid->users`,
  `approved_at timestamptz`, `risk_level text CHECK(low/medium/high)`,
  `release_required boolean`, `release_status text default 'pending'`,
  `likeness_risk/music_risk/trademark_risk text CHECK(none/low/medium/high)`,
  `synthetic_performer_flag/digital_replica_flag/training_data_outbound_flag bool`,
  `sag_aftra_notice_filed_at`, `source_type/creator/model_used/license_type`,
  `commercial_use_allowed`, `third_party_refs text[]`, `legal_notes`.
- `gate_approvals`: `gate_type, entity_type, entity_id, required_role,
  required_cosigners[], state, sla_hours, requested_at/resolved_at, resolved_by,
  trace_reviewed`.
- `greenlight_scores`: `concept_id, level, creative/audience/risk/business_score,
  decision, scored_by`.
- `releases`: `project_id, master_asset_id, platform, version_variant,
  hook_variant, scheduled_at, published_at, status`.

| Route | Rewrite onto real tables |
|---|---|
| `release-gate` | find candidate via `assets.asset_type='master'` (or `releases.master_asset_id`); join `rights_records` on `asset_id`; allowed iff `approved_for_release=true` AND (`release_required=false` OR `release_status` in approved/released). Rewrite `deriveBlockers` to real fields: not-approved; `release_required` && not approved; any `*_risk='high'`; `synthetic_performer_flag` && `sag_aftra_notice_filed_at` null. |
| `approve` | set `rights_records.approved_for_release=true, approved_by, approved_at=now(), release_status='approved'`; insert a `gate_approvals` row (`gate_type='release', entity_type='asset', entity_id=asset_id, state='approved', resolved_by, resolved_at, trace_reviewed`); log to `agent_runs`. Drop the project-level `approval/rightsStatus` write (no such `projects` columns; project has `status`/`greenlight_level` only). |
| `qa` | map onto `gate_approvals` (`gate_type='qa'`, entity_type='asset', entity_id=asset_id) ONLY. NOT `greenlight_scores` -- that is CONCEPT-scoped creative scoring (concept_id, decision in promote/hold/kill/reshape), not per-asset QA. Drop `qa_passed/qa_report` (no columns). |
| `run` | REWRITE onto `agent_runs` (see 5a -- NO project_id/entityType/entityId; `inputs/outputs` -> text `input_ref/output_ref`; `agentName->agent_name`; `plane` is REQUIRED; `status->human_gate_status` with a different vocab). |
| `sync` | scenes/shots are MINIMAL real tables (see 5a): scene has `scene_number`+`description` only (no title/synopsis/orderIndex); shot has `shot_number`+`description` (NOT NULL, no `prompt` column). Map title/synopsis->description, orderIndex->scene_number, shot.prompt->shots.description; resolve project by id. |
| `pipeline` | project has no pipeline columns -> drop or move to JSON side-state. |
| `c2pa`, `archive` | DROP (no `provenance_records`/`archive_packages`; provenance is normalized; archive out of scope). |
| `asset` | rewrite to the real `assets` insert shape (Fork B); normalize asset_type case; dedup by `uri`; write paired `rights_records` like `Ilyrium/app/api/generate/route.ts:170-182`. |
| console | remap to real reads; drop provenance/archive panels. |

`Ilyrium/app/api/generate/route.ts:170-182` is the canonical example of the
asset+rights_records write pair -- mirror it.

---

## 5a. Real support/governance table columns (verbatim DDL) -- closes every `(confirm)`

Read directly from `Ilyrium/.../db/migrations/0001_studio_os_spine.sql` (line
refs in parens). These are the ground-truth columns the rewrites map onto; no DB
needed. Constraints noted where they bind the route logic.

- **scenes** (`126-132`): `id uuid PK | project_id uuid | scene_number integer |
  description text | created_at timestamptz`. NO title/synopsis/orderIndex. The
  `sync` route's `title`/`synopsis` -> `description`; `orderIndex` -> `scene_number`.
- **shots** (`137-150`): `id | project_id | scene_id | shot_number integer NOT
  NULL | description text NOT NULL | camera text | characters uuid[] | location_id
  | status text default 'pending' | approved_take_id uuid (soft ref to assets) |
  cost_cents integer default 0 | created_at`. NO `prompt` column -> `sync`'s shot
  `prompt` text lands in `description` (which is NOT NULL, so it MUST be supplied).
  **`approved_take_id` is the real "selected take"** -- the chosen master asset for
  a shot is recorded here (replaces the idealized `Take.selectedForShot`).
- **prompts** (`104-116`): `id | project_id | text NOT NULL | negative_text |
  reference_assets uuid[] | model_id | settings_json jsonb | success_score real |
  reuse_tag | text_embedding vector(1536) | created_at`. Asset provenance =
  `assets.prompt_id` -> this table (NOT a provenance_records relation).
- **agent_runs** (`265-280`): `id | agent_name text NOT NULL | plane text NOT NULL
  CHECK(concept|production|rights|distribution|studio_os) | input_ref text |
  output_ref text | model_used text | tokens_in int | tokens_out int | latency_ms
  int | cost_cents int | human_gate_status text CHECK(pending|approved|rejected|
  auto_approved|timeout|revision_requested) | started_at | completed_at`.
  => `run` route mapping: `agentName->agent_name`; `costCents->cost_cents`;
  `latencyMs->latency_ms`; `inputs/outputs` (JSON in the old model) -> serialize to
  `input_ref/output_ref` TEXT; `status` -> `human_gate_status` (translate the
  RunStatus vocab QUEUED/RUNNING/SUCCEEDED/FAILED to the real human_gate vocab).
  DROP `project`/`entityType`/`entityId` (no such columns). SUPPLY `plane` (NOT
  NULL) -- pick the plane the route represents (e.g. 'production' or 'studio_os').
- **gate_approvals** (`288-305`): `id | agent_run_id uuid (FK agent_runs) |
  gate_type text NOT NULL | entity_type text NOT NULL | entity_id uuid NOT NULL |
  required_role text NOT NULL | required_cosigners text[] | state text NOT NULL
  CHECK(pending|approved|rejected|revision_requested|timeout|auto_approved) default
  'pending' | sla_hours int NOT NULL default 24 | requested_at | resolved_at |
  resolved_by uuid->users | resolution_note text | trace_reviewed boolean default
  false`. => `approve`/`qa` must supply gate_type, entity_type='asset',
  entity_id=asset_id, required_role; field is `resolution_note` (singular). Note
  the FK is `agent_run_id` (an approval is tied to an agent run, not directly to
  the asset -- entity_id carries the asset id).
- **greenlight_scores** (`246-258`): `id | concept_id uuid (FK concepts) | level
  text NOT NULL CHECK(G0..G7) | scored_by uuid->users | scored_at | creative_score
  int | audience_score int | risk_score int | business_score int | decision text
  NOT NULL CHECK(promote|hold|kill|reshape) | notes`. CONCEPT-scoped -- do NOT use
  for asset QA.
- **releases** (`209-219`): `id | project_id | master_asset_id uuid (FK assets) |
  platform text | version_variant text | hook_variant text | scheduled_at |
  published_at | status text default 'scheduled' | created_at`. The Relay/`decide()`
  distribution layer writes here; the release candidate = `master_asset_id`.
- **adapter_calls** (`328-340`): `id bigserial | agent_run_id uuid (FK) |
  capability text NOT NULL | vendor text NOT NULL | cost_cents | latency_ms |
  status text CHECK(ok|retried|failed_then_fallback|refused_cap|failed) | attempt
  int default 1 | fallback_chain text[] | occurred_at`. Part of normalized
  provenance/telemetry (with `assets.model_id`); not a route target now.

### Introspection gotchas for the baseline step (Section 6 step 4-5)
- **pgvector**: `prompts.text_embedding vector(1536)` will introspect as Prisma
  `Unsupported("vector(1536)")` (kept in the model, not queryable via the typed
  client) -- expected, not an error. Don't "fix" it.
- **Extensions**: the schema needs `pgcrypto` (gen_random_uuid) + `vector`. They
  already exist in the live DB. To keep the baseline `migrate diff --from-empty`
  drift-free, either declare them via the `postgresqlExtensions` preview feature in
  the introspected schema, or accept that the from-empty baseline emits
  `CREATE EXTENSION IF NOT EXISTS` (harmless, never executed -- it's `resolve
  --applied`). Verify the step-6 drift check is empty either way.
- **bigserial PKs** (performance_metrics, event_log, adapter_calls, audit_log)
  introspect cleanly as autoincrement; no action.

---

## 6. Updated ordered, reversible execution steps

Branch-first. R=read, W=write. Each W on the throwaway studio-os branch unless noted.

0. (Decision) Brad picks Decision 0 (0-A reconcile-here vs 0-B consolidate-on-Ilyrium).
   The steps below assume 0-A; under 0-B they become "port `/api/studio/*` into
   Ilyrium as raw SQL" with the same column mappings.
1. (R, console) From `Ilyrium`'s Vercel env or the studio-os console, obtain the
   working studio-os/production/ilyrium string. Create a FRESH protected branch off
   `production`; pull ITS string (direct host for CLI). Fix this repo's `.env`
   (correct endpoint + `sslmode=require`, drop the duplicated token). Clean shell;
   venv deactivated. VERIFY: `SELECT current_database()` -> `ilyrium` + 19-table
   list. STOP/HITL before any write.
2. (R) Confirm remaining real column sets not fully quoted here: `agent_runs`,
   `gate_approvals`, `greenlight_scores`, `scenes`, `shots`, `prompts`,
   `adapter_calls` -- read them straight from
   `Ilyrium/.../db/migrations/0001_studio_os_spine.sql` (no DB needed; the SQL is
   ground truth). Fill the `(confirm)` cells in Section 5.
3. (W) `git checkout -b feat/relay-schema-reconcile` (off `feat/creative-loop-v1`).
   Delete `lib/generated/prisma/` (orphan); archive `prisma/studio.prisma` ->
   `docs/relay/reference/`; (if retiring Campaign per Fork D) remove its files +
   archive its migration.
4. (W) Create `prisma/ilyrium.prisma` (generator block, output
   `./generated/studio-client`); point `prisma.config.ts` schema at it;
   `prisma db pull`. Review introspected models; `@map` snake_case -> chosen TS
   names; rename `AgentRun -> Run @@map("agent_runs")` to minimize route churn.
5. (W) Baseline (adopt without recreating): `migrate diff --from-empty
   --to-schema-datamodel prisma/ilyrium.prisma --script > prisma/migrations/0_init/
   migration.sql`; `migrate resolve --applied 0_init`. CONFIRM flags via `--help`.
   STOP if the SQL contains any `DROP`/`ALTER ... DROP`/data-loss.
6. (R) Drift check: `migrate diff --from-config-datasource prisma.config.ts
   --to-schema prisma/ilyrium.prisma --script` MUST be empty. STOP if not.
7. (W) Add `rating String @default("clean")` to Asset; hand-author
   `prisma/migrations/<ts>_add_asset_rating/migration.sql` with the single additive
   `ALTER TABLE public.assets ADD COLUMN rating ... CHECK (...)`; `migrate deploy`
   (NEVER `migrate dev`). STOP if the SQL is anything but that one ADD COLUMN.
8. (W) `prisma generate --schema prisma/ilyrium.prisma`.
9. (W) Rewrite routes/console per Section 5 (conform to Ilyrium's writers):
   projects by id; assets by uri + lowercase asset_type + case-normalization;
   rights/approve/qa/release-gate onto `rights_records`/`gate_approvals`/
   `greenlight_scores`/`releases`; drop `c2pa`/`archive`.
10. (R) Verify: `studioDb.project.findMany({take:3})` + `asset.findMany({take:3})`
    return real rows; `\d+ assets` shows `rating` + CHECK; a bad rating INSERT is
    rejected; `POST /api/studio/release-gate` with a real master returns 200.
11. (W) Commit; PR. Promote to studio-os `production` only behind a separate,
    explicit STOP/HITL gate (verified branch -> production migration), never as
    part of branch work.

Reversibility: all DB work on a throwaway studio-os branch; step-3 removals are
git-recoverable; the `rating` ALTER is additive.

---

## 7. Hard rules (binding)
- NEVER `migrate dev` / `migrate reset` / `--accept-data-loss` / bare `db push`
  without `--schema`. STOP + surface any `DROP`/`ALTER ... DROP`/data-loss SQL.
- Branch off `production` in `studio-os` BEFORE any write; strings from the
  studio-os console / Ilyrium Vercel env; database `ilyrium`, never `neondb`;
  verify with `current_database()` + the 19-table list.
- NEVER connect `ep-young-voice`/`ep-purple-shape` (archived -> billing).
  `ep-gentle-fire` is STRUCK (wrong). `relay-test`/`ep-nameless-star` expires
  ~Jun 20 2026 -- do not build on it.
- Clean shell (`echo $env:DATABASE_URL` empty so `.env` wins); `deactivate` the
  Python venv. The Python `NEON_DATABASE_URL` (ilyrium_memory/pgvector) is a
  DIFFERENT db -- do not touch.
- Prisma CLI: `db execute --url` is gone; `migrate diff` drift-check uses
  `--from-config-datasource` + `--to-schema`; confirm all flags with `--help`.
  Native connector (CLI) needs the direct, non-pooled host; the driver-adapter
  runtime uses WebSockets (pooled host fine).

---

## Appendix -- key DDL evidence (verbatim, `Ilyrium/apps/control-panel/db/migrations/`)

```sql
-- 0001_studio_os_spine.sql:36-45
create table if not exists projects (
    id                  uuid primary key default gen_random_uuid(),
    title               text not null,
    type                text not null check (type in ('short','pilot','series','commercial','feature')),
    status              text not null default 'active',
    owner_id            uuid references users(id),
    budget_cents        integer not null default 0,
    greenlight_level    text check (greenlight_level in ('G0','G1','G2','G3','G4','G5','G6','G7')) default 'G0',
    created_at          timestamptz not null default now()
);

-- 0001_studio_os_spine.sql:158-171
create table if not exists assets (
    id              uuid primary key default gen_random_uuid(),
    project_id      uuid references projects(id) on delete set null,
    shot_id         uuid references shots(id) on delete set null,
    asset_type      text check (asset_type in ('image','video','voice','music','still','master','reference','board')),
    model_id        text,
    prompt_id       uuid references prompts(id) on delete set null,
    uri             text not null,
    version         integer default 1,
    created_at      timestamptz not null default now()
);

-- 0001b_remaining_tables.sql:32-41
create table if not exists releases (
    id uuid primary key default gen_random_uuid(),
    project_id uuid references projects(id) on delete cascade,
    master_asset_id uuid references assets(id),
    platform text,
    version_variant text,
    hook_variant text,
    scheduled_at timestamptz,
    published_at timestamptz,
    status text default 'scheduled',
    created_at timestamptz not null default now()
);

-- 0001_studio_os_spine.sql:176-204 (rights_records, risk-based -- NOT the idealized state model)
create table if not exists rights_records (
    id uuid primary key default gen_random_uuid(),
    asset_id uuid references assets(id) on delete cascade,
    source_type text, creator text, model_used text, license_type text,
    commercial_use_allowed boolean, third_party_refs text[],
    likeness_risk text check (likeness_risk in ('none','low','medium','high')) default 'none',
    music_risk text check (music_risk in ('none','low','medium','high')) default 'none',
    trademark_risk text check (trademark_risk in ('none','low','medium','high')) default 'none',
    synthetic_performer_flag boolean default false,
    digital_replica_flag boolean default false,
    training_data_outbound_flag boolean default false,
    sag_aftra_notice_filed_at timestamptz,
    risk_level text check (risk_level in ('low','medium','high')) default 'low',
    release_required boolean default false,
    release_status text default 'pending',
    legal_notes text,
    approved_for_release boolean default false,
    approved_by uuid references users(id),
    approved_at timestamptz
);
```

### Writer evidence (real, authoritative)
- Projects get-or-create by title: `Ilyrium/.../scripts/seed-baseline.mjs:29-41`.
- Asset type inferred lowercase from path: `Ilyrium/.../scripts/ingest-assets.mjs:82-91`.
- Asset insert (no checksum) + uri dedup: `ingest-assets.mjs:222-224, 250-254`.
- Asset + rights_records write pair: `Ilyrium/.../app/api/generate/route.ts:158-182`.
- DB driver: `Ilyrium/.../lib/db.ts` -> `export const sql = neon(process.env.DATABASE_URL ?? "")`.
- Python sync (UPPERCASE type, SHA-256 checksum) to dead `/api/studio/asset`:
  `auto-studio/graph_sync.py:45-75`, `auto-studio/producer.py:254,314,382`.
```
