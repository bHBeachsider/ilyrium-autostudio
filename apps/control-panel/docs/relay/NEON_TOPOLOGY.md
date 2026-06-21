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
| **`patient-resonance-78640326`** | `ilyrium` | `ep-gentle-fire-ap8c0f9o` | **`neondb` only** (dead Campaign/Scene/Prisma scaffold; no real data) | **ORPHAN — delete candidate** |

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

## Orphan = `patient-resonance-78640326` (display name `ilyrium`) / `neondb`
- Endpoint `ep-gentle-fire` (the "struck" endpoint from earlier). Contains only `neondb` with
  the dead Campaign/Scene/`_prisma_migrations` scaffold — no real data, referenced by nothing
  in the repo. **Delete (or suspend) strictly by project ID `patient-resonance-78640326`.**
  Never delete by the display name `ilyrium` — that risks confusion with the real DB.

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
