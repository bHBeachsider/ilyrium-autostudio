# Archived reference artifacts (Phase 1 reconciliation, Step 3)

These files are **archived, not active**. They are kept for reference only and are not
wired into the app, the Prisma config, or any migration history.

## `studio.prisma.idealized`
Formerly `prisma/studio.prisma`. The never-deployed idealized studio asset graph
(every model `@@schema("studio")`, zero `@@map`, 9 pg enums, plus models with **no**
backing table: `Sequence`, `Take`, `AudioElement`, `Cut`, `ProvenanceRecord`,
`ArchivePackage`). Superseded by the canonical schema introspected from the real
`public` tables (`prisma/ilyrium.prisma`, created in Step 4). Preserved because it
documents the richer provenance/archive/rights design intended for a deferred phase.

## `20260531182246_init/`
Formerly `prisma/migrations/20260531182246_init/`. The Campaign/Scene track's init
migration. **Never applied** to the `ilyrium` database — its tables targeted a
different Neon project (`patient-resonance`/`neondb`). Archived out of the active
`prisma/migrations/` path so it does not pollute the canonical migration history
(the `0_init` baseline-adopt + `add_asset_rating` created in Steps 5/7).

## Retired Campaign track (deleted, recoverable from the baseline commit)
`app/api/campaigns`, `app/api/webhooks/video-render`, `lib/agents/assembly.ts`,
`lib/agents/production-dispatcher.ts`, `lib/db.ts` (the Campaign Prisma client),
`prisma/schema.prisma`. Rationale (Fork D): zero live callers, ffmpeg pipeline
commented out, imports of nonexistent `@/lib/media/*`, and the real reference app
(`Ilyrium/apps/control-panel`) has no Campaign concept. Also deleted:
`lib/agents/script-doctor.ts` (dead — no importers; broken `../db` stub imports).
