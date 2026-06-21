# Relay `decide()` — Slice 1 design (APPROVED + CONFIRMED; DESIGN ONLY)

> **Status:** approved, fully confirmed slice-1 design (mapping values signed off by Brad
> 2026-06-21). **No implementation in this slice** — no TypeScript, no tests. Implementation is
> a SEPARATE, later slice gated on this doc.

## Scope
`decide()` is Relay's single governed gate, as a **pure, deterministic function**. It runs
**only when `POST /api/studio/release-gate` returned `allowed === true`** — so it does NOT
decide allow/deny (that's upstream). For an already-release-approved asset it decides **HOW it
may be distributed** (`targets`) and **monetized** (`tier`). Actually publishing (writing the
`releases` table, the Graphile Worker) and the paywall (`tier → entitlement → Stripe`) are
LATER slices that **consume** this contract — out of scope here.

## 1. Contract (settled)
```ts
// Pure, total-except-on-contract-violation. No DB, no network, no clock, no randomness.
decide(input: DecideInput, policy: Policy): Decision

type Rating = 'clean' | 'mature' | 'uncensored'

DecideInput = {
  assetId: string     // echo-only; NOT a logic input
  rating: Rating      // the SOLE logic input
  allowed: boolean    // re-asserted (defense in depth)
}

Policy = {            // passed IN (not fetched) — keeps decide() pure + exhaustively testable
  version: string                                  // e.g. 'relay-policy-v1'
  rules: Record<Rating, { targets: Target[]; tier: Tier }>
}

Decision = {
  assetId: string        // echoed from input (traceability)
  rating: Rating         // echoed — records what drove the decision
  targets: Target[]      // eligible distribution targets (identifiers only; [] = unpublishable)
  tier: Tier             // paywall tier
  reasons: string[]      // rationale (governance / audit trail)
  policyVersion: string  // which policy produced this (reproducibility / audit)
}
```
- **Branches solely on `rating`.** `assetId` is echoed into `Decision` for traceability and is
  **not** a logic input — the decision must not depend on it (keeps purity honest and keeps it
  out of the test-matrix input axis).
- **`allowed === false` → THROW** `DecideContractError`. `decide()` is only called when
  release-gate returned `allowed === true`, so `false` is a **caller bug**, not a business
  state — fail loud rather than silently return an empty decision that mimics a legitimate
  "nothing eligible" result.
- **Policy is an argument**, not a fetch — so `decide()` stays pure. `policyVersion` is stamped
  into every `Decision` so a stored decision can be explained / replayed after a policy change.

## 2. Fail-closed semantics (settled — rating-only)
`decide()` branches solely on `rating`, so the **sole** fail-closed trigger is an
**unrecognized `rating`** (any value not `clean`/`mature`/`uncensored`) → the **most-restrictive**
decision: **no targets, `gated` tier**, `reasons: ['unrecognized rating → fail-closed (deny)']`.
- There are **no** rights/ambiguous-state clauses — `decide()` doesn't take those inputs, so such
  rules would be dead. (`allowed === false` is a thrown contract error, not a fail-closed return.)
- This branch is a **runtime safety net, not an expected path**: the `Rating` type prevents a
  valid caller from reaching it. The implementation slice's test matrix must cover it explicitly
  by forcing an invalid `rating`.

## 3. Mapping table (CONFIRMED 2026-06-21 — values signed off; structure + values settled)
Table-driven: changing this is a **data edit**, not a logic change.

| `rating` | `targets` | `tier` |
|---|---|---|
| `clean` | `public_web`, `discord`, `republic_archive` | `public` |
| `mature` | `discord`, `republic_archive` | `gated` |
| `uncensored` | `republic_archive` | `gated` |
| (unrecognized) | — (none) | `gated` |

- **Tiers (2):** `public` (free/open) and `gated` (membership/entitlement required). `premium`
  remains an easy future extension if a third tier is ever wanted.
- **`Target` ids** (`public_web` / `discord` / `republic_archive`) are **CONFIRMED** identifiers
  (Republic Archive = membership). Concrete pushing to them is the distribution slice's job.
- ✅ **`uncensored` is intentionally MORE restricted than `mature`** — members-only
  `republic_archive` vs. `discord` + members (confirmed by Brad).

## 4. Implementation structure (design note — NOT code)
`decide()` = assert `allowed` (throw `DecideContractError` if false) → look up `rating` in
`policy.rules` → return the mapped `Decision` (echo `assetId`/`rating`, stamp `policyVersion`,
populate `reasons`) → if `rating` unrecognized, return the fail-closed `Decision`. Deterministic,
table-driven, no I/O. (Intended shape only — the function is not written in this slice.)

## 5. Test-matrix outline (for the later implementation slice — outline only)
- Each valid `rating` (`clean`/`mature`/`uncensored`) → exact expected `{ targets, tier }`.
- Unrecognized `rating` (forced invalid) → fail-closed (no targets, `gated`).
- `allowed === false` → throws `DecideContractError`.
- Determinism: same input → identical `Decision`.
- `policyVersion` stamped on every returned `Decision`.

## Out of scope (later slices that consume this contract)
- **Distribution:** resolve `targets` → actually publish/schedule into the real `releases`
  table via the **Graphile Worker** (needs the **direct, non-pooler** Neon host — LISTEN/NOTIFY
  can't traverse the pooler). See `NEON_TOPOLOGY.md`.
- **Paywall:** `tier → entitlement → Stripe` (products/prices, checkout, webhooks, access).
- **The gate to writing code is this doc's approval.** Implementation is a separate slice.
