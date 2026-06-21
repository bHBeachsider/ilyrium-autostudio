# Neon topology — Ilyrium (authoritative, 2026-06-21)

> **THE RULE (root cause of this session's confusion): identify Neon projects by
> `project id` + endpoint + actual database contents — NEVER by display name.** The display
> names in this org are actively misleading/inverted (a dead project is named `ilyrium`; the
> real data lives in a project named `studio-os`). Also: `ep-…` compute endpoint ids DRIFT;
> `br-…` branch ids are STABLE. Never key safety on an `ep-…` string.

## The three Ilyrium.io projects (org `org-snowy-frog-64095823`)
| Project ID | display name | endpoint(s) | database(s) | status |
|---|---|---|---|---|
| **`patient-star-32154915`** | `studio-os` | `ep-young-voice-apndapaf` (prod) · `ep-morning-frost-apbgxh31` (dev) | **`ilyrium`** (REAL — `rating` live, 7 assets/2 projects) + `neondb` | **KEEP — production** |
| **`summer-forest-00092208`** | `ilyrium-studio-db` | `ep-purple-shape-aqhd4whp` (c-8) | **`ilyrium_memory`** (pgvector/LangChain) + `neondb` | **KEEP — separate memory store** |
| **`patient-resonance-78640326`** | `ilyrium` | `ep-gentle-fire-ap8c0f9o` | `neondb`: **public** Campaign(10)/Scene(34) + **studio** schema **POPULATED** (5 projects, 21 assets, 24 runs, 21 provenance, 18 scenes/shots, 4 rights, 3 archive) | **ORPHAN but NOT empty** — backed up; **SUSPEND, do not delete without review** |

## Canonical production = `studio-os` (`patient-star-32154915`) / `ilyrium`
- Branches: `production` (`br-odd-surf-ap2vfh9b`, primary compute `ep-young-voice-apndapaf`) +
  `studio_os_branch1` (`br-rough-river-apoi1602`, dev compute `ep-morning-frost-apbgxh31`).
  *(The earlier `br-spring-rain-ap81nd7m` on record was stale.)*
- This is where Phase 1 promoted `assets.rating`. `apps/control-panel/.env` (dev) points at
  `ep-morning-frost`; Vercel (prod) must point at the **pooled** `ep-young-voice` host.
- One logical `ilyrium` DB, two branches; identify by `br-…` ids, not `ep-…` strings.

## Memory = `ilyrium-studio-db` (`summer-forest-00092208`) / `ilyrium_memory`
- pgvector/LangChain long-term memory; used by `apps/auto-studio/memory/vector_store.py`
  (`NEON_DATABASE_URL` in the repo-root `.env`). Region c-8. **Do not touch.**

## Orphan = `patient-resonance-78640326` (display name `ilyrium`) / `neondb` — NOT empty
- Endpoint `ep-gentle-fire` (the "struck" endpoint). Referenced by **no** `.env`/code/`$PROFILE`
  (only docs). BUT it is **not empty scaffold** — `neondb` holds REAL early data:
  - `public`: `Campaign` (10 DRAFT — incl. "Test"/"Test 2" + restaurant-ad drafts), `Scene` (34),
    `_prisma_migrations` (the `20260531182246_init` Campaign migration — it WAS applied here,
    contra the determination's "never applied").
  - `studio`: the idealized `studio.prisma` graph DEPLOYED + populated — `Project` 5, `Asset` 21,
    `Run` 24, `Scene` 18, `Shot` 18, `ProvenanceRecord` 21, `RightsRecord` 4, `ArchivePackage` 3
    (provenance/archive have **no equivalent** in the real `ilyrium` model). This is the early
    "Cowork" Phase-A data, *separate* from the real `ilyrium` (7 assets/2 projects).
- **Full backup taken:** `C:\Users\bradu\patient-resonance-neondb-backup-20260621.sql`
  (pg_dump, public+studio, 108 KB) — so nothing is at risk.
- **Recommendation: SUSPEND, do NOT delete** until Brad reviews the actual `studio.*` data
  (are the 21 assets real renders worth keeping?). Suspend is reversible and ~free for this
  little data. If/when deletion is chosen, do it **strictly by project ID
  `patient-resonance-78640326`** (never by the display name `ilyrium`).

## Connection / CLI hygiene (carry forward)
- Prisma CLI: set `DATABASE_URL` explicitly; **direct (non-pooler)** host for DDL; drop
  `channel_binding`. Vercel/runtime: **pooled** host.
- The stale `DATABASE_URL` (→ PermitHub `ep-plain-haze/neondb`, project `permit-hub-api` in
  Brad's personal org, c-2) and `NODE_ENV=development` are **process-scope** leaks from a
  PermitHub-launched shell — not Windows vars. `unset` both before any prisma/build command;
  a session launched from `ilyrium-autostudio` won't have them. **PermitHub is a separate
  product/org — never touch.**
- Verify any connection with `SELECT current_database()` (`ilyrium`, never `/neondb`) +
  project/branch id; never trust the display name.
