# backlot — One World Set (Phases 0–3)

The studio's world as an input, not a reference. Everything a shot is generated from and verified against lives in
one OpenUSD stage per production; cameras, control points and set states are data in that stage; the `.blend` is an
export for looking and hand-editing, never the truth. See `docs/ows/OWS_PLATFORM_PLAN.md`.

```
backlot/
  world/nh/geometry.py      the New Harnomy assets, authored in Blender with asset + state tags
  world/nh/cameras.py       one camera per shot, as data (no bpy)
  usd/export_assets.py      Blender -> usd/nh/assets/<Asset>/geo[_state].usda
  usd/compose.py            -> usd/nh/assets/<Asset>/<Asset>.usda (variantSet "build"), cameras.usda, NewHarnomy_square.usda
  usd/derive.py             stage -> derived/cameras.json + control_points.json (what the gate and passes consume)
  usd/render_clay.py        render a shot camera's clay FROM THE STAGE at its set state
  usd/render_passes.py      conditioning passes per shot: clay, lineart, seg (class colours), depth (16-bit + EXR), normal
  generation/generate_keyframe.py   depth pass -> FLUX.1-dev + ControlNet Union Pro (depth) on the NH box via ComfyUI
  generation/keyframe_from_world.json, prompts/<SEQ>.json, MODELS.md   the workflow, the words, the licences
  generation/validate_first_take.py gate every take, report first-take pass rate against the >=90% target
  generation/edit_keyframe.py       the paid edit path (nano-banana-pro) with the incident rules as presets
  gate/run_gate.py          the QA station: geometry (blocking) + seg (advisory) + text (blocking, --autoletter) + judge
  gate/check_keyframe_geometry.py   projected posts, deck line, chair rows, clay|key sheet
  gate/seg_box.py           Grounding DINO + SAM on the box: per-class masks of the key in the seg pass's colours
  gate/seg_iou.py           key mask vs seg pass: platform extent + axis (BLOCKING with a box mask; CLIPSeg fallback advisory)
  gate/ocr_text.py, gate/letter_text_plane.py   every text plane must read the spec; auto-letter from the world's quad
  gate/judge.py             a vision model rules per invariant (ADVISORY until measured per invariant)
  gate/require.py, gate/install_key.py          no install, no motion render, without a fresh PASS receipt
  gate/regression.py, gate/regression_manifest.json   the gate's own test against the eye
  provenance/ledger.py      one row per generation (jsonl + sqlite); backfill, show, reproduce
  agent/resolve_scene.py    scene card -> resolved request against the catalog (reuse / variant / BUILD); never a prompt
  agent/stage_scene.py      resolved request -> stage in that state -> passes for the suggested camera
  agent/build_queue.py      the missing-asset table, ranked by scene demand, ledger regenerations, findings
  world/nh/lighting.yaml    lighting states as data (office_dawn, square_overcast_drizzle, feast_stage, ...)
  open_in_blender.py        stage -> nh_backlot.blend (asset roots are Empties under World)
  readback.py               edited .blend -> usd/nh/overrides/readback.usda (strongest sublayer)
  catalog.py, catalog/nh.yaml, schema/asset.yaml     the catalog: YAML truth, SQLite index, provenance per asset
  cost_preflight.py, budget.yaml                     no generation without a price and a budget
  schema/shot_spec_v2.patch.py, schema/migrate_nh_s901.py   the 'backlot' block on shot specs
```

## The loop

```
edit geometry.py / cameras.py          (or move an asset root in Blender and run readback.py)
python -m backlot.usd.export_assets    # Blender authors, exports per asset per state
python -m backlot.usd.compose          # assets, variants, cameras, stage
python -m backlot.usd.derive           # cameras.json + control_points.json for the gate
python -m backlot.usd.render_clay SH009
python -m backlot.usd.render_passes SH003 SH006 SH009      # -> usd/nh/passes/<SHOT>/{clay,lineart,seg,depth,normal}.png
python -m backlot.catalog rebuild
# on the NH box (ComfyUI at 127.0.0.1:8188): 
python backlot/generation/generate_keyframe.py SH003 SH006 SH009 --takes 5 --seed 2000
~/ComfyUI/venv/bin/python backlot/generation/validate_first_take.py --report report.json
```

## Contracts

- **Origin**: centre of City Hall's portico semicircle at pavement level; +X along the facade to the right, +Y into
  the square, +Z up. Assets are authored in world space for this production; the reference prim that places each
  one carries identity, which `readback.py` overrides.
- **States**: `/World{build=...}` selects one state on every stateful asset at once (`joists`, `half_decked`,
  `beam_seated`, `swept`, `finished`, `feast`); the build-site lumber deactivates when the stage is finished.
  `/World{weather=...}` is a token the lighting and generation layers read.
- **Cameras**: `/World/Cameras/<SHOT>`, Blender/USD convention (-Z forward, +Y up), `backlot:resolution`,
  `backlot:set_state`, `backlot:role` (shot | survey). Exterior shot cameras look square at the facade (NH-USA-047).
- **Control points** live inside the asset that owns them (`/RallyStage/ControlPoints/...`) so an override on the
  asset moves them; `derive.py` transforms them to world space for the gate.
- **Grades**: `conditioning` (default: greybox at scale, seg ids, text planes) or `hero` (only where close-ups or
  text demand it).
- **Derived files are never edited by hand.** `derived/cameras.json` and `derived/control_points.json` are outputs.

## Phase 0 checks (all passing 2026-09-08)

- the square rebuilds from USD alone: `render_clay.py SH009` matches the old builder's frame
- `derive.py` regenerates `cameras.json` and `control_points.json` byte-identical to the builder's for all seven shot cameras
- a hand edit round-trips: move `RallyStage` in the .blend → `readback.py` → recompose → `post_L` moves with it
- `catalog find kind=set` lists the stage; `used_in NH-S901` lists the six assets the teaser used
- `cost_preflight` refuses past the per-shot cap and below the floor

## Phase 1 result (2026-09-08, NH box, FLUX.1-dev fp8 + ControlNet Union Pro 2.0 depth, 1344x768, 28 steps, cn 0.7/0.8)

15 takes (5 seeds x SH003/SH006/SH009), no retries: **13/15 = 87% first-take gate pass** (target >= 90%: NOT MET).
SH003 5/5, SH009 5/5, SH006 3/5. `generation/reports/phase1_first_take_2026-09-08.json` has every gate line.

What the two SH006 fails are: the gate's edge detector could not find the far-right post - a thin, low-contrast
upright 40 m from the window camera - and locked onto a stronger vertical (a plaza axis line) 17% away. In both
frames the post IS drawn where the blockout puts it (see `reports/phase1_review_SH006_fails.png`). Layout held in
15/15 by eye; the misses are the verifier's, which is why Phase 2 replaces edge heuristics with seg-mask IoU against
the seg pass.

What the depth pass does not carry: the `half_decked` state read as a pergola/footbridge from the high POV in
SH006 (joists overhead instead of underfoot) - depth alone is ambiguous about open framing seen from above; feed the
seg pass as a second control (or normal) for build states. Chairs in SH009 come out blocky because the blockout's
chairs are boxes - a `hero`-grade chair asset fixes it at the source. Every take took ~50 s warm; the 30 GB of system
RAM (not the 24 GB A10G) is the limit - ComfyUI peaked at 24.4 GB and was OOM-killed once; a 10 GB swapfile is now on.

## Phase 1b result (2026-09-08, same box; depth 0.7/0.8 + lineart-as-edge 0.45/0.6; chair-shaped chairs)

15 takes, seeds 3000-3004, no retries: **14/15 = 93% first-take gate pass - target MET.** SH003 4/5, SH006 5/5,
SH009 5/5 (`generation/reports/phase1b_first_take_2026-09-08.json`, sheets in `phase1b_review.png`).

The two source fixes did what they were meant to: SH006's half-decked stage now reads as a platform with an open joist
grid underfoot (no pergola in any take) and SH009's chairs are chairs in one row in all five. The one FAIL (SH003
3004) is the same detector class as before - the post is drawn on its line, the edge finder locked onto a stronger
vertical - which Phase 2 addresses.

Cost of the edge control, stated plainly: at 0.45 the frames are more literal to the blockout - flatter facades,
blank window panels, less dressing (fewer sheaves, pumpkins, garlands; SH003's workmen dropped out in two takes), and
the banner reads as a plain purple rectangle. Layout went up; dress went down. Start Phase 2's judge on exactly this
trade-off, and try edge 0.3 / end 0.4, or edge only for build states, before touching the prompts.

## Phase 2 — the gate becomes the QA station (2026-09-08)

Built: `run_gate.py` (one verdict, one receipt `<key>_gate.json`, one sheet), text planes as world data (the banner
quad and its two lines live in the Banner asset's ControlPoints and flow through USD to `derived/control_points.json`),
`ocr_text.py` + `letter_text_plane.py --ink` (a world-generated key's blank banner is lettered from the projected quad
and re-read: similarity 0.91/0.97 on SH009), `require.py`/`install_key.py` (receipt is per sha256, not per filename),
`judge.py` (advisory, per-invariant), and `provenance/ledger.py` (87 rows back-filled: 30 takes with full
provenance, the installed v11 keys as `edit` rows that say plainly they have no sidecar).

Measured, not assumed (`gate/regression.py` on 30 takes, 28 correct by eye, 2 wrong):

| check | false-reject on good frames | misses on bad frames | status |
|---|---|---|---|
| geometry (edge posts) | 2/28 = 7% | 1/2 (the pergola: posts were in place) | blocking (as before) — 7% is above the 5% rule; the two rejects are the thin-far-post miss |
| seg (CLIPSeg extent/axis) | 5/28 = 18% | 2/2 | advisory only — worse than the eye on this set; not fit to block |

The honest conclusion: CLIPSeg at 352 px cannot see a 1%-of-frame stage well enough; the next verifier is a real
segmenter on the box (Grounded-SAM / SAM2 on the A10G, Phase 3) or a post-column check that reads the seg pass's
post pixels directly. Until then geometry stays the blocking check, its two known false rejects are documented, and
the sheet + judge carry the rest. The plan's Phase 2 check ("the archived bad takes all FAIL") is not yet met: only
the two Phase 1a bad takes are in the suite; the v3–v7 archive needs its pre-frontal cameras recovered first.

### Judge calibration (12 sheets, claude-sonnet-4-5, plain clay|key sheets, ~$0.25 on the studio key)

First lesson, before any number: the judge must see a PLAIN sheet. Shown the gate's annotated sheet it counted the
green post markers as uprights ("two tall green uprights"). `run_gate.py --judge` now builds `<key>_sheet_plain.png`.

Per invariant against the eye (10 good frames, 2 bad — the pergola and the footbridge):

| invariant | false "violated" on good frames | caught the bad frames | verdict |
|---|---|---|---|
| stage horizontal, parallel to the facade, not turned | 0/10 | 2/2 | promote to blocking after a 30-sheet sample (the only check so far that saw the pergola) |
| exactly two uprights, one at each end | 6/10 | 2/2 | not promotable as worded — the model counts chairs, steps and columns as "uprights"; reword to "tall posts rising above the crossbeam height" and re-measure |
| no crossbeam (SH003/SH006) | 1–2/6 | 2/2 | re-measure after the reword |
| flat grey overcast, wet paving | 1/10 | — | look note, not layout; keep advisory |
| workmen / single workman present | 0 false — the frames really lack them | — | true findings: the Phase 1b edge control dropped the people; feed it back to the generator, not the gate |
| open joists / half-decked / one row of chairs | 1/10 (SH006 3004 "half decked" ambiguous by eye too) | — | keep advisory |

Raw verdicts: `generation/reports/judge_calibration_2026-09-08/`. Nothing in the judge blocks yet (`BLOCKING = set()`).

### Seg verifier fixed (2026-09-08, box session 3, ~20 min GPU)

`gate/seg_box.py` runs Grounding DINO (tiny) + SAM (vit-base) on the A10G: 0.4 s a frame, masks per class in the seg
pass's colours, so `seg_iou.py` compares mask to mask at full resolution with no model in the loop. Four things had to
be learned on the 30-take suite before it agreed with the eye, each recorded in the code:

1. the detector boxes the whole City Hall, or the whole plaza, as "a wooden platform" — boxes are kept only if 70%
   inside the world's band and under 3× the world's extent;
2. a 5 m post stretches that band up to the portico — flat classes (deck, beam, chairs, steps, podium) get the
   PLATFORM band, posts the full one;
3. the detector labels a platform's front edge "beam" and a beam "platform" — deck and beam are one pool on both sides;
4. a tall post mask dominates a principal-axis fit and reads as "turned" — extent and axis are asked of the platform
   without the posts; posts get their own column check.

Result on the suite: **0/28 false rejects** (CLIPSeg: 5/28), so the seg check is now BLOCKING on extent (box IoU
< 0.25) and axis (> 15°) when a box mask exists, advisory on the CLIPSeg fallback. Stated caveat: the two bad takes
in the suite are SEMANTIC (a pergola and a footbridge whose footprint is exactly where the world puts it) — no 2D
extent check can see a roof vs a floor; the judge caught both. The suite has no layout-bad negative yet; the v9
turned-stage key joins it when its camera is recovered. `gate_regression_segbox_2026-09-08.json` has every row.

## Phase 3 — the Backlot Agent, and the world grows to the next sequence (2026-09-08)

The next sequence is NH-S101, the opening: Pengold's office at dawn. The office now exists as a set registered to
the world at its true position — the half-disc behind the colonnade plus six metres cut into the main block, floor
5.4 m, the three French windows shared with `CityHall` — so the office wide (`S101_SH004`) sees the columns a metre
beyond the glass and the north row across the square, and SH006's window POV looks out of the same room: the POV
contract holds by construction, not by prompt. Also registered: `PILFInterior`, `LysteriaInterior` (blockout),
`Mannequins` (neutral figures on marks, one state per scene family: office_dawn, feast, build), marks as control
points (`desk_chair`, `window_centre`, `door`; `podium`, `beneath_portrait`, `stage_left_threshold`, `upstage_right`),
state FAMILIES on `/World` (`build`, `office`, `people`, `weather` — each drives only its own assets), and lighting
states as data. Depth passes are now inverse-depth normalised to the frame's own 1st–99th percentile range (a fixed
linear near/far made every interior pass near-white); `--depth-mode linear` keeps the Phase 1b convention.

The agent: `resolve_scene.py` reads the 17 scene cards of `02_script/scenes.json` and resolves each — every office
and Feast scene lands on its set by alias (0.95–0.99), every named prop is found in the blockout (desk, lamp, cup,
newspaper, the mauve books, the portrait; podium, chairs, steps, banner), every character gets a mark, and the three
theatre scenes (auditorium, proscenium, vomitoria) come back as BUILD requests because no such set exists — which is
the correct answer. `stage_scene.py` refuses a scene with anything queued, otherwise sets the variants and renders
the passes; `build_queue.py` ranks what is missing (top of the list today: a hero-grade RallyStage — 62 generations
against it in the ledger — then the theatre). The agent emits no prompt anywhere.

**Phase 3 check, honestly:** the agent takes a libretto scene and returns a resolved spec whose every asset exists or
is queued (met, 17/17), composes the stage in the right state and renders passes (met, scenes 4/5/7). "Generates keys
that pass the gate nine times in ten" is NOT yet measured for the office: it needs one more box session (10 takes of
S101_SH004/005 through the same workflow), and that session must also re-validate SH003/006/009 under inverse depth,
since the 93% was measured under linear depth.

**Unreal, on evidence (task 21):** deferred as decided. The criterion stays written down: adopt Unreal for a
sequence with a camera move only if it beats headless Blender on iteration speed for depth+seg passes of a move
(Blender today: ~15 s per still, no move path yet). Until a moving-camera sequence is scheduled there is no evidence
to collect.

### Phase 3 check, measured (2026-09-08, box session 4, ~40 min GPU, 45 takes)

**Office keys nine in ten: NOT MET — and the reason is exact.** From the world, the room is right in every take:
10/10 wides have the three windows with the columns beyond, the desk, the lamp, the credenza with the books
(`phase3_office_SH005_std.png`). But the seated man is absent in 10/10 at Phase 1b control strengths: the box-and-
sphere mannequin in the depth and edge passes is drawn literally — a bust on the credenza. At softer control (edge
0.2, depth 0.6) the drapes and window light appear and 2/5 mediums have a real man reading the paper; 3/5 still draw
the box-stack. The verifier saw it too: the seg check's interior structure includes the pass's person, and the
key's missing person collapsed the extent (SH005 seg 2/10) — a true finding, not a false reject.

Fix at the source, two options, both queued: (a) mannequins condition nothing until they are human-shaped —
`stage_scene.py` now renders passes with `people=none` by default, so the set is held by the world and the person is
the generation layer's, judged against the mark; (b) a hero-grade human mannequin (build queue). (a) is a one-line
change already in; its 10-take measurement is the next box session.

**Exteriors under inverse depth: 12/15 (80%) vs 14/15 (93%) under linear.** SH003 5/5, SH009 5/5 (dressier than 1b),
SH006 2/5 — inverse depth compresses the far uprights out of the signal and they vanish; three real misses. So depth
normalisation is now per camera (`cameras.py DEPTH_MODE`): linear for exteriors, inverse for interiors.

Also learned: the geometry check expects the stage posts through the office windows (they project into frame) —
interiors need the post check scoped to exteriors; recorded, not yet done.

### The actor and the dressing layer, measured (2026-09-09, box session 5, ~40 min GPU, 35 takes)

Two arms for the office medium, ten takes each, same softer control (edge 0.2, depth 0.6):

| arm | the room | a figure on the mark (desk chair, reading) | a real man | notes |
|---|---|---|---|---|
| A — passes condition the SET only, the man left to the prompt | 10/10 | 1/10 | 4/10 | best dress so far (drapes, windows, columns through the glass); the man wanders — standing, or seated by the window |
| B — human-shaped mannequin in the passes | 10/10 | 10/10 | 4/10 | posture and mark held every time; the SPHERE head is drawn as a globe, helmet or lamp in 6/10 |

Neither reaches nine in ten, and the split is informative: the world can hold the mark and the posture (B), and the
prompt can make a man (A); what fails is the one primitive that does not look like its subject. Next fix at the
source: an ovoid head with a hair cap and a neck, and a person-region FADE in the depth/edge control (the body's
silhouette guides, it does not dictate) — then ten more takes. `phase3b_SH005_A_set_only.png`, `_B_mannequin.png`.

Dressing as data works: pumpkins and hay bales placed in the `finished` state appear along the stage front in 5/5
SH009 takes (`phase3b_SH009_dressing.png`; near-recall 14–55%, advisory threshold 0.30 until calibrated). The
sheaves at the columns are faint and the garland on the beam is not drawn — thin things at distance again, the same
lesson as SH006's posts. Interior seg extent is advisory until calibrated (35 office takes were noisy on it).
