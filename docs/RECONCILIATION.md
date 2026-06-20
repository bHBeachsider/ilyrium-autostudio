# Ilyrium — Reconciliation & Single Source of Truth (2026-06-20)

Reconciles the two parallel Ilyrium efforts into ONE documented environment before Phase 2
(Relay). Produced from a read-only audit (4 parallel investigations). Destructive/outward
steps (push, Neon-project deletion) are gated on Brad's explicit approval — see **Open
actions**.

## The two efforts & what each owns
- **(A) Cowork — the auto-studio engine.** `apps/auto-studio/` (multi-engine renders,
  take/cut model, Style Kernel, keyframe→image-to-video, scaffolder, per-stage agents, the
  ilyrium-studio MCP) + the Phase-A asset-graph UI/routes in `apps/control-panel/`. Owns
  generation, the Python sync writers (`graph_sync.py`, `producer.py`,
  `studio_pipeline_service.py`), and the pgvector memory (`ilyrium_memory`).
- **(B) Relay — this reconciliation.** Replaced the never-deployed `prisma/studio.prisma`
  with the REAL `prisma/ilyrium.prisma`, rewrote `/api/studio/*` onto `lib/studio-writes.ts`,
  added `assets.rating`, **promoted to production**, and teed up Phase 2
  (`apps/control-panel/docs/relay/PHASE_2_RELAY_KICKOFF.md`). Owns the schema, the route↔DB
  contract, migrations, and the `decide()`/distribution/paywall layer to come.

Net: one DB, one schema, two writer surfaces (the TS routes and the Python sync) that now
converge.

## 1. Canonical schema & code (verified single source of truth)
- **Schema:** `apps/control-panel/prisma/ilyrium.prisma` — the ONLY active schema.
  `prisma.config.ts` `schema` points at it. `prisma/studio.prisma` is **archived**
  (`docs/relay/reference/studio.prisma.idealized`); the campaign `prisma/schema.prisma` and
  `lib/db.ts` are **deleted**.
- **Migrations:** `prisma/migrations/{0_init, 20260620032217_add_asset_rating,
  migration_lock.toml}`. `0_init` = adopt baseline (pure CREATE of the existing 19 tables,
  recorded via `migrate resolve --applied`, never executed). `add_asset_rating` = the single
  additive `ALTER TABLE assets ADD COLUMN rating text NOT NULL DEFAULT 'clean' CHECK (rating
  IN ('clean','mature','uncensored'))`. **Both applied on the branch AND production.**
- **Client:** `lib/studio-db.ts` → `../prisma/generated/studio-client` (the only generated
  client). Routes use it via `lib/studio-writes.ts`.
- **Alignment:** `/api/studio/{sync,asset,…}` ↔ `lib/studio-writes.ts` ↔ `ilyrium.prisma` all
  write only real columns (asset_type validated to the 8-value vocab → 422 otherwise; dedup
  by `uri`; paired `rights_records`; projects get-or-create by `title`). No orphan fields, no
  unset NOT-NULL columns.

## 2. ENV → database map (definitive)
| Logical DB | Used by | Endpoint(s) | Region | Status |
|---|---|---|---|---|
| **`ilyrium`** (studio) | `apps/control-panel` (Prisma/Next), Python sync via the routes | dev `ep-morning-frost-apbgxh31` (`apps/control-panel/.env`) · prod `ep-young-voice-apndapaf` (Vercel target) | c-7 | **ACTIVE** |
| **`ilyrium_memory`** (pgvector/LangChain) | `apps/auto-studio/memory/vector_store.py` | `ep-purple-shape-aqhd4whp` (root `.env` `NEON_DATABASE_URL`) | c-8 | **ACTIVE — keep** |
| `neondb` @ `ep-gentle-fire` | nothing | — | — | **ORPHANED** (no `.env`/code reference) → delete via Neon console |
| `neondb` @ `ep-plain-haze` | **PermitHub** (different product) | — | c-2 | **DO NOT TOUCH** |

- **`ilyrium` is ONE logical DB with two Neon branches** (dev `studio_os_branch1` /
  `ep-morning-frost`; prod `production`=`br-spring-rain-ap81nd7m` / current primary compute
  `ep-young-voice`). Endpoint ids drift; **branch ids are the stable identity.**
- **Distribution question — RESOLVED:** "distribution" is a **`plane` enum value**
  (`agent_runs.plane`, `event_log.producer_plane` ∈
  `concept|production|rights|distribution|studio_os`) within the single `ilyrium` DB. There
  is **NO separate distribution database** — no distinct connection string or DB name exists
  in code or env.

## 3. auto-studio ↔ control-panel ↔ Neon wiring
```
apps/auto-studio (Python)                      apps/control-panel (TS/Next + Prisma)
  producer.py / studio_pipeline_service.py  ──HTTP POST──▶  /api/studio/{sync,asset,run,...}
  graph_sync.py  (asset_type lowercased)                    └▶ lib/studio-writes.ts
        │                                                        └▶ Prisma (ilyrium.prisma)
        │                                                            └▶ Neon `ilyrium` (studio)
  memory/vector_store.py  ──pgvector──▶  Neon `ilyrium_memory`  (separate DB; not touched)
```

### Python payload reconciliation (`graph_sync.sync_asset` → `/api/studio/asset`)
The route consumes `{externalId|title, type, uri, model, provider}`; everything else is
**intentionally dropped** (Fork B: "add only what Relay needs"). Decision: **keep omitted.**
| Payload field | Disposition | Rationale / future path |
|---|---|---|
| `type`,`uri`,`model`,`provider` | **kept** | `asset_type` (validated), `uri` (dedup), `model_id` |
| `checksum` | omit | content-addressing stays Python-side; add `assets.checksum` only if cross-uri dedup is needed |
| `seed` | omit | reproducibility metadata; future `assets.generation_metadata jsonb` if needed |
| `storageProvider`,`sizeBytes`,`mimeType` | omit | not modeled in v1; derive from `uri`/R2 at serve time |
| `sceneNumber` | omit | scene/shot live via `/api/studio/sync`; future `assets.shot_id` FK (exists, unpopulated) |
| `costCents` | omit | already captured in `agent_runs.cost_cents` / `adapter_calls` via `record_run()` |
| `prompt` (text) | omit at asset write | `prompts` table + `assets.prompt_id` FK exist (unpopulated) — wire for lineage in a later phase |
- **Known deferred (not a bug):** `studio_pipeline_service.py:565` sends `asset_type="SUBTITLE"`,
  which the route 422s — this is the **recorded DEFER decision** (`subtitle` not in the vocab;
  no DDL beyond `rating`), not a regression.

## 4. Git branches & strategy
- `main` — release-only; **does not contain `apps/control-panel/`** yet.
- `feat/creative-loop-v1` — **active integration branch** (origin is ~48 ahead of `main`);
  carries the full reconciled app incl. Phase 1 (merged via PR #2 `2780bc24`). *Local copy is
  6 behind origin — pull before working on it.*
- `feat/relay-schema-reconcile` — Phase-1 working branch (reconciliation already on origin via
  PR #2); has **4 unpushed doc-only commits** (`d8bfd0a`,`0ab41c5`,`cf25500`,`1ae275a`).
- **Verified:** `ilyrium.prisma` is byte-identical across `creative-loop-v1` and `relay`; no
  `studio.prisma`/`schema.prisma` on either; no divergent schema copies.

**Strategy (proposed — pending Brad's sign-off):** `feat/creative-loop-v1` is the integration
branch; `main` updates only on a deliberate release cut; **Phase 2 (Relay) branches off
`creative-loop-v1`**; the 4 doc commits get pushed on `relay` (preserve) and optionally
forwarded into `creative-loop-v1` so the integration branch carries the full record. Do NOT
delete `feat/relay-schema-reconcile`.

## 5. `film_projects` — CORRECTION (do NOT delete)
`C:\Users\bradu\Documents\film_projects` is **NOT a stale backup.** It holds a unique,
**unbacked ~45.4 GB production `Blue_Angels_Kathy_Flyby`** (finished renders
`kathy_flyby_v8/v9.mp4`, Blender `composite.blend` modified Jun 4, dialogue audio, source
footage `blue_angels_kathy_house_2min.mp4`, Unreal assets) that exists **nowhere in
`ilyrium-autostudio`** and is **not a git repo**. **Verdict: keep; back `Blue_Angels` up to
cloud.** Only empty cruft inside is `ComfyUI_windows_portable/`, `tools/` (0 bytes) and a
69 KB `ilyrium-bucket-mirror/` stub. (Note: it also contains a `.env` with API keys —
secure it.)

## 6. Environment hygiene (CLI traps)
- The stale `DATABASE_URL` (→ PermitHub `ep-plain-haze/neondb`) and `NODE_ENV=development`
  are **process-scope** (injected by this PermitHub-launched session), **NOT** Windows
  User/Machine vars — nothing to delete. In this session, `unset DATABASE_URL`/`NODE_ENV`
  before any prisma/build command. **A session launched from `ilyrium-autostudio` won't have
  them.**
- Prisma CLI: set `DATABASE_URL` explicitly; use the **direct (non-pooler)** host for DDL;
  drop `channel_binding`. Vercel/runtime uses the **pooled** host. Gate Neon connections on
  **branch identity + console status**, never on `ep-…` endpoint strings (they drift).

## Open actions (ownership)
| Action | Owner | Status |
|---|---|---|
| Push the 4 doc-only commits → `origin/feat/relay-schema-reconcile` | CC (on Brad's go) | **pending approval** |
| Forward doc commits into `feat/creative-loop-v1` (optional) | CC (on Brad's go) | pending |
| Final branch-strategy sign-off | Brad | pending |
| Delete orphaned `ep-gentle-fire`/`neondb` Neon project | **Brad (Neon console)** | repo confirms nothing references it |
| Back up `Blue_Angels_Kathy_Flyby` (45 GB, unbacked) | **Brad** | recommended |
| Do NOT delete `film_projects` | — | corrected (premise was wrong) |
| Phase 2 (Relay) design | CC, fresh session | brainstorm-gated; off `creative-loop-v1` |
