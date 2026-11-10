# Console UI/UX lane - inventory (2026-11-09)

Written by the new console lane from the worktree
`.claude/worktrees/console-uiux-inventory-16d579` (branch
`claude/console-uiux-inventory-16d579`, cut from `feat/ily-205-console-p0` at `7c5e17e`).
Inventory only: no feature code, nothing committed, no PR. The main checkout at
`C:\Users\bradu\Documents\ilyrium-autostudio` was read with `git -C ... status|diff|log`
and file reads only. Paths starting `PermitHub-API/` are under `C:\Users\bradu\Documents\`.

## Headlines

1. **The console UI/UX work is ILY-205, and its record lives in PermitHub-API, not here.**
   There is no later "enhancement" spec or task list anywhere I searched.
2. **ILY-205 is merged to `origin/main`** as squash PR #26 (`f352d94`, 2026-10-28). The
   briefing's "8 commits ahead of main, not merged" comes from a stale local `main`.
3. **"All 30 tasks merged" is not true.** About 14 of 30 tasks are built as specified,
   about 5 are partial, about 11 are not built. Phase 0 (hygiene, a11y, design system)
   and Phase 1 (the Shots grid) are essentially missing.
4. **The console does not build in a clean checkout**, and its Playwright tests fail there.
5. **The uncommitted edits in the main checkout are four months old** (July 2026), predate
   ILY-205, and are load-bearing: committed console UI calls endpoints that exist only in
   those uncommitted files.
6. **New scope direction from Brad (2026-11-09, in this session):** "create a console that
   clones the features of DaVinci Resolve". Recorded in section 6; not acted on yet.

---

## 1. The UIUX lane's own record

### Found: ILY-205 (all in PermitHub-API)

| What | Path |
|---|---|
| The plan (research, audit triage, stack table, keyboard map, Phase 0 `/goal` prompt, 4 open decisions) | `PermitHub-API/Claude outputs/PLAN-ilyrium-studio-console-uiux-2026-10-26.md` |
| Companion brief (metrics-registry correction, Phase 0 dependency) | `PermitHub-API/Claude outputs/BRIEF-dashboard-method-control-panels-2026-10-26.md` |
| The spec, 30 numbered tasks in 6 phases | `PermitHub-API/docs/roadmap/inbox/processed/ilyrium-studio-console-uiux-upgrade.md` (tracked; filed in PermitHub PR #1526). An identical untracked copy sits at `docs/roadmap/inbox/ilyrium-studio-console-uiux-upgrade.md` |
| Project definition, 30 tasks, `status: Not Started`, target 2026-11-30 | `PermitHub-API/docs/roadmap/projects/studio-console-ui-ux-upgrade.yaml` |
| Registry entry, `status: active`, created 2026-10-26 | `PermitHub-API/docs/roadmap/registry/ILY-205.yaml` |
| Scope file (allowed paths are relative to `apps/control-panel`) | `PermitHub-API/docs/roadmap/projects/ILY-205.scope.yaml` |
| The static audit the plan is built on (75/100; a11y 48, design system 50) | `C:\Users\bradu\Downloads\UIUX-Studio\reports\control-panel-20261026-1307\` (folder exists; I did not open the report) |

The tool that produced the audit is "UIUX-Studio" (`C:\Users\bradu\Downloads\UIUX-Studio`,
also installed as the `uiux-studio` skill). That is probably where the lane name comes from.

### Found in this repo

- `apps/control-panel/app/studio/console/ILY-205-DECISIONS.md` (tracked): Phase 0
  decisions A (remove take-delete) and B (fixtures, not a Neon branch).
- `docs/plans/2026-10-29-console-phase2-e2e.md` (**untracked, main checkout only**, dated
  2026-10-29): workstream A is FilmCraft Phase 2; **workstream B is console work**: four
  Playwright spec files for console phases 1-4 (`phase1-review`, `phase2-timeline`,
  `phase3-queue`, `phase4-chat`, 16 test IDs). B has not been done anywhere (section 4).
  Its phase numbering does not match ILY-205's (its "Phase 2" is the timeline, ILY-205's
  is the Review Room).
- Older console design docs, all **untracked, main checkout only**:
  `docs/STAGE_CONSOLE_BLUEPRINT.md` (2026-06-03; the 8 stages as Resolve-style pages -
  the ILY-205 plan cites it), `docs/PRODUCTION_CONSOLE_ROADMAP.md` (2026-05-31),
  `docs/STUDIO_OS_STAGE_WORKSPACES.md` (2026-06-02).
- Tracked July plans that the uncommitted edits implement:
  `docs/plans/2026-07-12-production-console.md`,
  `docs/plans/2026-07-12-console-model-selector-and-repl.md`,
  `docs/plans/2026-07-12-multifile-upload.md`.

### Not found

- **No spec, task list, handoff or prompt for console work beyond ILY-205's 30 tasks.**
- The PermitHub "UIUX" lane files are **CoreBuild**, not Ilyrium:
  `Claude outputs/uiux/UIUX-REPORT-1..5.md`, `Claude outputs/LANE-RESPONSE-uiux-1..11.md`
  (last active 2026-10-02), and today's
  `Claude outputs/ORCHESTRATOR-UIUX-PROMPT-2026-11-10.md`, whose remit is UI-004 and
  UI-005 only. It does not mention the Ilyrium console.
- Nothing console-related in `PermitHub-API/docs/handoff/` or `docs/specs/` by filename.
- The `ilyrium-autostudio-filmcraft-env` worktree holds no lane record (section 4).

---

## 2. ILY-205's true state

### Where the commits are

| Ref | Tip | Contains ILY-205? |
|---|---|---|
| `origin/main` | `73ab46e` (PR #30, 2026-11-07; confirmed with `git ls-remote`) | **Yes**, as squash `f352d94` "ILY-205 Studio Console UI/UX Upgrade (phases 0-5) (#26)", merged 2026-10-28. `git diff 5db00c9 f352d94` is empty: the squash tree equals the Phase 5 commit. |
| local `main` | `7bddee2` | No. It is stale: 12 behind `origin/main`. Its "87 ahead" are the pre-squash originals of what #26 landed. |
| local `feat/ily-205-console-p0` (main checkout, and this worktree's base) | `7c5e17e` | Yes, as the 7 original commits `18cacac`..`5db00c9`, plus `7c5e17e` (merged separately as PR #27). The remote branch is deleted. **This branch is a merged leftover.** |

Also on `origin/main` and **not** in this worktree: PR #24 (fal.ai MediaAdapter), #23
(multi-track audio mixing), #25 (append-only Take/Cut/AudioElement data layer), #28
(ledger chain fix), #30 (packs). Under `apps/control-panel` that is 19 files, +1621/-102,
including `lib/ledger.ts`, `lib/adapters/falAdapter.ts`, `prisma/takes.prisma`,
`app/api/studio/takes/route.ts`, the removal of the 98 dead lines noted below, and a
+175-line change to `TimelinePanel.tsx`.

### What the commits contain, against the 30 tasks

Checked by reading the commits and grepping the tree at `7c5e17e`. "Partial" means the
feature exists but not with the specified library or acceptance check.

| Phase | Tasks | State | Evidence |
|---|---|---|---|
| 0 Hygiene and harness | 1 pin next/react | **Not done** | `package.json` still has `"next": "latest"`, `react`, `react-dom`, `elevenlabs` all `latest` |
| | 2 shadcn/Radix | **Not done** | no `components.json`, no `@radix-ui` import |
| | 3 seven audit findings | **Mostly not done** | take-delete button removed (`7bddee2`); but no `loading.tsx`/`error.tsx`, `.state-pulse` has no reduced-motion guard (`app/globals.css:31`), 74 inline hex colours remain in console files |
| | 4 type-scale tokens | **Not done** | 344 `text-[Npx]` literals in `app/studio/console/*.tsx` (was 254 in the audit; it grew) |
| | 5 metrics to `lib/metrics` | **Not done** | `costPerRenderSec` still inline at `app/studio/console/page.tsx:56`; `lib/metrics/` holds only `costMeter.ts` |
| | 6 Playwright + axe smoke | **Partial** | Playwright yes; `@axe-core/playwright` not installed |
| | 7 re-audit >= 85 | **Not done / no record** | no audit re-run found |
| 1 Shots home | 8-12 | **Not built** | commit `6d2c75b` titled "Phase 1" only deletes two dead files and a footer (+1/-376). No TanStack, no grid, no saved views, no inspector, no ledger-reconcile test, no screenshot baselines |
| 2 Review room | 13 player | Partial | `ReviewRoom.tsx` uses `requestVideoFrameCallback`; no Media Chrome |
| | 14 A/B compare, 15 playlist, 16 hotkeys, 17 append-only reject, 18 replace approve flow | Built | `ReviewRoom.tsx`, `app/api/studio/review/route.ts` |
| | 19 verify | Partial | `tests/nh-s901-review-keyboard.spec.ts` exists; see section 5 for its state |
| 3 Timeline | 20-21 | Built | `TimelinePanel.tsx`, `wavesurfer.js` |
| | 22 verify NH-S901 in sync | No record | no test |
| 4 Queue / cost / palette | 23 queue rail, 25 cost meter | Built | `QueueRail.tsx`, `CostMeter.tsx`, `lib/metrics/costMeter.ts` + test |
| | 24 box on/off intervals, billed hours | **Not built** | nothing records intervals; `BoxPanel.tsx` only polls status |
| | 26 Ctrl+K palette + cheat sheet | Partial | hand-rolled `CommandPalette.tsx`, not cmdk |
| | 27 verify estimate vs spend | Partial | unit test only |
| 5 Rights / deliver | 28 C2PA chips, 29 blocked badge + gate, 30 Playwright | Built | `RightsPanel.tsx`, `tests/phase5-rights.spec.ts` |

### Honest status line

> ILY-205: merged to `origin/main` in PR #26 (2026-10-28). Phases 2-5 (Review Room,
> timeline, queue/cost/palette, rights) are built in a first form without the specified
> component libraries. Phase 0 (dependency pins, shadcn, accessibility fixes, type scale,
> metrics extraction, axe) and Phase 1 (Shots status grid) are not built. Roughly 14 of 30
> tasks done, 5 partial, 11 open. No re-audit has been run; the last recorded score is
> 75/100.

The PermitHub records disagree with each other and with this: `registry/ILY-205.yaml`
says `active`, `projects/studio-console-ui-ux-upgrade.yaml` says `Not Started`,
`docs/plans/2026-10-29-console-phase2-e2e.md` says "all 30 tasks merged".

### ILY-203

`[INTEL] Auto-Studio RSI L0 Blueprint B`: the execution harness (`harness/run.py`,
`harness/admission_gate.py`, the PR template, per-project findings registries). 22
references in this repo. It is pipeline infrastructure, not console work. PermitHub
**retired it on 2026-11-05** (`PermitHub-API/docs/roadmap/registry/ILY-203.yaml`:
"Targets the separate ilyrium-autostudio repo, not PermitHub or CoreBuild; 0/19 tasks,
idle since June") although much of it is visibly built here. That triage reasoning applies
equally to ILY-205, which matters for where the new lane's ID should live (section 5).

---

## 3. Uncommitted edits in the main checkout

Branch `feat/ily-205-console-p0`. File dates are from the filesystem.

### `apps/control-panel` - modified (4)

| File | Dated | What it does | Finished? | Kind |
|---|---|---|---|---|
| `app/api/llm/chat/route.ts` (+104) | 2026-07-14 | Gives the local model a `generate_image` tool, parses the tool call out of the reply text, calls the pipeline service `POST /studio/render`, returns the image inline | Looks finished; no tests | Console feature (chat image render) |
| `lib/llm/providers/localQwen.ts` (+40) | 2026-07-14 | Default model changed from `qwen3-coder:latest` to `huihui_ai/qwen2.5-coder-abliterate:7b`; adds an identity system prompt; passes `tools` through; serialises native tool calls | Finished. The model default is an operational choice that may be stale (memory says the box setup has changed since) | Console feature + config |
| `lib/llm/types.ts` (+2) | 2026-07-14 | Adds `tools?: any[]` to `ChatOpts` | Finished | Supports the two above |
| `next-env.d.ts` | 2026-10-26 | Rewritten by `next dev` | Generated noise | Do not commit as work |

These three July files are the server half of a feature whose client half **is
committed**: `ChatPanel.tsx` (commit `7bddee2`) already reads `d.image?.url` from the chat
route. On `origin/main` the chat can never return an image.

### `apps/control-panel` - untracked (3)

- `AGENTS.md` (2026-11-02): auto-written by `next dev` (Next.js agent rules block). The
  file says to commit it or it keeps reappearing. Harmless.
- `playwright-report/`, `test-results/` (2026-10-26 22:03): output of a Playwright run in
  which **both `nh-s901-review-keyboard` tests failed** (`test-results/.last-run.json`).
  That run predates the fix commit `81f12ad` (22:26 the same night); there is no later
  result on disk. Neither folder is in `.gitignore`.

### `apps/auto-studio` - modified (5)

| File | Dated | What it does | Finished? | Kind |
|---|---|---|---|---|
| `studio_pipeline_service.py` (+164) | 2026-07-14 | (a) brief attachments: `files[]` of any kind saved with a collision guard, `brief_files` in run state; (b) `stage_media` same-second collision guard, plus new `GET .../media/file` and `POST .../media/delete` (traversal-guarded); (c) new `POST /studio/render` and `GET /studio/render/file` for chat image renders; (d) **`shot_action` op `delete`** calling `ps.remove_take` | (a)-(c) look finished, no tests. **(d) must not be committed**: it deletes takes, which breaks the append-only invariant and contradicts ILY-205 Decision A | Pipeline service, in support of console features. Note this file also **differs on `origin/main`** (PR #23 touched it), so it needs a real merge |
| `stage_scaffold.py` (+82/-…) | 2026-07-13 | Adds `media_files()` and a `files` list per checklist element (attachments count as done); adds `JSON_KERNEL_FIELDS` | **Not safe as-is.** It also *removes* `project_paths.resolve_project` / `list_projects` (the client-aware `projects/<client>/<project>` resolution from commit `790128c`) in favour of a hard-coded `projects/<name>`, and strips comments. Looks like a rewrite from an older base | Pipeline; needs hand-merging, keep only the media additions |
| `pipeline_exec.py` (+22) | 2026-07-14 | Render model from `project['render_model']` (default `comfyui`) instead of hard-coded `grok-imagine`; an attached song (`brief_files` kind audio) becomes the master music track | Finished; depends on (a) above | Pipeline behaviour change - film lane should review |
| `studio_mcp.py` (+9) | 2026-08-03 | Forces UTF-8 on stdout/stderr so emoji log lines do not crash on Windows cp1252 | Finished | Pipeline bug fix (see `_emoji_scan.txt`, `studio_mcp.py.bak_utf8fix`) |
| `model_registry.json` (+349) | 2026-08-15 | Adds 7 Higgsfield and 4 Seedance-via-fal model entries; re-escapes em-dashes | Finished | Pipeline / film (model catalogue), not console |

Committed console UI that depends on the uncommitted service code:
`StageChecklist.tsx:63` and `:114` call `/media/delete` and `/media/file`;
`StageChecklist.tsx:109` reads `el.files`; `Pipeline.tsx:112` sends `files[]`.

### `apps/auto-studio` - untracked (97 entries at top level, 123 files)

Not inspected file by file. Grouped by name and date:

| Group | Files | Kind |
|---|---|---|
| **Load-bearing pipeline modules never committed**, also absent from `origin/main` | `project_store.py` (2026-07-13), `conformance.py`, `release_gate.py`, `c2pa_sign.py`, `publish.py`, `style_kernel.py`, `style_validator.py`, `studio_pipeline.py`, `otio_export.py`, `model_select.py`, `prompt_kit.py`, `tracing.py`, `evals.py`, `throughput.py`, `tool_knowledge.py`, `error_handling.py`, `bible_checklist.json`, `stage_checklists.json`, `prompt_taxonomy.json`, `requirements.txt`, `prompt_templates/` (12), `media/*.py` (8 renderers), `core/`, `graph/`, `agents/`, `schemas/`, `memory/`, `utils/` | Pipeline. **Tracked code imports these** (`pipeline_exec.py` imports `project_store`; `stage_scaffold.py` opens `bible_checklist.json`; CLAUDE.md names `conformance.py` as a gate). The pipeline service the console talks to can only run from the main checkout |
| ComfyUI workflows | `comfyui_workflows/` (10, July) | Pipeline / box |
| Reference harvesting | `museum_refs.py`, `museums.yaml`, `met_refs.py`, `scrape_refs.py`, `organize_refs.py`, `region_tag.py`, `registry_harvest.py`, `harvester_mcp/` | Pipeline tooling |
| Project-specific and one-off scripts | `kingsize_*.py` (4), `render_*.py`, `run_img2img.*`, `simple_img2img.py`, `image_to_image.py`, `image_workflow_helper.py`, `z_imager*`, `zimage_prompt.txt`, `migrate_kernels.py`, `debug_panel.py`, `ci_check.py` | Film / scratch |
| Tests | `tests/test_fal_seedance.py`, `tests/test_higgsfield_renderer.py`, `test_astria.py`, `test_conformance.py`, `test_tensorart.py` | Pipeline tests |
| Kernels | `kernels/new_harnomy.json` (2026-08-15) + `.bak` | **Film lane - not ours** |
| Junk | 5 `*TEMP_MPY_wvf_snd.mp4`, `_test/`, `_emoji_scan.txt`, 6 `*.bak*`, `media/jersey_dreamboats.png`, `media/taco dive/`, `ComfyUI/` | Delete or ignore (Brad's call) |

Nothing in the untracked `apps/auto-studio` set is console UI/UX work.

### Summary of ownership

None of these edits were made by an ILY-205 session: every code file is dated July to
mid-August, ILY-205 started 2026-10-26. They are leftovers from the July console/pipeline
sessions (plans `docs/plans/2026-07-12-*.md`) and August film sessions.

---

## 4. Other worktrees

All are clean (no uncommitted changes). None holds unmerged console work.

| Worktree | Branch | State | Console relevance |
|---|---|---|---|
| main checkout | `feat/ily-205-console-p0` | merged leftover branch + the uncommitted edits of section 3; film lane active here | ILY-205 originals |
| `...-filmcraft-env` | `chore/ily-205-filmcraft-env-example` | merged as PR #27; clean | none - adds `.env.example` only; the "ily-205" in the name is incidental |
| `.claude/worktrees/great-agnesi-c10109` | `claude/great-agnesi-c10109` | merged as PR #24 | fal.ai MediaAdapter in `apps/control-panel/lib`; done |
| `.claude/worktrees/vibrant-jang-2c370f` | `claude/vibrant-jang-2c370f` | merged as PR #25 | Take/Cut/AudioElement data layer; done |
| `.claude/worktrees/silly-lichterman-12d4d5` | `claude/silly-lichterman-12d4d5` | merged as PR #23 | multi-track audio mixing, labelled ILY-205; done |
| `.claude/worktrees/fal-ledger-chain` | `fix/fal-ledger-chain` | merged as PR #28 | `lib/ledger.ts` chain; done |
| `.claude/worktrees/feat-filmcraft-phase2-9be3dd` | `claude/feat-filmcraft-phase2-9be3dd` | **PR #29 open**; local is 1 commit ahead of its remote (`4a54777`, unpushed) | Workstream A of the 10-29 plan. No `apps/control-panel` changes; **workstream B (console E2E specs) not started** - `tests/` has only the two existing specs |
| `ilyrium-autostudio-worktrees/relocation-packs` | `claude/relocation-packs` | merged as PR #30 | none |
| `C:\Users\bradu\ily-relay-worker-wt` | `docs/relay-worker-drain-design` | June; 2 unmerged relay commits | none (relay, not console) |

Six of these are finished-PR leftovers that could be removed. Not mine to remove.

---

## 5. What the lane needs before real work

### Project ID

- Highest ILY number in use: **ILY-205**. Taken: 049, 197-205. **ILY-206 is free**
  (no file or reference under `PermitHub-API/docs/roadmap`).
- Caveat 1: IDs are allocated by PermitHub's filing tooling (`generate_project.py`), not
  by hand. ILY-204 and ILY-205 have `registry/*.yaml` files but are missing from
  `PROJECT_ID_REGISTRY.yaml`, whose last ILY entry is 203.
- Caveat 2: PermitHub retired ILY-203 on 2026-11-05 for targeting this repo. A new
  autostudio project filed there may be triaged out the same way, and this repo has no
  project registry of its own (only `ilyrium-shots/SONG_ID_REGISTRY.json`, which is for
  song IDs).
- Proposal: **continue under ILY-205** for its 16 open/partial tasks (the spec and scope
  file already exist and are accurate), and take **ILY-206** for the Resolve-style
  expansion in section 6. Brad decides whether 206 is filed in PermitHub or recorded here.

### Branch to build on

**`origin/main` (`73ab46e`)**, not `feat/ily-205-console-p0`. The current base is a
merged pre-squash branch that lacks five later PRs. Because #26 was a squash, a branch cut
from `feat/ily-205-console-p0` will show the whole ILY-205 history again in any PR and
conflict with `TimelinePanel.tsx` and `studio_pipeline_service.py`. This worktree should be
re-cut from `origin/main` before any feature commit.

### Bringing in the uncommitted edits

They are not in this worktree and this lane must not move them. Recommended split:

1. **Brad or the owning session, in the main checkout:** commit the load-bearing untracked
   pipeline modules (`project_store.py`, `conformance.py`, `release_gate.py`,
   `c2pa_sign.py`, the two checklist JSONs, `media/`, etc.) on a branch from `origin/main`.
   Until that lands, no clean checkout can run the pipeline service. Film-lane files
   (`kernels/new_harnomy.json`, `projects/`, `ilyrium-shots/`) stay out of it.
2. **Console lane, once (1) is on `main`:** a small PR for the chat-image-render and
   multi-file-attach service code: `route.ts`, `localQwen.ts`, `types.ts`, and from
   `studio_pipeline_service.py` hunks (a)-(c) only, re-applied onto the `origin/main`
   version. Drop the `op == "delete"` hunk. From `stage_scaffold.py` take only
   `media_files()` and the `files` field; keep `project_paths`. Brad confirms the default
   local model first.
3. **Film/pipeline lane:** `pipeline_exec.py`, `model_registry.json`, `studio_mcp.py`.
4. Add `playwright-report/`, `test-results/` to `apps/control-panel/.gitignore`; commit
   `AGENTS.md`; discard `next-env.d.ts`.

### Tests that exist

- Vitest (`pnpm test`, config includes `lib/**/*.test.ts` only):
  `lib/metrics/costMeter.test.ts`, `lib/relay/decide.test.ts`. On `origin/main` also
  `lib/ledger.test.ts`, `lib/adapters/falAdapter.test.ts`, `app/api/webhooks/fal/route.test.ts`.
- Playwright (`apps/control-panel/tests/`): `nh-s901-review-keyboard.spec.ts`,
  `phase5-rights.spec.ts`, fixtures `shots.json`, `ledger_nh-s901-test.jsonl`. Chromium
  only, starts `npm run dev` on port 3000 and reuses any server already there.
- No axe tests, no screenshot baselines, no component tests.

### Results in this worktree, as-is (2026-11-09)

| Check | Result |
|---|---|
| `npm ci` | **Would fail**: `package-lock.json` is stale (pins `next` 14.2.3, lacks `wavesurfer.js` and `@playwright/test`). `pnpm-lock.yaml` is the live lockfile; both are committed |
| `pnpm install --frozen-lockfile` | OK. Resolves `next` 16.4.3, `react` 19.3.1 |
| `vitest run` | **Pass**: 2 files, 27 tests |
| `tsc --noEmit` | **Fail**, 3 errors: missing generated Prisma client (a setup step), and `prisma.config.ts` imports `dotenv/config` and `@prisma/config`, neither declared in `package.json` |
| `next build` | **Fail**: `lib/studio-db.ts` cannot resolve `../prisma/generated/studio-client` |
| `next build` after `prisma generate --schema prisma/ilyrium.prisma` (codegen only, no DB) | **Still fails**: generated client cannot resolve `@prisma/client-runtime-utils` under pnpm's strict `node_modules`. Also warns that `experimental.serverComponentsExternalPackages` in `next.config.js` is an invalid key in Next 16 |
| Playwright `phase5-rights.spec.ts` | **4 of 4 fail**: the console page does not compile (same Prisma error), so the nav button never renders |
| Playwright `nh-s901-review-keyboard.spec.ts` | **Not run.** It creates and deletes `ilyrium-shots/ledger/nh-s901-test.jsonl`, and `ilyrium-shots/` is outside this lane's limits. Only recorded result: 2 of 2 failed on 2026-10-26, before fix `81f12ad` |

No `.env` exists in the worktree and `DATABASE_URL` was unset, so nothing contacted Neon.
Side effects of the test run (`AGENTS.md`, `next-env.d.ts`, `test-results/`) were removed;
`node_modules`, `.next` and `prisma/generated` remain and are git-ignored.

Two things the lane should know about the review spec and route:

- `app/api/studio/review/route.ts` appends approval records to the **real**
  `ilyrium-shots/ledger/<songId>.jsonl` by a path relative to the server's working
  directory. Its own comment says "local dev only". There is no guard on `songId`.
- The spec's test song ID `nh-s901-test` is not in `SONG_ID_REGISTRY.json`.

---

## 6. Scope direction received: a Resolve-style console

Brad, 2026-11-09, in this session: "create a console that clones the features of" DaVinci
Resolve, with a feature summary pasted (pages, Neural Engine tools, scripting/MCP).

This matches the direction already on file: `docs/STAGE_CONSOLE_BLUEPRINT.md` and the
ILY-205 plan both model the console as Resolve-style pages over shared panels, and
`ConsoleShell.tsx` is the layout seam for it. A first mapping of Resolve's pages onto this
studio, for Brad to correct:

| Resolve page | Console equivalent | Exists today |
|---|---|---|
| Media (ingest, bins, metadata) | Assets: refs, keyframes, takes, smart bins as saved views | attach/upload in `StageChecklist.tsx`; no browser or bins |
| Cut / Edit (timeline NLE) | Timeline: shots on tracks, trim, reorder, take swap | `TimelinePanel.tsx` (playback/animatic only, no editing) |
| Fusion (node compositing) | Generation graph: the ComfyUI workflow per shot, as nodes | none in the console |
| Color (grading) | Look: style kernel, LUT/grade per shot, scopes | none |
| Fairlight (audio) | Audio: VO, music bed, SFX tracks, ducking | waveform in `TimelinePanel.tsx`; multi-track mix exists server-side (PR #23) |
| Deliver (render/export) | Deliver: release QA, rights gate, master export | `RightsPanel.tsx`, `app/api/studio/release-gate/route.ts` |
| (none) | Review: version stacks, approve/reject | `ReviewRoom.tsx` |
| Neural Engine search / transcript edit / voice tools | IntelliSearch over takes, text-based edit from the script, voice cast | chat panel only |

Limits to state plainly: a browser console cannot reproduce Resolve's real-time 32-bit
grading engine, Fusion's 3D compositor or a 2,000-track DAW. What can be built is the
page structure, the editorial interactions (timeline editing, review, bins, node view of
generation, per-shot look controls, audio lanes, deliver gate) and the AI-assist features,
all driving this studio's own pipeline, with its own name and visual design rather than
Resolve's.

This is far larger than ILY-205's remaining tasks and needs a spec and an order of pages
before any code.

---

## 7. Could not verify

- The audit report's contents and whether a re-audit was ever run (did not open
  `Downloads\UIUX-Studio\reports\...`; no re-audit output found).
- Whether `nh-s901-review-keyboard.spec.ts` passes today (not run; see section 5).
- Whether the console builds and its tests pass on `origin/main` or in the main checkout.
  The main checkout's `node_modules` is also pnpm-style, so it may fail the same way, but
  I did not run anything there.
- Whether the built Phase 2-5 features work against real data. I checked that the code
  exists, not that it behaves; nothing was exercised in a browser.
- Who made each July/August uncommitted edit. Dates and content point to the July console
  sessions; there is no author record for uncommitted files.
- Whether the untracked pipeline modules are current or stale relative to what the film
  lane actually runs.
- Whether `huihui_ai/qwen2.5-coder-abliterate:7b` is still the intended local chat model.
- PermitHub Notion/roadmap state for ILY-205 (not queried), and whether Brad intends
  autostudio IDs to keep being filed in PermitHub after the ILY-203 retirement.
- The companion brief's section 4.1 (not read).
- Task counts in section 2 are from code inspection and are approximate at the
  partial/built boundary.

## 8. Open questions for Brad

1. **Project ID and home.** Continue the 16 open ILY-205 tasks under ILY-205 and file the
   Resolve-style expansion as ILY-206? In PermitHub, or in a registry in this repo?
2. **Uncommitted edits.** Who commits the untracked pipeline modules in the main checkout,
   and do you agree the take-`delete` hunk is dropped?
3. **Scope and order.** For the Resolve-style console: which page first, and does the
   unfinished ILY-205 Phase 0 (pins, shadcn, a11y, type scale) come before it?
4. Is the stale `package-lock.json` to be deleted (pnpm only)?

## 9. Recommended first three tasks

1. **Make the console build and test green on a branch from `origin/main`**: re-cut this
   worktree, fix the Prisma resolution and the two undeclared dependencies, drop the stale
   lockfile, pin `next`/`react`/`react-dom` (ILY-205 task 1), ignore the Playwright output
   folders, and make the review spec write its test ledger to a temp directory instead of
   `ilyrium-shots/ledger/`.
2. **Land the stranded July service code** (section 5, step 2) after Brad arranges step 1
   of that list, so the committed chat-image and multi-file UI actually work.
3. **Write the spec for the Resolve-style console** (section 6): page list, shared
   primitives, what each page reads and writes in the pipeline, invariants (append-only
   takes and ledger), and a phase order that folds in ILY-205 Phase 0 and the Shots grid.
   Then build the page shell first.

---

## Addendum (2026-11-09, later the same session)

Brad approved recommended task 1. It is done on branch `fix/ily-205-console-build`
(cut from `origin/main` `73ab46e`), in the commit after this document. The "Results in
this worktree" table in section 5 describes the state **before** that fix. After it, from
a clean checkout with no database: `pnpm install --frozen-lockfile`, `pnpm run typecheck`,
`pnpm test` (54 tests), `pnpm run build` and `pnpm run test:e2e` (6 passed, 1 `fixme`) all
exit 0, and the specs no longer write under `ilyrium-shots/`.

Corrections to section 5 found while fixing: on `origin/main` it is `pnpm-lock.yaml` that
was stale (missing three dependencies) and `package-lock.json` that matched `package.json`
while locking Next 14; the real runtime is Next 16.4.3 / React 19.3.1 under pnpm. Both
Playwright specs had never been able to pass: the console page needed a live database, and
the catch-all route mock shadowed the specific ones.
