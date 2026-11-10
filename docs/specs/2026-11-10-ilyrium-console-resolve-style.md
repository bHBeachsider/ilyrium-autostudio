# [ILY] Ilyrium Console: a page-per-task studio console in the manner of DaVinci Resolve

PermitHub-Spec-Type: ILY
project_id: ILY-206 (proposed; not yet assigned by Brad, see decision D2)

Status: DRAFT 2 for Brad's review, 2026-11-10. No code has been written against it.
Draft 1 was reviewed by four independent critics; 22 objections stood and are folded in
(section 13 lists what changed). Absorbs the open tasks of ILY-205 (section 9).

## 1. Objective

Brad's request (2026-11-09): "create a console that clones the features of" DaVinci
Resolve, with a pasted feature summary (the pages, the AI tools, the scripting/MCP
surface, collaboration).

This spec turns `apps/control-panel` route `/studio/console` from seven `useState`
"domains" into a routed, page-per-task console: one persistent viewer, media pool,
inspector and timeline, rearranged per task, with Resolve/Premiere keyboard conventions,
real clip editing, and a deliver gate. Each page drives **this studio's generative
pipeline**. It is the studio's own product: own name (working name "Ilyrium Console"),
own visual design, no Blackmagic names, icons, layouts or art.

What "clone the features" means here, stated plainly so nobody is surprised later:

- **Taken from Resolve:** the page-per-task structure, the shared primitives, the editing
  vocabulary and key map, version stacks, a render queue, a command surface for agents.
- **Rebuilt for a generative studio:** media is takes and specs, "compositing" is the
  generation recipe, "grade" is the style kernel plus grade data, "ADR" is voice takes.
- **Not built in a browser:** a real-time 32-bit grading engine, a 3D node compositor, a
  2,000-track DAW, HDR mastering. Those stay in Resolve 20.3.3 Studio (reached by
  OTIO/XML export and scripts) and FilmCraft (headless CLI). Section 4 lists every
  Resolve feature and its fate.

**What v1 is.** Phases 0-5: the pages Library, Review, Sequence, Deliver, Floor and Run.
No Sound, Look, Stills or Graph page. Sequence edits picture; audio in v1 is the film's
existing song/VO mix attached as one lane and passed through unchanged. Estimated at
61-82 working days of one engineer-agent lane (not calendar time), and it cannot start
its server-side half until decisions D1 and D4 are made.

**The proof of v1** is a milestone, not a page count: NH-S901 ("The Scaffold") reviewed,
regenerated where rejected, picture-cut, checked and released entirely from the console,
with its existing audio attached, `chain_ok` true at every step, and the GPU box
confirmed stopped at the end. Mixing from the console is Phase 6.

## 2. Where things stand (the facts the plan rests on)

From `docs/plans/2026-11-09-console-uiux-lane-inventory.md` and a survey of the code on
2026-11-10, corrected by the fact-check pass. Items marked (read, not run) come from
reading code and must be confirmed by a test before anything relies on them.

**Console**
- One route, no URLs per page: `Workspace.tsx` switches seven domains (pipeline, review,
  studio chat, script, generation, assembly, analytics) with `useState`, so changing page
  unmounts it and loses review decisions, notes and chat. Reload returns to Pipeline.
- `ConsoleShell.tsx` (the layout seam the blueprint promised) is used once, by
  `Pipeline.tsx`. Review Room and Timeline hand-roll their own grids.
- The timeline is playback-only: one proportional strip, no clip model, no trim, reorder,
  split, zoom, snap or undo (`TimelinePanel.tsx`, 635 lines).
- Review Room hotkeys are a document-level listener with no modifier guard, and the
  stage-5 review panel stays mounted but hidden, so `A` (approve) is live on every
  Pipeline stage (read, not run).
- The Review, Generation and Assembly domains fed from Neon are inert: `page.tsx` sets
  `sceneNumber: null` on every asset, so nothing joins (read, not run).
- No component primitives, no type-scale tokens (about 340 hard-coded `text-[Npx]`), no
  `loading.tsx`/`error.tsx`, no axe tests. Of ILY-205 Phase 0 only the version pins exist,
  and only on PR #31; ILY-205 Phase 1 (the Shots grid) was never built.
- **PR #31 is open, not merged.** On its branch (`fix/ily-205-console-build`) the app
  installs, type-checks, builds and passes 54 unit tests and 6 browser tests (1 more is
  `fixme`) from a clean checkout with no database, as run on 2026-11-09. `main` does not
  have this yet. This spec's branch is stacked on it.

**Ledgers**
- Writers that can append to `ilyrium-shots/ledger/<song>.jsonl` today:
  1. `ilyrium-shots/provenance.py` `Ledger` (snapshot records with `chain.record_hash`),
     used by `batch_render.py`. All 142 records in `NH-S901.jsonl` are in this format.
  2. The Next review route, with its own copy of the hash code, same format.
  3. `apps/control-panel/lib/ledger.ts` (`{seq,event,songId,payload,prev,hash}`), used by
     the takes route and the fal webhook. This was a deliberate choice in merged PR #28.
  4. `apps/auto-studio/cut_ledger.py` on **open PR #29**, a Python writer of format 3.
  (`backlot/provenance/ledger.py` is a separate ledger and out of scope.)
- Formats 1-2 and 3-4 cannot share a file: each verifier rejects the other's lines (read,
  not run). Any format-3 append to a film ledger that already holds format-1 history
  would break `chain_ok` for that song.
- `Ledger.append` reads the last hash and then appends with no file lock, and
  `batch_render.py` appends from its own long-running process. Two appenders can fork a
  chain (read, not run).
- The provenance record schema is closed (`additionalProperties: false`): approval state
  is pending/approved/rejected with one free-text note. It has no field for hidden,
  selected, kernel version, a frame-pinned note or a release citing a cut.
- In the real NH-S901 ledger no record is approved yet: 57 distinct records, 28 rendered
  and 29 failed, all `pending` (read, not run).

**Backend**
- Four disconnected stores with no shared ids: `outputs/<campaign>/project.json` (the
  :8800 pipeline service), `ilyrium-shots/shots/*.json` + ledger (the film world), Neon
  (rights, runs, approvals), and a SQLite takes layer.
- **The Python backend cannot be imported from a clean checkout.** The modules that
  `studio_pipeline_service.py`, `studio_mcp.py` and `producer.py` import, directly or
  transitively, are largely untracked in Brad's main checkout: `project_store`,
  `studio_pipeline`, `conformance`, `release_gate`, `style_kernel`, `c2pa_sign`,
  `otio_export`, `model_select`, `evals`, `tracing`, `registry_harvest`, `organize_refs`,
  the `media/` package (8 modules plus `__init__.py`), and more. Six **tracked** files
  also carry uncommitted edits there (`studio_pipeline_service.py`, `studio_mcp.py`,
  `pipeline_exec.py`, `stage_scaffold.py`, `model_registry.json`,
  `SONG_ID_REGISTRY.json`). The take-delete code is one hunk inside the first of those.
- There is no edit-decision model: order is `scene_number`, one selected take per shot,
  no in/out, no tracks. Reorder today would mean renumbering, which the ledger rule
  forbids.
- No job model: heavy operations block inside an HTTP request; the queue rail polls
  `/pipeline/jobs`, which no service implements (read, not run).
- No auth on any route. `/box/start` (which starts billing), paid renders and the release
  approval are unauthenticated; reviewer identity is a string the client sends. The MCP
  `approve_stage` accepts an `override` flag with free text, and the release gate can be
  switched off with `ILYRIUM_ENFORCE_RELEASE_GATE=0`.
- `project_store.add_take` selects a new take by default, and also selects the first take
  of any shot that has no selection even when asked not to. Both break "selection is
  separate". A `remove_take` exists (untracked) and must stay unreachable.
- The style kernel has no version field and no bump code.
- **Cost data is partial and inconsistent.** `backlot/cost_preflight.py` already
  implements preview-before-spend (`estimate`, `preflight`, `book`) against
  `backlot/budget.yaml`, which holds deposits, a spend log, a $2 floor and a $6 per-shot
  cap, and no project cap. Its rate table covers only some operations.
  `graph_sync.ENGINE_RATES` is a second, guessed table that disagrees with it.
  `policies/routing.yaml` has per-song and per-shot limits; CLAUDE.md says per-job caps
  live in `.env`. Nothing prices music, voice, Astria refine, inpaint or chat renders. The
  console's own cost-per-render-second is computed wrongly.

**About the pasted Resolve description**
- The Photo page in Resolve 21 is confirmed on Blackmagic's product page.
- Blackmagic's 21.1 release page says it integrates with AI assistants and adds scripting
  APIs. "Built-in MCP server", "Studio only" and a tool count come from trade press only.
  This spec does not depend on it; the studio runs 20.3.3 Studio.

## 3. Pages

Nine task pages plus the existing guided run. Names are ours; rename freely (D3).

| Page | Phase | Resolve analogue | What it is for | Starts from |
|---|---|---|---|---|
| **Run** | exists; routed in 1 | none | The existing 8-stage guided pipeline, kept while other pages take over its stages | `Pipeline.tsx` |
| **Floor** | 2 | Render queue + project status | Jobs, cost, budget, GPU box state. Also a chip on every page | `QueueRail.tsx`, `CostMeter.tsx`, `BoxPanel.tsx` |
| **Library** | 3 | Media | One pool of everything a film owns: shots, takes, keyframes, refs, voice, music, masters. Shot status grid (the unbuilt ILY-205 Phase 1). Bins are saved views | new; asset table in `Workspace.tsx` |
| **Review** | 3 | none (Frame.io-style) | Frame-accurate approve/reject of takes, A/B and wipe, persistent frame-pinned notes, playlists with auto-advance | `ReviewRoom.tsx` |
| **Sequence** | 4 | Cut + Edit | The real edit: tracks, trim, ripple, reorder, split, take swap, markers, undo. A "rough cut" layout (source/record viewers, insert/append) is a mode of this page | `TimelinePanel.tsx` (replaced) |
| **Deliver** | 5 | Deliver | QC, rights, C2PA, the A4 approval, export presets, OTIO/XML hand-off to Resolve | `RightsPanel.tsx`, release-gate route |
| **Sound** | 6 | Fairlight | Voice, music, SFX and ambience on timed tracks; gain, fades, ducking; versioned voice takes; loudness | audio cells in `TimelinePanel.tsx` |
| **Look** | 7 | Color | The style kernel as a versioned thing; grade as data (CDL + one 3D LUT) with slider controls; stale-shot flags; preview frame and scopes | new |
| **Stills** | 8 | Photo | Keyframes, anchors, plates, key art: edit, inpaint, restyle, promote to a shot | `AstriaRefine.tsx`, `StageChecklist.tsx` |
| **Graph** | 8 | Fusion | How a take was made: spec, prompt, workflow nodes, models, lineage. Read-mostly; edits go to the spec | new |

What happens to today's seven domains: **pipeline** becomes Run. **review**,
**generation** and **assembly** (the inert Neon-fed ones) are deleted in Phase 1; Run's
own review stage keeps working until the Review page replaces it in Phase 3. **studio
chat** becomes a side panel of Run, and its box panel moves to Floor. **analytics** stays
reachable from Run until its parts move (queue and cost to Floor in Phase 2, rights to
Deliver in Phase 5). **script** is read-only today; fold into Run stage 2 or drop (D16).

Stage taxonomy: the repo has both 8 stages (console) and 11 (scaffold). Pages are task
views, not stages. Run keeps the 8; Phase 1 commits one mapping table (11 -> 8 -> page).

**Shared primitives** (every page is a layout of these, behind `ConsoleShell`): page bar,
Viewer, Pool, Inspector, Timeline, Take stack, Notes rail, Job/cost chip, Command palette.

**Key map** (Resolve/Premiere conventions, scoped per page so keys cannot collide):
J/K/L transport; arrows = 1 frame, Shift+arrows = 10; I/O marks; M marker/note; A approve,
R reject with reason, N/P take, Shift+N/P shot (Review); B blade, Delete = remove from
sequence (never deletes a take), Ctrl+Z/Ctrl+Shift+Z undo/redo (Sequence); backslash A/B;
Ctrl+K palette; ? cheat sheet generated from the key registry. Every primary action is
reachable from Ctrl+K. Single-key shortcuts are off while focus is in a text field or
select, and never fire with a modifier held.

## 4. Resolve feature coverage (the honest matrix)

Legend: **v1** = Phases 0-5. **later** = Phases 6-9. **gated** = Phase 10, each behind its
own one-page proposal and Brad's approval. **delegated** = done in Resolve/FilmCraft by
script or export. **no** = not built.

| Resolve feature | Fate | How |
|---|---|---|
| Page-per-task workspaces on one project | v1 | Routed pages over one store |
| Media pool, metadata, smart bins | v1 | Library; bins = saved views |
| Proxies and thumbnails | v1 | H.264 proxy + thumbnail job |
| Clone/checksum ingest, Slate ID, camera tethering | no | No camera media here; takes already carry sha256 |
| Cut page: source tape, fast assembly | v1 | Rough-cut mode of Sequence |
| Edit page: tracks, trim, ripple, reorder, split, markers, undo | v1 | Sequence + the Sequence Document |
| Roll/slip/slide and asymmetric trim, dual timeline | no | Later version of Sequence if asked |
| Multicam, nested timelines, optical-flow retime, effects stack | no (delegated) | Finish in Resolve via OTIO |
| Keyframe curve editor, Lottie/OGraf graphics | no | |
| Fusion node compositing, 3D, particles, tracking, roto, keyer, Krokodove | no (delegated) | Graph shows the generation recipe only |
| Color: primaries (CDL), saturation, one LUT | later | Look; grade is data, applied by ffmpeg at render |
| Color: scopes | later | Server-rendered scopes of the preview frame |
| Color: node graph/layer list, curves, colour warper, power windows, tracker, HDR wheels, Wide Gamut, ACES, Dolby Vision, HDR10+, MultiMaster, DCTL | no (delegated) | Mastering stays in Resolve |
| Photo page: stills edit | later | Stills, on existing edit/inpaint recipes |
| Photo page: stills grading, albums, LightBox | no | The grade applies at sequence render only |
| Fairlight: tracks, clip gain, fades, ducking, meters | later | Sound; server mix is the truth, browser meter is indicative |
| Fairlight: ADR | later, reframed | Versioned voice takes (fixes F-0006) |
| Fairlight: 2,000 tracks, clip EQ, chain FX, track folders, Atmos, Spaceview | no | |
| Deliver: presets, batch render, render queue | v1 | Deliver + Floor, real job model |
| Deliver: direct uploads, IMF, DCP | no | Export, then upload by hand or deliver from Resolve |
| AI IntelliSearch | later (text) / gated (visual, faces) | Full-text over prompts, VO, notes first |
| Magic Mask | gated | Grounding DINO + SAM exists box-side as a batch gate only |
| Text-based editing | later, reframed | Script-linked: editing a script line proposes a sequence change |
| AI multicam | no | |
| Speech generator | later | "Generate voice take" on Sound, via the existing ElevenLabs path |
| Voice isolation, music remixer, voice convert | gated | New models; voice convert also needs a consent rule |
| UltraNR/temporal NR, SuperScale/UltraSharpen, Speed Warp, motion deblur, depth map/CineFocus | gated | Each a costed job producing a new take |
| Scripting API (Python/Lua), MCP server | later, reframed | One HTTP command API; the existing studio MCP extended to the same commands. No Python or Lua binding and no in-console scripting |
| Multi-user collaboration, bin/timeline locks | later (locks only) | Version-checked saves + an edit lock; no co-editing, no live chat |
| Blackmagic Cloud, hardware panels, Free/Studio tiering | no | |
| Anything else on a Resolve page not listed above | no | Not built; ask to promote |

## 5. The foundation (what must exist before pages multiply)

### 5.1 One write spine

Every state change and every spend goes through one path. No page gets its own.

1. **One ledger format per song, one appending class, with a lock.** Which format is
   canonical for film ledgers is decision D4; recommended is the `provenance.py` format,
   because NH-S901's history is already in it. Under that choice:
   - `provenance.Ledger` is the only class that appends to a film ledger, and every
     process that appends goes through it: the HTTP service, `batch_render.py`, and
     (after agreement with its author) the cut writer on PR #29.
   - `Ledger.append` takes an inter-process exclusive lock from reading the last hash
     through writing the line.
   - Render-completed and take-registered events that `lib/ledger.ts` writes today keep
     landing in the song ledger, re-expressed through the Python writer. They are part of
     the audit spine and are not moved out. `lib/ledger.ts` stops appending to song
     ledgers itself.
   - Every write validates the song id against `SONG_ID_REGISTRY.json` (including its
     legacy claims), appends, runs `Ledger.verify_chain`, and returns `chain_ok`.
   - If the chain fails to verify, the console and `batch_render.py` both refuse further
     appends for that song. Repair is a human-authored forward record; no line is edited.
   - Until D4 is settled, no format-3 writer may append to a ledger that already holds
     format-1 history.
2. **Where console state that the ledger cannot hold lives (D5).** Hidden flags,
   selection, kernel version stamps, frame-pinned notes and a release that cites a cut
   need either new optional fields in the provenance schema (a "1.1", agreed with the
   film lane, old records still valid) or a separate, hash-chained console event log
   beside the ledger. Recommended: optional schema fields for `hidden`, `selected` and
   `kernel_version` on shot snapshots, because those are facts about a take; a separate
   console event log for notes, sequence versions and releases. A reviewer's rejection
   reason is never overwritten by a later hide or select.
3. **Cost gate at the layer everything passes through.** The gate reuses
   `backlot/cost_preflight.py` and `backlot/budget.yaml` as the single book; no second
   budget file. It is enforced where the producer and `harness/run.py` dispatch work, not
   in a web route, so the console, the studio MCP and CLI scripts all hit it. A spend is
   two calls: `preview` returns per-item cost, total, gates checked and "the box is
   stopped; starting it costs about $1.20/h", plus a short-lived token; `commit` requires
   the token and books the spend. Token and budget state are files, readable by every
   process. An operation with no rate entry is blocked until measured, not guessed.
   `graph_sync.ENGINE_RATES` is retired in favour of the one table.
4. **Minimum auth, early.** Services bind to 127.0.0.1. A bearer token is required for
   box start, any cost-token commit, and the release approval. Reviewer identity comes
   from the token, not from a string the client sends.
5. **Job log.** Heavy operations return a job id at once and append to an append-only
   `jobs.jsonl`. Cancel appends a line and stops queueing; a running paid call is allowed
   to finish and is recorded. Retry creates a new job that references the old. Box
   start/stop appends to `box_intervals.jsonl`, from which billed hours are computed.
6. **Canonical identity.** `ClipRef = {song_id, shot_id, take_id}` everywhere in the
   console. A generated map joins it to `scene_number`/`take_N` and to Neon ids where a
   view needs them. No page invents an id.
7. **Takes are append-only, selection is separate.** The console always creates takes
   with selection off, including the first take of a shot (which needs a change inside
   `project_store.add_take`, not just a flag). Selecting is its own reversible action.
   Hiding is a flag, never a deletion. Nothing can reach `remove_take`.
8. **Console runtime state has one home.** Sequence versions, jobs, box intervals, notes
   and exports live under `outputs/<campaign>/console/`, beside `project.json`, which the
   console owns. The console's code does not edit film content under `projects/` or
   `ilyrium-shots/`. The exceptions each need the film lane's agreement (D4): ledger
   appends through the single writer, the kernel version field (Phase 7), and the
   milestone retrospective in `00_admin/`.

### 5.2 The Sequence Document

The one genuinely new data structure. It is what makes real editing possible without
touching specs, scene numbers or ledger history.

- **Shape.** `sequence {id, song_id, fps, size, video_tracks[], audio_tracks[]}`; a video
  clip is `{clip_id, shot_id, take_id | null, src_in_f, src_out_f, speed, transition_in,
  look_id?, markers[]}`. Time is integer frames at the sequence fps (one project setting,
  default 24).
- **Audio in v1 is one attached lane**: the film's existing song/VO mix, with a start
  frame, passed through to the render unchanged. Gain, fades, ducking and more lanes are
  reserved fields until Phase 6.
- **Conform rule.** Every take is probed once. Proxies are constant-frame-rate at the
  sequence fps with the frame count asserted; a take whose rate differs is conformed by
  the proxy job or refused, never silently stretched. A dissolve needs handle frames on
  both sides; the document is invalid without them.
- **Order is array position.** Reordering never renumbers `scene_number` or a shot id.
- **Versions are append-only.** Each save writes a new `vNNN.json` with `parent_version`
  and a sha256, created exclusively under the same lock as its chain entry, so two
  simultaneous saves cannot both win. A stale `base_version` is refused. Undo in the
  editor is local; "revert" appends a new version.
- **Pins are honest.** `take_id: null` means "hold the keyframe". If a pinned take is
  later rejected or hidden, the clip keeps the pin and is flagged stale; nothing is
  substituted silently. Either case blocks master export (section 6, Deliver) but still
  allows a draft preview.
- **One meaning, two readers.** A TypeScript resolver (browser playback) and a Python
  resolver (render) each reduce a document to a per-frame table of (clip, take, source
  frame). A golden-fixture test fails CI if they differ.
- **Rendered by plain ffmpeg first** (trim, concat, dissolve, mux the attached audio; CPU,
  free). FilmCraft trim commands are adopted only after a time-boxed headless check
  through `harness/run.py`. Resolve gets the same sequence as OTIO/FCP7 XML.
- **Scope of v1 editing:** insert, append, replace, trim in/out, ripple, move, split,
  remove, set take, constant speed, cut or dissolve, marker. No roll, slip or slide.
- **Schema in git** (`sequence.schema.json`), validated on both sides, like the shot spec.

### 5.3 Console foundation

- Routes `/studio/console/[page]` under one layout that holds the store, so state survives
  page changes; `loading.tsx`, `error.tsx`, `not-found.tsx`.
- One typed API client and one base-URL constant (there are five today, one misnamed).
- A key registry with scopes; the cheat sheet and palette are generated from it.
- Component primitives and tokens (type scale, spacing, radius, focus ring) on the existing
  dark palette. Dark-only stays, by the earlier decision.
- Fixed per-page layouts with resizable, remembered panel sizes. No docking.
- Tests: fixtures only (ILY-205 Decision B). Contract fixtures mirror every service
  endpoint the console calls, so CI needs no Python service, no database and no GPU box.
  Take-delete stays removed (ILY-205 Decision A).

### 5.4 Stack (versions read from npm on 2026-11-10; pin exact at install)

| Need | Choice | Notes / rejected |
|---|---|---|
| Primitives | shadcn/ui on Radix, mapped to existing `@theme` tokens | as decided in ILY-205 |
| Layout | react-resizable-panels 4.21 behind `ConsoleShell` | dockview only if tab pop-out is asked for |
| Grid | TanStack Table 9.3 + Virtual 3.14 | v9 migration notes not yet read |
| Server state | TanStack Query | new since ILY-205 |
| Document state + undo | zustand + immer patches | new since ILY-205 |
| Hotkeys | react-hotkeys-hook 5.4 (has scopes) | new since ILY-205; tinykeys has no scopes |
| Palette, toasts | cmdk 1.1 (shadcn Command), Sonner | replaces the hand-rolled palette |
| Viewer | plain `<video>` + `requestVideoFrameCallback`, H.264 proxies | **Media Chrome is dropped**: hand-built controls already exist. ILY-205 forbade substitution without re-deciding; this line is that re-decision. No WebCodecs, ffmpeg.wasm or ProRes decode in v1 |
| Timeline | custom, DOM clips on virtualised tracks | rejected on licence or maturity: Remotion, Twick, designcombo, OpenCut, @xzdarcy/react-timeline-editor |
| Waveform | wavesurfer.js 8 (installed) | |
| Node graph | @xyflow/react 12 (MIT) | litegraph only inside ComfyUI itself |
| A11y tests | @axe-core/playwright | |

## 6. Tasks

Estimates are working days for one engineer-agent lane and are guesses, revised upward
after review; Sequence is the likeliest to overrun. **v1 (Phases 0-5): 61-82 days.**
Phases 6-9 add 25-34. Phase 10 is per tool. Tasks marked **[D1]** cannot start until the
backend is importable from git (decision D1); **[D4]** needs the film lane's agreement.

**If D1 slips:** Phase 0 is limited to tasks 3 and 9, and Phase 1 proceeds on fixtures.
No server-side task in Phases 2-5, and no Verify that imports the service, starts before
D1 lands. That is a stop, not a workaround.

### Phase 0 — Trust layer: reproducible backend, one ledger writer (6-8 days)
Precondition: PR #31 is merged, or work branches from `fix/ily-205-console-build`.
1. Land the backend in git (Brad's action, D1): compute the exact set of local modules
   that the service, the MCP and the producer import and that `git ls-files` lacks, and
   commit that allow-list after a secrets scan. Commit the six edited tracked files, using
   a partial add on `studio_pipeline_service.py` so the take-delete hunk is left out.
   Do not take `stage_scaffold.py`'s removal of `project_paths` resolution, backup files,
   temp media, scratch scripts or `kernels/` (film lane's). `pipeline_exec.py` needs a
   film-lane read first.
2. **[D1]** Pytest: the service and the MCP import from a clean checkout; no route or tool
   reaches `remove_take`. Add a pinned Python requirements file.
3. Ledger cross-format test, written first and independent of D1: a format-3 line verified
   by `provenance.Ledger(dir).verify_chain(song_id)`, and a format-1 file verified by the
   TypeScript verifier. Record both outcomes in `FINDINGS.md`.
4. **[D4]** Inter-process lock inside `Ledger.append`, with a test in which two processes
   append concurrently and the chain still verifies.
5. **[D4]** Settle D5 with the film lane and write it down: the provenance schema 1.1
   fields and/or the console event log, with a test that existing 1.0 records still
   validate and chain.
6. **[D1][D4]** One HTTP endpoint over the single writer. The Next review route becomes a
   proxy: an unknown shot is a 404 (it stops fabricating records), song ids are checked
   against the registry. The takes route and fal webhook write through the same endpoint.
7. **[D1]** Fix the shots payload to carry `shot_id`, `song_id`, `c2pa_status`, measured
   `duration_s` and `hidden`; forward the reject reason into regenerate; make regenerate
   and edit leave selection untouched, including the first take of an unselected shot
   (change in `project_store.add_take`), and update the tests that assumed otherwise.
8. **[D1]** Generate and persist the `ClipRef` map at project adopt.
9. Contract fixtures for every endpoint the console calls (seeded from the service as it
   stands, labelled unverified until task 2 passes), a Playwright helper that serves
   them, a `ci:test` script, and a CI workflow so PRs report checks.
10. Verify: on a fresh clone, install, typecheck, vitest, build, Playwright and pytest
    pass with no database, no `.env` and no box; the service answers `/health`; a decision
    written through the endpoint leaves `chain_ok` true on a fixture ledger; the two-process
    append test passes; an unregistered song id is refused; a first take created with
    selection off leaves the shot unselected; nothing in `apps/control-panel` writes to
    `ilyrium-shots/ledger/` directly (grep test).

### Phase 1 — Shell and foundation (absorbs ILY-205 Phase 0) (12-16 days)
11. Routes `/studio/console/[page]` with a shared layout and store provider; redirect `/`;
    `loading.tsx`, `error.tsx`, `not-found.tsx`. At the end of this phase `run` is the
    only real page; every other slug serves a placeholder naming the phase that builds it.
12. Typed API client with TanStack Query; one base-URL constant; no empty `catch` blocks,
    a visible error state instead.
13. Key registry with scopes; remove the document-level Review listener; generate the
    palette commands and cheat sheet from the registry.
14. Install and pin shadcn/Radix, cmdk, Sonner; build the primitives the pages need on the
    existing tokens.
15. Type-scale, spacing, radius and focus-ring tokens; replace `text-[Npx]` and inline hex
    in the four largest files; lint rule against new ones.
16. Fix the six ILY-205 audit findings still open (alt text, unlabeled fields, clickable
    rows, reduced motion, route boundaries, inline hex). The seventh, take-delete, is
    closed by Decision A.
17. Split `Pipeline.tsx` into a run controller and stage components (the Run page), and
    reduce `Workspace.tsx` to the page shell. Apply the domain dispositions in section 3:
    delete review, generation and assembly by name; chat becomes a Run side panel;
    analytics stays reachable from Run.
18. Add `@axe-core/playwright` to every route; commit the 11 -> 8 -> page mapping table.
19. Verify: Run and each placeholder slug load by URL and survive reload; Run's state
    (stage, chat) survives Run -> placeholder -> Run; pressing `A` outside the review stage
    does nothing and Ctrl+K never pauses a video (Playwright); axe reports zero serious or
    critical issues on every route; the cheat sheet equals the registry (test); no console
    file over 500 lines except `TimelinePanel.tsx`, exempt until Phase 4 replaces it.
    Manual, by Brad, since the tool lives outside the repo: the UIUX-Studio static audit
    scores at least 85 with a11y at least 80, design system at least 70, and no high or
    medium findings; the score file is committed.

### Phase 2 — Write spine and Floor (9-12 days)
20. **[D1]** Minimum auth (5.1 item 4): localhost bind, bearer token on box start, commits
    and release approval; reviewer identity from the token.
21. **[D1]** Cost gate at the producer/harness layer on `cost_preflight` and `budget.yaml`
    (5.1 item 3), with file-based tokens. Wire the console operations (regenerate, edit,
    keyframe, music, refine, chat render, box start) and every paid tool in
    `studio_mcp.py` through it. State in the code which of this gate and the existing
    `confirm_cost` step is authoritative.
22. **[D1]** One rate table: give each operation in task 21 a measured rate, or mark it
    "cost unknown, blocked". Add session and project cap fields to `budget.yaml` (D9).
    Retire `graph_sync.ENGINE_RATES`.
23. **[D1]** `jobs.jsonl` job model; wrap the heavy operations as jobs; list, cancel,
    retry; rewire the queue rail.
24. **[D1]** `box_intervals.jsonl`; idle is defined server-side as no running job and an
    empty render queue; the idle check runs in the service so it works with the browser
    closed. No auto-stop while a job is running.
25. `lib/metrics` registry with a vitest per metric: cost per render-second is render-run
    cost over measured duration, or "n/a"; never an assumed 8 s.
26. Floor page; box card with billed hours and idle warning; cost/box chip on every page;
    palette commands for every primary action.
27. Verify: a paid call with no token, a stale token or over the cap is refused over HTTP,
    through each paid MCP tool, and through the keyframe CLI (pytest; one test enumerates
    the MCP tools and fails if a paid one is not behind the gate); an unauthenticated box
    start or approval is refused; regenerate in the UI does nothing until the preview is
    confirmed (Playwright); jobs sum equals the cost summary on fixtures; the idle warning
    fires at the threshold under a fake clock; the estimate is within 20% of the fake-run
    actual.

### Phase 3 — Library and Review (absorbs ILY-205 Phase 1) (8-10 days)
28. Shared Viewer: probed fps (not a hard-coded 30), timecode, J/K/L, frame step, A/B and
    wipe. **[D1]** Proxy and thumbnail job (ffmpeg on the local machine, CPU), conformed
    per 5.2.
29. Library: pool endpoint with filter and pagination; grid of song -> scene -> shot rows
    by pipeline step with status chips and a version-stack cell; saved views ("Pending
    review", "Approved, no provenance", "NH-S901 teaser"); inspector with take stack and
    provenance. The grid itself writes nothing.
30. Hide/unhide take through the store chosen in D5; hidden takes behind a toggle.
31. Review on the write spine: frame-pinned notes persisted in the console event log;
    approve/reject with required reason; select as a separate action; reject can queue a
    previewed regenerate carrying the reason; playlists with auto-advance. One Review
    component serves both the page and Run's review stage.
32. Verify: every shot of the fixture film appears with its true ledger status and the
    counts reconcile to the ledger in a test; the grid is keyboard-navigable; the fixture
    teaser is reviewed with the keyboard alone; notes survive reload; `chain_ok` is true
    after the session by the Python verifier; screenshot baselines are committed; Brad
    confirms on the real NH-S901 ledger (read-only) that Library matches the CLI.

### Phase 4 — Sequence (20-28 days)
33. `sequence.schema.json` (including the single attached-audio lane, the conform rule and
    dissolve handles), the operation set in 5.2, and valid/invalid fixtures.
34. TypeScript and Python resolvers with shared golden fixtures.
35. **[D1]** Sequence store and routes: list, get, save version (exclusive create, stale
    base refused), revert, dry-run compile (frame table, duration, cost). Hash-chained
    version log in the console event log.
36. Timeline UI: tracks, ruler, playhead, zoom, snap, selection, trim handles, drag
    reorder, split, markers, undo/redo, the key map; one clock driving the viewer; the
    attached-audio lane with its waveform.
37. Take swap in place from the inspector: an existing take, or a previewed regenerate.
38. **[D1]** ffmpeg sequence renderer as a job, muxing the attached audio unchanged;
    output is a new cut under `outputs/<campaign>/console/` that records the sequence
    version; nothing is overwritten.
39. Rough-cut layout: source and record viewers, I/O marks, insert/append/replace.
40. **[D1]** OTIO/FCP7 XML export of any version, with a scripted Resolve import recipe.
41. Time-boxed check (1 day): FilmCraft trim and place commands headless via
    `harness/run.py`; adopt behind a flag only if it passes.
42. Verify: reorder two clips, trim one, split one, undo twice, redo once, save
    (Playwright) yields a valid new version while the previous file is byte-identical; a
    second tab on a stale version is refused, and two simultaneous saves produce exactly
    one new version (test); both resolvers produce identical frame tables for at least 10
    golden documents; the rendered cut's probed duration is within one frame of the
    document, the attached audio's onset is within one frame of its start, and five
    chosen frames match golden frames within a mean absolute difference of 2/255; no file
    under `ilyrium-shots/shots` or `ledger` changes except appended lines; the NH-S901
    fixture plays end to end in sync with its audio, with held keyframes for unapproved
    shots (closes ILY-205 task 22); the exported OTIO opens in Resolve (Brad, manual).

### Phase 5 — Deliver (the v1 line) (6-8 days)
43. Deliver page: one ordered gate panel. Blocking gates: `chain_ok`; conformance;
    **sequence resolves** (every clip in the exported version points at an approved,
    non-hidden take; held keyframes and stale pins block master export and allow only a
    draft preview); QC; rights; C2PA; A4. Loudness is measured on the attached audio and
    reported only; it becomes blocking after Phase 6. The page shows whether release-gate
    enforcement is on and refuses master export when it is off.
44. Make "Export to Master" real: preset catalogue with 21:9 and 4:5 added; exports as
    jobs with a manifest (sequence version, sha256, preset). Keep the source-and-licence
    panel and the blocked-only filter from ILY-205.
45. Override scope: only the rights-risk blockers the approve route already allows an
    override for. Never `chain_ok`, conformance, sequence-resolves, C2PA or A4, and never
    from an agent or MCP caller. An override needs a typed reason and a token identity,
    and is recorded on the export manifest and in the console event log.
46. A4 stays human: the no-likeness attestation is typed by the reviewer in the UI and the
    endpoint requires the human token. Remove `override` and `override_reason` from the
    MCP `approve_stage` at stage 7 and stop it hard-coding rights states.
47. Drive the rights view from the shot list, reporting "no takes" and "unapproved"
    separately (un-fixme test P5-05).
48. Verify: master export is blocked while any blocking gate is red and allowed on a clean
    fixture (Playwright); a fixture with a held keyframe and one with a clip pinned to a
    hidden take each block master export and allow a draft preview; posting the A4 payload
    without the human token is refused, and so is the MCP tool (tests); an override
    attempt on a non-overridable gate, or from MCP, is refused; re-export creates a new id
    and overwrites nothing; every take in the fixture shows a rights state.
49. **Milestone (Brad, supervised, real spend): release NH-S901 from the console**, picture
    cut with its existing audio attached. Every spend goes through the previewed gate.
    Write the retrospective to `projects/new_harnomy_usa/00_admin/` and any recurring
    failure to `FINDINGS.md`. Confirm the box is stopped.

### Phase 6 — Sound (6-8 days)
50. Versioned voice takes: generation never overwrites an existing file (FINDINGS F-0006);
    a selected-voice pointer.
51. Open the reserved audio fields: multiple lanes, gain, fades, duck rules; legacy audio
    elements are read into lanes without rewriting old project files.
52. Sound page: track list, gain, mute/solo, fades, duck rules, waveform lanes, "generate
    voice take" (previewed), a short mix-window preview job; per-clip ducking rendered by
    ffmpeg. Loudness becomes a blocking Deliver gate.
53. Verify: a second voice generation leaves the first file byte-identical; a four-track
    fixture renders and measures within 1 LU of expectation by the server QC pass; the
    ducking envelope is present in the render; the browser meter is labelled indicative.

### Phase 7 — Look (7-9 days)
54. **[D4]** Kernel version field, changelog in `00_admin/`, bump route; new render
    records are stamped with the kernel version; takes rendered under an older version,
    or with no stamp, are flagged stale in Library and never re-rendered automatically.
55. Grade block (ASC CDL slope/offset/power, saturation, one 3D LUT id, colour-space tags)
    in the kernel and as a per-clip `look_id`; LUT upload and validation.
56. Look page controls: sliders and numeric inputs for the CDL values and saturation, at
    kernel level (a bump) or per clip; reset to neutral; before/after wipe.
57. Server-rendered preview frame and scopes (waveform, vectorscope, histogram) with a
    hash cache; grade applied at sequence render by the same ffmpeg filters.
58. Verify: a kernel edit creates v+1 and a changelog and flags exactly the older takes
    (test); changing a CDL value changes the preview frame, and preview and rendered frame
    match within a mean absolute difference of 2/255 on at least 5 fixture frames and 2
    LUTs; no take file changes during any Look action (hash check); the page says
    "preview, not a mastering reference".

### Phase 8 — Stills and Graph (6-9 days)
59. Stills: HTTP routes for the edit, inpaint and text-edit recipes that are MCP-only
    today, behind the cost gate; results are new image takes with selection off and a
    parent link; promoting a still to a shot keyframe is a validated spec edit.
60. Graph: read-only node view of a take's recipe from the ledger and the workflow JSON,
    with a cached node-metadata snapshot so the box need not be running; spec-owned
    parameters (seed, prompt, steps, LoRA) editable through conformance; "Open in ComfyUI"
    for real node editing.
61. Verify: an inpaint yields a new take and the original is byte-identical; the tracked
    Wan workflow renders every node and edge (Playwright); a parameter change produces a
    conformance-checked spec diff and a previewed job, never a direct render.

### Phase 9 — Command API, Find, locks (6-8 days)
62. One command schema used by both HTTP and the studio MCP: sequence operations, pool
    queries, cost preview, hide/select, jobs. Project per request, no global project.
    This unifies the schema; MCP cost gating already exists from Phase 2.
63. Find: a local full-text index over prompts, voiceover, kernel text, take metadata and
    notes; results open in Library.
64. Script-linked editing: deleting or reordering a script line proposes the matching
    sequence change, applied only on confirm, as a new version.
65. Edit lock per sequence with owner and expiry, on top of the version check.
66. Verify: the same operation over the UI, HTTP and MCP yields the same version hash; a
    second editor sees "locked by" and overwrites nothing; a phrase from a voiceover finds
    the right shot; a script-line proposal never applies without confirmation.

### Phase 10 — AI tools as costed jobs (gated; 2-4 days each)
67. A generic derived-take job: tool, parent take, parameters, cost preview; output is a
    new take or a sidecar with parent lineage; the parent is never modified.
68. For each candidate (upscale, frame interpolation/speed warp, motion deblur, noise
    reduction, object mask, depth map, voice isolation, music remixer, voice convert,
    visual search, word-level transcript): a one-page proposal under `docs/specs/`
    covering model and licence, VRAM fit on one 24 GB box, cost class, registry modality,
    and for voice convert a consent rule. Build only after Brad approves that proposal.
69. Verify per tool: a fixture test with a fake runner; one supervised real run; the parent
    is byte-identical afterwards; cost preview precedes execution; the box is confirmed
    stopped after the run; the licence is recorded in the registry.

## 7. Constraints and invariants

- Takes are append-only. Selection is separate and reversible. No delete, overwrite or
  renumber of a take, a voice file, a cut, a sequence version or a ledger line. "Delete" on
  the timeline removes a clip from a sequence version only.
- Every render and every registered take appends to the song ledger. The ledger has one
  format per song, one appending class with a lock, and must verify `chain_ok` after every
  session. Never rewrite, reorder or renumber history.
- Specs are the contract: parameter edits go to the shot spec through the schema and
  `conformance.py`, never to a take or a workflow file. Nothing renders unconformed.
- A kernel change is a version bump that flags dependents; nothing re-renders by itself.
- Release is gated. A4 is human, typed, authenticated and non-delegable. No auto-approve.
  Overrides exist only where section 6 task 45 says. Master export refuses to run with
  gate enforcement switched off.
- Cost: preview before any spend, from any caller; unknown cost blocks; one budget book;
  one g6.2xlarge at a time; the box is stopped when idle and nothing starts it without an
  explicit, previewed, authenticated confirm.
- All model, ComfyUI and FilmCraft calls go through `harness/run.py` (`lint_no_raw_sdk`).
  FilmCraft runs headless only; its control port is never opened.
- Script, don't click: Resolve and Blender are reached by export and scripts.
- Tests use fixtures. No test, audit or CI run touches production Neon, the real ledger,
  a paid API or the GPU box. The only real-spend step in this spec is task 49, supervised.
- Own product: no Blackmagic or Resolve branding, UI art, names or trademarks.
- Lane boundary: as in 5.1 item 8.

## 8. Explicit non-goals

- No real-time grading engine, node-based grading, curves, power windows, tracking,
  HDR/ACES/Dolby Vision mastering or calibrated monitoring.
- No 3D or node compositor, particles, roto or keyer.
- No DAW: no plugin hosting, clip EQ, Atmos or sample-level editing.
- No multicam, nested timelines, roll/slip/slide, optical-flow retime, effects stack or
  keyframe curves.
- No Python or Lua scripting binding and no in-console scripting.
- No real-time co-editing, presence cursors, chat or cloud collaboration.
- No direct uploads to platforms, IMF or DCP.
- No third-party editor kit, no in-browser transcode, no ProRes or HEVC browser decode.
- No dockable windows, light theme or mobile layout.
- No changes to the Streamlit Ad Studio; no Neon schema changes without stopping to ask.
- No GPU-dependent AI tool in v1.

## 9. Where ILY-205's open tasks land

ILY-205's numbering is kept for traceability. Re-verify each "built" task rather than
trusting the inventory's count. Whether ILY-205 is formally closed is decision D15.

| ILY-205 task | Lands in |
|---|---|
| 1 pin versions | done on PR #31 (open, unmerged) |
| 2 shadcn, 4 type scale, 6 axe | Phase 1 (tasks 14, 15, 18) |
| 3 seven audit findings | Phase 1 (task 16); take-delete closed by Decision A |
| 7 re-audit, zero high/medium | Phase 1 (task 19), manual |
| 5 metrics to `lib/metrics` | Phase 2 (task 25) |
| 8-12 Shots grid, saved views, inspector, verify | Phase 3 (Library, tasks 29, 32) |
| 13 Media Chrome | dropped; plain video re-decided (section 5.4) |
| 14, 16-18 A/B, hotkeys, append-only reject, replace approve flow | built; rehomed on the write spine in Phase 3 (task 31) |
| 15 review playlists, auto-advance | Phase 3 (task 31) |
| 19 verify keyboard review and chain | Phase 3 (task 32) |
| 20-21 waveform and timeline | replaced by Sequence, Phase 4 (task 36 keeps the waveform) |
| 22 NH-S901 plays in sync | Phase 4 (task 42) |
| 23 queue, 24 box intervals, 25 cost meter | Phase 2 (tasks 21-26) |
| 26 palette and cheat sheet, every action reachable | Phase 1 (task 13) and Phase 2 (task 26) |
| 27 estimate accuracy | Phase 2 (task 27) |
| 28 C2PA chips and licence panel, 29 blocked badge and gate, 30 verify | built; made real in Phase 5 (tasks 43-48) |
| ILY-205 open decisions | take delete: Decision A (recorded). Audit target: Decision B, fixtures (recorded). Phase order: overtaken; see D7. Figma first: D14 |
| Console E2E plan of 2026-10-29 (16 test IDs) | superseded: each page's Verify task is its E2E |

## 10. Open decisions (for Brad)

Each has a recommended default. D1 and D4 block the server-side half of the work.

- **D1. Land the backend in git.** Who and when? *Recommended:* Brad, one chore PR, before
  Phase 0, scoped as task 1 says (import allow-list, secrets scan, the six edited tracked
  files, no take-delete hunk, no `stage_scaffold.py` path regression).
- **D2. Project ID and home.** *Recommended:* ILY-206, with this file in this repo as the
  source of truth, since PermitHub retired ILY-203 for targeting this repo.
- **D3. Names.** Product ("Ilyrium Console") and pages. *Recommended:* accept or replace.
- **D4. Film ledger format and writer; film-lane agreement.** Which format is canonical
  for film ledgers? *Recommended:* the `provenance.py` format, since NH-S901 is in it.
  Consequences to agree with the film lane and the author of PR #29 before task 6: the cut
  writer on PR #29 is rebased onto that format (or writes its own file) before it merges;
  PR #28's takes and fal writes move behind the single writer; the lock goes into
  `Ledger.append`; `batch_render.py` honours the broken-chain rule. This also covers the
  other writes under `projects/` and `ilyrium-shots/` listed in 5.1 item 8.
  *Alternative:* make format 3 canonical, which means NH-S901 starts a new ledger file,
  since history is never rewritten.
- **D5. Where console facts live.** *Recommended:* optional provenance schema fields for
  `hidden`, `selected`, `kernel_version`; a separate hash-chained console event log for
  notes, sequence versions, releases and overrides. *Alternative:* everything in the
  console event log and no schema change.
- **D6. Scope line.** *Recommended:* commit to Phases 0-5; decide on 6-9 after two weeks
  of use. Skipping Phase 6 means the console never mixes; audio stays an attached file.
- **D7. Order after the foundation.** *Recommended:* Library and Review, then Sequence,
  then Deliver. Deliver cannot come before Sequence as specified, because an export
  records a sequence version.
- **D8. Selection off on regenerate.** Already required by the contract ("selection is a
  separate, reversible act"). To confirm only: MCP and Run users will need an explicit
  `select_take` afterwards, including for a shot's first take.
- **D9. Budget and box policy.** `budget.yaml` has a $2 floor and a $6 per-shot cap and
  nothing else. *Recommended:* add a session cap ($20) and a project cap ($25 until real
  numbers exist) there; confirm any batch above $5; idle warning at 15 minutes; auto-stop
  at 45 minutes only if Brad opts in, never mid-job. Say which of `.env`, `budget.yaml`
  and `policies/routing.yaml` owns per-job limits; recommended `budget.yaml`.
- **D10. Sequence fps.** *Recommended:* one project fps, default 24.
- **D11. Graph and Stills.** *Recommended:* Stills yes; Graph only if lineage view is
  wanted.
- **D12. AI tools.** Which proposals first? *Recommended:* upscale and text search first;
  voice convert last, behind a consent rule.
- **D13. Collaboration.** *Recommended:* single operator; locks in Phase 9 only if a
  second editor is real.
- **D14. Figma round.** *Recommended:* one mock round for Library and Sequence before
  Phase 3.
- **D15. Close ILY-205?** *Recommended:* yes, as absorbed here; update its PermitHub
  registry entry, which currently says both "active" and "Not Started".
- **D16. The read-only Script domain.** *Recommended:* fold into Run stage 2.

## 11. Risks

- **Backend not reproducible** until D1. Without it more than half of v1 cannot start.
- **Ledger.** Four writers, two formats, no lock, and an open PR that adds to it. Tasks
  3-6 turn the inferred collisions into tested facts and one writer; they depend on
  agreement outside this lane (D4). Highest invariant risk.
- **Sequence overrun.** Every editing feature multiplies state and tests. The operation
  set in 5.2 is the scope. Variable frame counts in generated clips are the likeliest
  source of off-by-N bugs; the conform rule exists for that.
- **Preview/master drift** on long-GOP footage and on colour. Mitigated by conformed
  proxies, the golden frame-table test and server-rendered Look previews; not eliminated.
- **Cost leakage.** The gate only works if it sits below every caller. Any paid path that
  bypasses the producer/harness layer defeats it; task 27's enumeration test is the check.
- **Auth is minimal** (one local token). Adequate for a single operator on one machine;
  not for a hosted or multi-user console.
- **NH-S901 has no approved takes today.** The milestone includes the review work, and
  29 of its 57 records are failed renders.
- **One shared 24 GB GPU.** Interactive AI tools queue behind renders. Some candidate
  models are non-commercial (FLUX.1-dev, some depth checkpoints, XTTS v2).
- **Next 16** has breaking changes (`AGENTS.md`); read its bundled docs before Phase 1.
- **Estimates.** Draft 1 said 45-58 days for v1; review found Phases 1, 2 and 4 too low.
  61-82 is still a guess.
- **Nothing in the survey was executed.** The "read, not run" items in section 2 are the
  first things Phase 0 and Phase 1 tests must confirm or correct.

## 12. Source

- Brad's request and pasted Resolve summary, 2026-11-09.
- `docs/plans/2026-11-09-console-uiux-lane-inventory.md` (this repo).
- ILY-205: `PermitHub-API/docs/roadmap/inbox/processed/ilyrium-studio-console-uiux-upgrade.md`
  and `PermitHub-API/Claude outputs/PLAN-ilyrium-studio-console-uiux-2026-10-26.md`;
  `apps/control-panel/app/studio/console/ILY-205-DECISIONS.md`.
- `docs/STAGE_CONSOLE_BLUEPRINT.md`, `docs/PRODUCTION_CONSOLE_ROADMAP.md`,
  `docs/STUDIO_OS_STAGE_WORKSPACES.md` (untracked, Brad's main checkout).
- Survey by five readers and three independent design proposals (pipeline-first,
  editor-first, risk-and-cost-first), 2026-11-10. This spec takes the write spine and the
  NH-S901 milestone from the first, the Sequence Document and shared primitives from the
  second, and the phase order, v1 line and gating of AI tools from the third.
- Critique by four reviewers with each objection challenged, 2026-11-10.

## 13. What changed from draft 1

- Ledger: named all four writers and PR #29; the canonical format is now a decision (D4)
  with consequences spelled out; added a lock and a broken-chain rule; render and take
  events stay in the song ledger.
- Added D5: the provenance schema cannot hold hidden, selected, kernel version, notes or
  releases as it stands.
- Cost: reuse `cost_preflight` and `budget.yaml` instead of a new budget file; gate at the
  producer/harness layer so MCP and CLI are covered; unknown rates block.
- Auth minimum moved from Phase 9 to Phase 2; A4 and overrides tightened; a
  "sequence resolves" gate added so held keyframes and unapproved takes cannot ship.
- v1 no longer claims a mix: audio is one attached lane until Phase 6.
- Phase 1's Verify no longer requires pages built later; every existing domain has a
  stated fate.
- Selection-off needs a change inside `add_take`, not a flag.
- D1 widened to the edited tracked files and an explicit allow-list; a stop rule added if
  D1 slips.
- Estimates raised: v1 from 45-58 to 61-82 days.
- Matrix: missing Resolve items placed; scripting row no longer implies a Python/Lua API;
  Look gained grade controls; stills grading marked not built.
