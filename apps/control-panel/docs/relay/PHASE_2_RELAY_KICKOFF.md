# Phase 2 — Relay: kickoff brief (for a fresh session)

> Phase 1 is COMPLETE on the branch AND production (see `RUNBOOK_phase1.md`). Phase 2
> (Relay) is **greenfield — no spec exists yet.** It was deferred to a fresh session for a
> clean context budget. Open the next session with the **brainstorming skill**, anchored on
> the items below; do NOT write Relay code before a design is approved.

## What Relay is (and the decomposition)
"Relay" = the `decide()` layer that routes distribution and gates a paywall on
`assets.rating`. It is likely **2–3 independent subsystems** — decompose and design the
first piece (`decide()`) first, each with its own spec → plan → implementation:
1. **`decide()` gate** — given a release-approved asset + its `rating`, return a distribution
   decision (eligible targets + paywall tier). Pure, testable, fail-closed. **Build first.**
2. **Distribution routing** — actually publish/route to targets; the real `releases` table
   already exists (`project_id, master_asset_id, platform, version_variant, hook_variant,
   scheduled_at, published_at, status`).
3. **Paywall / monetization** — `rating` → access tier + billing mechanics.

## Confirmed attachment point (from Phase 1 — do not re-derive)
- `POST /api/studio/release-gate` returns `{ allowed, blockers[], asset: {id, uri, assetType,
  rating}, rights }`. `decide()` runs on an asset only when `allowed === true` (fail-closed).
- `assets.rating` is live (`clean`/`mature`/`uncensored`, `text NOT NULL DEFAULT 'clean'` +
  CHECK) on the branch `studio_os_branch1` AND production (`ilyrium` @ `ep-young-voice`).
- Real governance model is risk-based: `rights_records` (approvedForRelease, releaseStatus,
  *_risk, riskLevel, synthetic/SAG-AFTRA) + `gate_approvals` + `releases`.
- Shared writers/helpers in `lib/studio-writes.ts`; gate logic in `lib/release-gate.ts`.

## Open questions to resolve in the brainstorm (first ones)
1. **Distribution targets** — which platforms/surfaces does Relay route to (YouTube/TikTok/X?
   a hosted Ilyrium gallery? the `releases.platform` field)?
2. **Paywall gating** — does access gate on `rating` alone (e.g. clean=free, mature/
   uncensored=paid), or `rating` × something else (platform policy, region, age)?
3. **Billing mechanics** — Stripe? tiers? Is monetization in Phase 2 scope or a later phase?
4. **`decide()` output shape** — what does it return (eligible targets + tier + reasons),
   and how does it compose with `release-gate` (gate first, then decide)?

## Environment notes (carry forward)
- Repo: `ilyrium-autostudio/apps/control-panel`. Next 14.2.3 + Prisma 7.8 (canonical
  `prisma/ilyrium.prisma`).
- Shell traps: always `unset DATABASE_URL` (stale PermitHub `ep-plain-haze` var) and
  `unset NODE_ENV` (leaked `development` crashes `next build`) before CLI/build.
- Gate Neon connections on **branch identity + console status**, not `ep-…` endpoint strings
  (those drift). Production = `br-spring-rain-ap81nd7m` (primary compute currently
  `ep-young-voice-apndapaf`). `.env` stays on the branch; never write to production without
  an explicit gate.
