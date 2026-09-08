# OWS — the Ilyrium Backlot
### Evaluation of the backlot proposal, reconciled with what NH-S901 taught, and a plan

*v2, 2026-09-08. Supersedes v1 (written before the proposal was seen). Status: proposal.*

Two seeds are on the table. The first is the **backlot proposal** Brad brought: an AI-native digital studio backlot
with OpenUSD at the centre, Blender for authoring, Unreal for shooting, a catalogued and provenanced asset library, a
Backlot Agent that assembles a filmable stage from a scene description, and a loop that makes every production
cheaper than the last. The second is the **NH-S901 record**: eleven cuts of a sixty-second teaser, a code-defined
greybox world with per-shot cameras, a geometry gate, and a ledger of thirty-seven ways the image models broke
continuity. The proposal describes where the studio should end up. The record says which parts of the road are
load-bearing. This document is the two put together.

---

## 1. Evaluation of the proposal

### 1.1 What it gets right, and why the record confirms it

**OpenUSD as the canonical representation.** This is the proposal's most important decision and it is correct. The
things NH-S901 needed and improvised — set states (open joists → half-decked → beam → finished), dressing layers
(harvest), weather layers (drizzle), per-shot cameras, a banner as a tracked plane — are exactly USD's native
vocabulary: variant sets, layers, references, prims. The `layout.yaml` I proposed in v1 is a home-made subset of a
USD layer stack; better to use the real thing from the start. Blender exports and imports USD; Unreal imports it well;
`usd-core` gives Python composition for free.

**A catalog with structured metadata and provenance.** Right, and it converges with the studio's existing instinct
(the batch_render provenance ledger, the findings ledger). The proposal's framing of a *rights-cleared proprietary
asset corpus* is the correct economic argument: every set built for New Harnomy is a set the next production does not
build. Provenance per asset — created how, by whom, licensed how, used where, approved when — should be there from
asset one, because it cannot be back-filled honestly.

**Deterministic 3D feeding generative imagery (§9).** This is the exact architecture the teaser arrived at by
failure: the world renders depth, segmentation, camera and continuity references; the generative model paints inside
them. The proposal's list — character reference, environment reference, camera trajectory, depth, segmentation,
lighting, pose, motion, props, wardrobe, continuity reference, previous frame — is the conditioning stack. Everything
in v1's Phase 1 is a subset of it.

**Universal sets with variants (§4), procedural generators (§2), the self-expanding loop (§10).** All sound. Variants
are USD variant sets; generators are what `build_backlot.py`'s `storefront()` already is in miniature; the loop is
the findings ledger turned into a build queue.

**"Build the catalog, the USD schema and the agent at the same time, around one short."** Correct emphasis. The
first milestone being an *assembled, filmable stage from a scene description* rather than *a beautiful scene* is the
right test.

### 1.2 Where the record disagrees, or the proposal is early

**It has no verification layer.** The proposal goes catalog → agent → USD → Unreal → render as if assembly were the
hard part. The record says assembly is the easy part; the hard part is that every generative step *re-invents* what
it was given (NH-USA-016, 034, 041, 043, 045, 047, 048, 051 — eight findings, one pattern). A backlot without a gate is
a library of things the model will ignore. The gate — projected control points, segmentation IoU, OCR of text
planes, a judge reading the comparison sheet — is the studio's contribution to this architecture and must sit
between "generate" and "spend" at every tier.

**Unreal is right for a different studio.** Its virtual-production stack (nDisplay, Live Link, camera tracking,
Composure) exists for LED volumes and tracked physical cameras. Ilyrium is not shooting people on a stage; it is
generating frames from a world. What Unreal offers *this* studio is real-time iteration on camera and light, and fast
conditioning passes for moving cameras. Both matter later — sequences with camera moves, a director working live —
and neither is needed to fix what broke in the teaser. Headless Blender already renders the passes and the survey
views in seconds. Unreal is a Phase 3 adoption, on evidence of need, not a foundation. Omniverse likewise: its
value here is USD services, which `usd-core` provides without it.

**Film-ready photoreal assets are the wrong fidelity for most of the backlot.** The proposal assumes hero-quality
models, materials and LODs. In a generative pipeline the look comes from the model; the world's job is to fix *where*
and *what state*. Two grades are enough: **conditioning-grade** (greybox at true scale with segmentation IDs and
text planes — what exists now, cheap, and sufficient for depth/seg conditioning) and **hero-grade** (only where the
generative path cannot be trusted: text-bearing signage, hero props, anything read in close-up). Building
hero-grade everything is the traditional CG cost the proposal itself, in §9, argues the studio should avoid.

**Natural language in, geometry out is where continuity dies.** "Give me 1970s Manhattan at night in rain" is the
right *interface*, but the agent's output must be a structured spec against a catalog of real geometry — never a
prompt to an image model. The record's worst failures came from prose asked to do geometry's job. The Backlot Agent
resolves *assets and states*; it does not describe scenes to a diffusion model.

**Scope.** Five environments, ten modular sets, two hundred props, ten vehicles, five characters, a virtual-camera
system, a catalog, a schema and an agent is a studio department's quarter. For a solo operator with Claude sessions
the MVP has to be one production's worth of world — New Harnomy — with the schema, catalog and agent built at full
generality but populated only as far as the next sequence needs. "Generic_USA" is a bucket to grow into, not to
fill first. Semantic search over embeddings is premature below a few hundred assets; the metadata schema must be
right on day one so it can be added without migration.

**Characters.** Listed as assets; the hard part is not a rig, it is identity across generated frames, which the
studio handles with anchors and LoRAs. In the backlot a character is a mannequin on a mark — enough for blocking,
pose passes and eyelines — plus a pointer to its identity assets. That is a deliberate half-measure and should be
labelled as one.

### 1.3 Net

Adopt the proposal's spine — USD, catalog, provenance, agent, self-expanding loop, deterministic-3D-into-generative —
now. Add the verification layer it lacks. Defer Unreal and Omniverse to evidence of need. Scope the MVP to New
Harnomy. Keep the world conditioning-grade except where close-ups demand more.

---

## 2. Architecture (as amended)

```
                          BACKLOT AGENT
             libretto scene ─► asset + state + camera spec
                                  │  (never a prompt)
                                  ▼
                          BACKLOT CATALOG           provenance on every row
                 locations · sets · props · text planes · marks
                 cameras · lighting states · weather states
                                  │
                                  ▼
                          OpenUSD STAGE  (layers + variant sets = states)
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
        BLENDER (headless)   CONDITIONING        [UNREAL — phase 3,
        author · generators  clay depth normal    moving cameras,
        USD export           seg-ID line-art      live iteration]
                             text quads · control points
                                  │
                                  ▼
                          GENERATION  (one entry point per tier)
                 structure-locked key (ControlNet) · camera-preserving edit
                 (single-reference) · motion (Veo first/last · Wan on box)
                                  │
                                  ▼
                          THE GATE  — before any spend
                 projected posts · seg IoU · OCR · judge on the sheet
                 PASS / WARN / FAIL  + sheet saved beside every key
                                  │
                                  ▼
                 RENDER ─► LEDGER ─► ASSEMBLE ─► FINDINGS ─► RULES ─► (loop)
```

---

## 3. The plan

Six phases. Each ends in a check that does not depend on a summary.

### Phase 0 — USD, catalog and provenance under what already exists (no spend, ~3 sessions)

1. Create `backlot/schema/asset.yaml` — the catalog row: `asset_id`, `kind`, `production`, `period`, `states[]`,
   `grade` (conditioning | hero), `formats[]`, `provenance` (method, creator, source, license, approval, used_in[]),
   `text_planes[]`, `marks[]`, `control_points[]`. Every field the proposal's LOC_NYC_042 example has, plus grade and
   control points.
2. Create `backlot/catalog.py` — a SQLite catalog with a YAML mirror in git; `add`, `find` (structured filters),
   `provenance`, `used_in`. Embeddings are a column reserved now and filled later.
3. Convert `build_backlot.py` to emit **USD**: one `.usda` per asset (`CityHall.usda`, `RallyStage.usda`,
   `Bodega.usda` …), a `NewHarnomy_square.usda` that references them, **variant sets** for set states
   (`build: joists | half_decked | beam_seated | swept | finished | feast`) and for weather/time, and a
   `cameras.usda` layer with one camera prim per shot. The `.blend` becomes an export, not the truth.
4. Create `backlot/readback.py` — harvests transforms from a `.blend` Brad has edited by hand into the USD layer,
   so a building moved in the GUI is a diff in git, not a divergence.
5. Register every existing NH asset in the catalog with provenance (method: procedural; creator: builder script;
   used_in: NH-S901) — the corpus starts with what exists.
6. Extend the shot-spec schema to v2: `camera` (prim path), `set_state`, `weather`, `dressing`, `invariants[]`,
   `conditioning[]`, `budget_usd`; raise the render cap; migrate the twelve NH-S901 specs.
7. Add `backlot/cost_preflight.py` — every generating entry point prints its cost and refuses past a per-shot cap or
   below a balance floor; Veo's observed rate replaces the assumed one.

**Check:** the square rebuilds from USD alone; `cameras.json` and `control_points.json` regenerate byte-identical
from the USD cameras layer; all twelve specs validate; `catalog find kind=set production=NH` lists the stage.

### Phase 1 — Conditioning passes and structure-locked keyframes (the box, ~$20 GPU + ~$5 test spend)

8. Create `backlot/conditioning/render_passes.py` — headless Blender from the USD stage per shot camera: clay,
   depth (EXR, normalised), normal, segmentation-ID (flat colour per class: deck, post, beam, chair, building,
   paving, text plane), line-art; plus projected control points and text-plane quads.
9. Install on the ComfyUI box FLUX.1-dev, a Union ControlNet (depth + canny), an IP-Adapter for look from the LOCKED
   plates; pin versions in `backlot/generation/MODELS.md`.
10. Create `backlot/generation/generate_keyframe.py` — shot spec → passes → prompt *built from the spec by the
    linter, not typed* → FLUX + depth ControlNet at high weight + IP-Adapter → 2K key + sidecar.
11. Fold the six incident scripts into `backlot/generation/edit_keyframe.py` with named single-reference presets
    (`harvest`, `overcast_drizzle`, `strip`, `letter_from_plate`) — nano-banana kept for what it is safe for.
12. Validate on SH003, SH006, SH009: five takes each through the ControlNet path, gate all fifteen.

**Check:** first-take gate pass rate ≥ 90% over the fifteen (the teaser ran at roughly 40%). If the look reads CG,
the tier becomes ControlNet-for-structure → single-reference restyle, gated again after.

### Phase 2 — The gate becomes the QA station (~2 sessions, no spend)

13. Add segmentation IoU: deck, posts, beam masked in the seg pass vs. the same classes in the key (a
    small open-vocabulary segmenter on the box); a low deck IoU FAILs — this is the check that catches a *turned*
    stage, which edge heuristics could not (NH-USA-052).
14. Add OCR on every text plane: the banner must read the spec's string exactly; otherwise `letter_from_plate`
    runs automatically.
15. Add a judge: the comparison sheet plus the spec's invariants → one verdict per invariant, advisory until its
    false-positive rate is measured, then blocking per invariant.
16. Gate every entry point: no motion render without a PASS; no key installed without its sheet beside it.
17. Create `backlot/provenance/ledger.py` — one row per generation with the USD stage hash, camera prim, state,
    prompt, seed, model, cost; back-fill NH-S901 from the sidecars; add `reproduce <key>`.

**Check:** the eleven archived bad takes from v3–v10 all FAIL; every installed key PASSes. That regression suite
costs nothing and runs on every change to the gate.

### Phase 3 — The Backlot Agent, and Unreal on evidence (~3 sessions)

18. Create `backlot/agent/resolve_scene.py` — input: a libretto scene (or the storyboard's shot row); output: a
    structured request — location, set, state, weather, time, props, marks, camera — resolved against the catalog:
    reuse / configure variant / **queue a build**. It never emits a prompt.
19. Create `backlot/agent/build_queue.py` — the missing-asset queue, ranked by the findings ledger and by how
    often an asset was re-generated (the self-expanding loop, §10, as a table rather than a hope).
20. Populate the catalog to the next sequence's needs only: north row to shot-ready, the university gate, the three
    interiors (Pengold's office with its windows on the drum wall, PILF, LYSTERIA) as USD sets registered to the
    world, lighting states as data, the Feast state of the square, character mannequins on marks.
21. Trial Unreal on one sequence with a camera move: import the USD stage, place the shot cameras, render depth and
    seg for a move, condition Wan on the box with them. Adopt if it beats headless Blender on iteration speed for
    that work; otherwise it stays optional.

**Check:** the agent takes one NH scene from the libretto and returns a resolved spec whose every asset either exists
in the catalog or is a queued build with a grade; a stage composes from that spec and its passes render without a
hand edit.

### Phase 4 — Motion and rules (~2 sessions)

22. Veo first/last-frame: render both ends through the ControlNet path, gate both before the clip is bought.
23. Depth-video conditioning on the box (Wan 2.2 + depth) as the previz tier for moving cameras.
24. Create `backlot/rules/prompt_lint.py` from the findings: refuses negations, contradictions with the set contract,
    a second reference on a fixed-camera shot, "platform/stage" ambiguity when both are in frame — each refusal
    cites its finding.
25. Create `backlot/rules/camera_lint.py`: exteriors square to the facade unless the spec overrides; a camera that
    cannot contain the invariants it asserts is refused.

**Check:** the v10 SH009 prompt is refused citing NH-USA-051; the v8 SH009 camera is refused citing NH-USA-047.

### Phase 5 — Operate

26. One status page per production: first-take pass rate, $ per accepted key, retakes per shot, continuity defects
    found after delivery (target zero; each one becomes a finding and then a rule).
27. `batch_render` calls the backlot path (`spec → stage → passes → generate → gate → render → ledger → assemble`);
    the incident scripts are retired.
28. `backlot/README.md`: how to add a set, a state, a camera, a rule; the grades; the provenance contract.

---

## 4. The MVP, in this studio's terms

The proposal's milestone, re-aimed at New Harnomy:

> A Backlot Agent takes one scene of the libretto, resolves every required asset from the New Harnomy catalog
> (reusing, configuring a variant, or queuing a build), composes a USD stage in the right state and weather, renders
> conditioning passes for each shot camera, generates keyframes that pass the gate on the first take nine times in
> ten, and hands over a shot list with gated keys ready to render — with every asset's provenance and every
> generation's lineage in the ledger.

Film one (the teaser) built 100% of its world by hand. The next NH sequence should build under half. The Feast
should build almost none. That is the moat the proposal describes, measured.

## 5. Risks, plainly

- **Over-constraint looks CG** — mitigated in Phase 1 by structure-then-restyle, both gated.
- **Video is unconstrained mid-clip** — locked-off cameras and short clips until a video ControlNet earns its cost.
- **USD in Blender is good, not perfect** — variant sets and some material round-trips need care; the builder owns
  the USD, Blender consumes it, which sidesteps most of it.
- **Segmentation reliability** — measured on the regression suite before it blocks anything.
- **Scope creep toward the generic backlot** — the catalog schema is general; the population is New Harnomy only,
  until a second production pulls something else in.
- **Time** — Phases 0–2 are about two weeks of sessions; they pay back on the first sequence that ships without a
  continuity note.

## 6. Decisions needed

- Confirm USD as the canonical format (it changes Phase 0's first task).
- Confirm Unreal deferred to Phase 3 on evidence, not adopted up front.
- Which interior first: Pengold's office (the POV contract) is my recommendation.
- Run Phase 1 on the box before the next teaser note — every note since v5 has been a continuity note.
