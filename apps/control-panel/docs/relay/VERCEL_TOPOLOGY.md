# Vercel topology — Ilyrium (load-bearing reference, verified 2026-06-21)

> **Read this INSTEAD of re-deriving.** Companion to `NEON_TOPOLOGY.md` (the Neon map).
> **Headline:** the live Vercel production site is a **separate, early sample-data scaffold
> repo** — it is **NOT** the Phase-1 reconciled Relay app in `ilyrium-autostudio`. Do not
> assume "fix the Vercel env var → the reconciled app is wired." It isn't deployed there.

## 30-second re-verification (run these, don't trust prose)
```bash
# which repo does the Vercel prod project build? (answer: ilyrium-worldwide-productions, NOT ilyrium-autostudio)
vercel --cwd "$(mktemp -d)" link --yes --project ilyrium-worldwide-productions --scope project-next1
#   → then `vercel env ls production` and `vercel project ls`
gh api repos/bHBeachsider/ilyrium-worldwide-productions/git/trees/main?recursive=1 --jq '.tree[].path' | grep -iE 'db\.ts|prisma|studio-writes|release-gate'
#   → only apps/control-panel/lib/db.ts (campaign-era neon() driver); NO prisma / studio-writes / release-gate
curl -s https://ilyrium-worldwide-productions.vercel.app/settings | grep -oE '[0-9]+ tables provisioned'
#   → "20 tables provisioned" = app reaches ilyrium (19 base + _prisma_migrations)
```

## Two different repos — do not conflate (key by repo id, not name)
| GitHub repo | repo id | what it is | Vercel? |
|---|---|---|---|
| **`bHBeachsider/ilyrium-worldwide-productions`** | `1252408119` | **early sample-data UI scaffold** (campaign-era `lib/db.ts` + `@neondatabase/serverless` `neon()`; pages render HARDCODED data — "Kathy 01–03 / NH-01–02"; only `/settings` touches the DB via `dbHealth()`). **No Prisma, no `ilyrium.prisma`, no `studio-writes.ts`, no `release-gate`, no `decide()`.** | **YES — this is what production serves** |
| **`bHBeachsider/ilyrium-autostudio`** | (this monorepo) | the **reconciled Phase-1 + Relay app** (Next 14.2.3 + Prisma 7.8 → `ilyrium.prisma`, `lib/studio-writes.ts`, `release-gate`, `lib/relay/decide.ts`). `lib/db.ts` is **deleted** here. | **NO — never deployed to Vercel** |

→ **The reconciled Relay app has never been deployed.** "Phase 1 promoted to production" referred to the **Neon DB migration** (`assets.rating` on the `ilyrium` prod branch), **not** the Vercel app.

## Canonical Vercel project (key by ID)
| thing | value (STABLE) |
|---|---|
| Team | `project-next1` = **`team_D83ME2otD4yTngsa4CziJYYI`** (SAML) |
| Project | `ilyrium-worldwide-productions` = **`prj_6N4pjTL58npofXIOM8Yq9P5z1VIb`** |
| Production alias | `https://ilyrium-worldwide-productions.vercel.app` |
| Git source | repo `ilyrium-worldwide-productions`, branch `main` |

## `DATABASE_URL` — history & current state (resolved 2026-06-21)
- **Before:** an **EMPTY** (`""`) **Encrypted** Production var, created ~2026-05-28 (~24d). It pointed at **nothing** — *not* `patient-resonance`/`ep-gentle-fire`. (This is why the deploy commits all "guard against missing DATABASE_URL"; the scaffold serves hardcoded data and only `dbHealth` reads the DB.)
  - ⇒ **Pre-suspend guard SATISFIED:** the live app did not depend on the `patient-resonance` orphan, so suspending it (a separate, later task) is safe from the app's side.
- **Now:** set to the **verified pooled `ilyrium`** string, posture upgraded to **Sensitive** (write-only), and the prod deployment **redeployed** → `/settings` reports **Connected / healthy / 20 tables**.
- **Target string** (pooled = Vercel/serverless runtime; host re-derived from the STABLE prod branch id `br-odd-surf-ap2vfh9b`, never trusted from an `ep-…` id):
  ```
  postgresql://<neondb_owner>:<pw>@ep-young-voice-apndapaf-pooler.c-7.us-east-1.aws.neon.tech/ilyrium?sslmode=require
  ```
  Pooled `-pooler` host, `/ilyrium`, `sslmode=require`, **drop `channel_binding`** (it caused P1000 for Prisma — see `NEON_TOPOLOGY.md`). The **direct** host (for the later Graphile Worker / LISTEN-NOTIFY) is the same **without** `-pooler`.
- **How it was set:** via the **authed Vercel CLI** (`bhbeachsider` / `project-next1`) — value sourced `neonctl`→pipe, **never printed**, pull-verified as Encrypted before promoting to Sensitive. (One-off authorized deviation from "Brad sets it in the dashboard"; the CLI is the connectable path — there is **no env-var tool** in the Vercel MCP.)

## Named anti-patterns (each = a wrong conclusion avoided this session)
- **"The Vercel app is the reconciled app."** NO — it's a different repo (`…-productions`), a sample-data scaffold. Setting its `DATABASE_URL` does not deploy Relay.
- **"A stale `DATABASE_URL` is breaking production right now."** NO — pages are hardcoded; the var was empty and only `dbHealth` cared. Not time-sensitive.
- **"Sensitive vars are unreadable, so I can't see the old value."** The old var was **Encrypted** (readable via `vercel env pull`), not Sensitive — so it *was* readable. (It's Sensitive now, by intent.)
- **`vercel env ls` labels the value column `Encrypted` for Sensitive vars too** — confirm write-only posture by a `pull` returning empty, not by the label.
- **`vercel env add --force` keeps the existing var's type.** To change Encrypted→Sensitive you must `rm` then `add --sensitive`.

## Open task (NOT done — surfaced for a future session)
**Deploy the reconciled Relay app to Vercel.** The `decide()` gate + the distribution/paywall
slices need a real deployment home, and today's Vercel project builds the *old* scaffold repo.
Either re-point `prj_6N4pjTL58npofXIOM8Yq9P5z1VIb` at `ilyrium-autostudio` (root dir
`apps/control-panel`, Prisma generate, env) **or** stand up a new project. This is a separate,
brainstorm-gated task — it is not "flip an env var."

## Secrets
No passwords here by design — team/project/branch ids + endpoint hosts are safe to commit. Pull
the real connection string from the Neon console / `neonctl` at point of use; never paste a
credential here or into git.
