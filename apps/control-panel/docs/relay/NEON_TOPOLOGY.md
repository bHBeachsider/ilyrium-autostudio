# Neon topology — Ilyrium (load-bearing reference, verified 2026-06-21)

> **Read this INSTEAD of re-deriving.** Every claim below has a 30-second re-check next to it.
> **Identify Neon projects by `project id` + database CONTENTS — never by display name** (the
> names here are inverted: a dead project is named `ilyrium`; the real data is in one named
> `studio-os`). **`project ids` and `br-…` branch ids are STABLE; `ep-…` compute ids DRIFT** —
> today's false alarm came from treating an `ep-…` id as stable. Never key safety on `ep-…`.

## 30-second re-verification (run these, don't trust prose)
```bash
unset DATABASE_URL NODE_ENV   # the shell leaks a PermitHub DATABASE_URL (process-scope)
neonctl projects list --org-id org-snowy-frog-64095823 -o json | grep -E '"id"|"name"'
# which project holds the real ilyrium? (answer must be patient-star-32154915):
neonctl databases list --project-id patient-star-32154915 --branch-id br-odd-surf-ap2vfh9b
# production proof (pull the string from Neon console / Vercel; DIRECT host for psql/CLI):
psql "<studio-os/production/ilyrium, direct host>" -c "SELECT current_database();"   # => ilyrium
psql "<...>" -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"  # => 19
psql "<...>" -c "SELECT count(*) FROM information_schema.columns WHERE table_name='assets' AND column_name='rating';"  # => 1 (Phase 1 live)
```

## The three Ilyrium.io projects (org `org-snowy-frog-64095823`) — key by ID
| project id (STABLE) | display name (misleading) | database(s) (the truth) | endpoint(s) (MUTABLE) | verdict |
|---|---|---|---|---|
| **`patient-star-32154915`** | `studio-os` | **`ilyrium`** (real studio DB, `rating` live) + neondb | `ep-young-voice-apndapaf` | **KEEP — production** |
| **`summer-forest-00092208`** | `ilyrium-studio-db` | **`ilyrium_memory`** (pgvector) + neondb | `ep-purple-shape-aqhd4whp` (c-8) | **KEEP — memory store** |
| **`patient-resonance-78640326`** | `ilyrium` | `neondb`: Campaign(10)/Scene(34) + a **populated `studio` schema** (5 proj/21 assets/24 runs/21 provenance/3 archive) | `ep-gentle-fire-ap8c0f9o` | **ORPHAN but NOT empty — backed up; SUSPEND, do not delete w/o review** |

## Canonical production = `patient-star-32154915` (name `studio-os`) / database `ilyrium`
- **Branch ids (STABLE):** `production` = **`br-odd-surf-ap2vfh9b`** · `studio_os_branch1` =
  **`br-rough-river-apoi1602`** (forked from production).
  ⚠️ The `br-spring-rain-ap81nd7m` in older docs/briefs is **STALE — it does not exist.** Verify:
  `neonctl branches list --project-id patient-star-32154915 -o json | grep -E '"id"|"name"'`.
- **Endpoints (MUTABLE — current only):** prod primary compute `ep-young-voice-apndapaf`
  (where Phase 1 promoted `assets.rating`); dev compute `ep-morning-frost-apbgxh31`
  (`apps/control-panel/.env`). These `ep-…` ids can change; re-derive from the branch id, never
  hard-trust them.
- One logical `ilyrium` DB, two branches. Real dataset: 7 assets / 2 projects.

## Memory = `summer-forest-00092208` (name `ilyrium-studio-db`) / `ilyrium_memory`
- pgvector/LangChain long-term memory, used by `apps/auto-studio/memory/vector_store.py`
  (`NEON_DATABASE_URL` in the repo-root `.env`), region c-8. **Separate project. Do not touch.**

## Orphan = `patient-resonance-78640326` (name `ilyrium`) / `neondb` — NOT empty
- Referenced by **no** `.env`/code/`$PROFILE` (only docs). But `neondb` holds real EARLY
  "Cowork" data: `public` Campaign/Scene drafts + a populated `studio` schema (the idealized
  `studio.prisma` was deployed here; provenance/archive have **no equivalent** in the real
  `ilyrium`). Separate from the real DB.
- **Full backup:** `C:\Users\bradu\patient-resonance-neondb-backup-20260621.sql` (pg_dump,
  public+studio, 108 KB). Re-check contents:
  `neonctl connection-string --project-id patient-resonance-78640326 --branch-id br-solitary-wind-apuboqas --database-name neondb` then
  `psql "<that>" -c "SELECT count(*) FROM studio.\"Asset\";"`.
- **SUSPEND / leave idle — do NOT delete** until the `studio.*` assets are reviewed. If ever
  deleted, strictly by **project id `patient-resonance-78640326`** (never by the name `ilyrium`).

## Named anti-patterns (each = an hour lost this session)
- **Names are inverted.** Three projects all read like "ilyrium" — identify by **id + contents**.
- **`ep-…` ids drift; `br-…`/project ids are stable.** Never gate safety on an `ep-…` string
  (that produced the "ep-young-voice is archived" false alarm — it's production-idle).
- **`/ilyrium`, never `/neondb`.** A wrong-db string CONNECTS and shows Campaign/Scene instead
  of erroring. Always `SELECT current_database()` = `ilyrium` before trusting a connection.
- **Pooled vs direct host:** **direct** (non-`-pooler`) host for the Prisma CLI/DDL **and the
  Phase 2 Graphile Worker** (LISTEN/NOTIFY cannot go through the pooler); **pooled** (`-pooler`)
  host for Vercel/serverless runtime.
- **Drop `channel_binding=require`** for Prisma's native connector (caused P1000); psql tolerates it.
- **Shell `$env:DATABASE_URL` overrides `.env`** under dotenv. This session leaks a process-scope
  `DATABASE_URL` (→ PermitHub `ep-plain-haze/neondb`, a SEPARATE product/org — never touch) and
  `NODE_ENV=development` (crashes `next build`). Start a clean shell; verify with `echo $DATABASE_URL`
  (empty) and `unset` both. A session launched from `ilyrium-autostudio` doesn't have the leak.

## Secrets
This doc has **no passwords** by design — endpoint hosts + project/branch ids are safe to commit.
Pull the actual connection string from the **Neon console** or **Vercel env** at point of use;
never paste a credential here or into git.
