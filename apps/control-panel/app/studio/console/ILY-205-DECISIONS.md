# ILY-205 Phase 0 — Open Decisions

Recorded 2026-10-26 before Phase 0 feature branch `feat/ily-205-console-p0` was cut.

## Decision A — Take-delete semantics

**Verdict: remove the delete button (done in commit 7bddee2 on main).**

The pipeline invariant is clear: takes are append-only; `regenerate_shot` adds a take,
it never overwrites one. `select_take` is the reversible act. A delete path would:
- Punch a hole in `ledger/<song-id>.jsonl` (breaks `chain_ok`)
- Let the UI diverge from the on-disk take directory with no reconciliation path

The `🗑` button in `AssetGenPanel` (Pipeline.tsx) has been replaced with a plain
select-only chip. If a take needs to be suppressed from the picker in future, the
right mechanism is a `hidden: true` flag on the take record — never a hard delete.

## Decision B — Playwright / axe smoke test data source

**Verdict: fixtures (not Neon branch).**

Rationale:
- A Neon branch adds an external dependency to every CI run; a network hiccup or
  billing pause kills the suite silently.
- The console UI tests are assertions about rendered HTML — they do not need live
  data. Static JSON fixtures stored under `apps/control-panel/tests/fixtures/` are
  sufficient and deterministic.
- If integration tests against a real DB are ever needed, a separate `e2e:neon`
  script can be added; it stays off the standard `ci:test` path.

Fixture location: `apps/control-panel/tests/fixtures/`
Fixture format: JSON files mirroring pipeline-service API responses (`/pipeline`,
`/pipeline/:id`, `/stage/:project/:n/checklist`).
