# OWS — One World Set
### A platform plan for Ilyrium Studios, seeded by NEW HARNOMY, U.S.A. / NH-S901

*Drafted 2026-09-08 from the v1–v11 production record of "The Scaffold" teaser. Status: proposal.*

**Reading of the brief.** "OWS" is taken here as **One World Set**: a single, versioned, code-defined 3D world for each
production, from which every generated frame is derived and against which every frame is verified before money is
spent on it. The seed is what the teaser forced into existence in the last four days — the City Hall blockout, the
per-shot cameras, the backlot, the geometry gate, the findings ledger — and this plan is that seed made into a
platform rather than a set of rescues. If "OWS" meant something else, the evaluation below still stands; the plan
would need re-aiming.

---

## 1. Evaluation of the seed

### 1.1 What the teaser proved

The teaser went through eleven cuts. Roughly a third of the generations in that run were retakes for **continuity**
failures rather than taste: the truss turning into a lattice, the stage standing at the foot of the building in one
shot and thirty metres out in the next, the stage skewed, the stage turned perpendicular, an upright mid-span, two
chair rows, a build state jumping ahead, a second reference stealing the camera, a cleanup edit deleting the wrong
platform. Each was fixed; each cost a generation, a render, and a review round. None was caught by the pipeline.

Four things did work, and they are the seed:

- **A code-defined world with one origin.** `build_city_hall.py` fitted to the LOCKED dusk plate by overlay put the
  stage at 32 m from the column line and settled the argument for every shot at once. `build_backlot.py` extends it
  to the town (shakedown row, both churches, PILF, the axis street, the university). The sight line from the
  university gate to the portico now exists as geometry.
- **Cameras as data.** `cameras.json` carries one camera per shot; the rule that every exterior camera looks square
  at the facade came out of a real failure (NH-USA-047) and is now a coordinate, not a note.
- **A gate that projects the world into the frame.** `check_keyframe_geometry.py` refused the mid-span upright at
  35% of frame width and passes good keys at 1–2%. Its limits are documented honestly (NH-USA-052): posts are
  blocking, orientation and counts are advisory, and it writes a blockout-beside-keyframe sheet for the human look.
- **A findings ledger.** NH-USA-016 through 052 is an institutional memory of how these models fail. It is the most
  valuable artefact of the run and currently the least enforced.

### 1.2 What is structurally weak

1. **Generation is unconstrained.** Every keyframe is composed independently by an image model. Prose is a
   suggestion; a reference image is a stronger suggestion that can be outvoted (NH-USA-043); a clay render is a
   picture the model may or may not honour. The world exists, but nothing forces a frame to obey it.
2. **Verification is by eye.** The gate proves one thing (post columns). Orientation, build state, chair rows,
   dressing, and text are checked by looking — by me, then by Brad, after the render has been paid for.
3. **Set state is implicit.** The build ladder (open joists → half-decked → beam seated → swept → chairs out) lives
   in prompts and in memory. The blockout knows two states. Shot specs name none.
4. **Text is fought every time.** Models scramble any text they touch (NH-USA-033/040/042). The fix — re-lettering
   in pixels from the plate — works, but the banner's box is found by hand for each new camera.
5. **The tooling is a pile of incident scripts.** `fal_keyframes.py`, `fal_dress_harvest.py`, `fal_weather.py`,
   `fal_rekey_frontal.py`, `fal_v9_cleanup.py`, `fal_rekey_sh006.py` — six entry points, prompts hand-edited in
   place, outputs installed by hand. Reproducible only by reading the storyboard's production record.
6. **Renders live outside the ledger.** fal generations are not in batch_render's provenance chain (NH-USA-038);
   sidecars exist but nothing consumes them.
7. **Cost is spent before checking.** Veo billed above the estimated rate and the balance ran dry mid-pass; every
   continuity retake was a paid render of a still that could have been refused for free.
8. **Interiors are not in the world.** Pengold's office is contracted to the colonnade by prose (SET_BIBLE §4), not
   by a window registered in world coordinates.
9. **The GUI and the code do not talk.** Brad works in Blender by hand; the builder is the source of truth; nothing
   carries a hand-moved building back into the code.
10. **Prompts are written free-hand**, so the two failure modes that produced v10's perpendicular stage — a
    shot instruction contradicting a set rule, and a negation nominating the thing it forbids (NH-USA-051) — can
    recur in any prompt anyone writes.

The pattern behind all ten: **the world is a reference, not an input.** OWS is the change that makes it an input.

---

## 2. What OWS is

One World Set is seven layers, each with one job. Existing pieces are named where they already exist.

| Layer | Job | Exists today |
|---|---|---|
| **World** | The production's sets, props, marks, text planes, cameras and lights in one coordinate system, versioned in git, with named **states** (build ladder, dressing, weather, time of day) | `build_city_hall.py`, `build_backlot.py` (two states) |
| **Shot spec v2** | One JSON per shot naming camera, set state, action, dressing/weather preset, references, machine-checkable invariants, conditioning passes, budget | `ilyrium-shots/shots/*.json` (no camera, no state) |
| **Conditioning** | Headless Blender per shot → clay, depth, normal, segmentation-ID and line passes, projected control points, text-plane quads | clay only; `control_points.json` |
| **Generation** | One entry point per tier: structure-locked keyframe (ControlNet), camera-preserving edit (single-reference nano-banana), motion (Veo / Wan). Sidecars always. | six incident scripts; `fal_veo_render.py` |
| **Verification** | The gate, before any paid render: projected posts (blocking), deck/segmentation IoU against the seg pass, OCR of text planes, a VLM judge given the comparison sheet and the invariants; PASS / WARN / FAIL with a sheet | `check_keyframe_geometry.py` (posts only) |
| **Provenance** | World version hash + camera + state + prompt + seed + model + cost for every generation; back-filled into batch_render's ledger | sidecars, unconsumed |
| **Rules** | Findings turned into lint: prompts checked for negations and for contradictions with the set contract; cameras checked against the square-to-facade rule; costs checked against budget | `FINDINGS.md` (prose) |

The thing to hold onto: **the world is greybox and stays greybox.** It decides where things are and what state they
are in. The look still comes from the models, conditioned on the world, then verified against it.

---

## 3. The plan

Five phases. Each has a gate you can check without trusting anyone's summary. Numbers are for a solo operator with
Claude sessions; the box is the g5.2xlarge already provisioned.

### Phase 0 — Make the world the input (no spend, ~2 sessions)

1. Create `ows/world/layout.yaml` — every set, prop, text plane and camera as data (name, position, rotation,
   dimensions, state membership); `build_backlot.py` becomes a consumer of it rather than the place numbers live.
2. Add `ows/world/readback.py` — opens a `.blend` Brad has edited by hand and harvests object transforms back into
   `layout.yaml`, so a building moved in the GUI becomes a diff in git.
3. Add **set states** to the builder: `build.joists`, `build.half_decked`, `build.beam_seated`, `build.swept`,
   `finished`, `feast` — each a named subset of objects; the storyboard's build ladder becomes a list of state names.
4. Add **text planes**: the banner (and every future sign) as a tracked quad in the world, so `set_banner_text.py`
   receives its box or perspective quad from the camera projection instead of from a crop I measured by hand.
5. Extend the shot-spec schema (v2): `camera` (ref into cameras), `set_state`, `weather`, `dressing`, `invariants[]`,
   `conditioning[]`, `budget_usd`. Raise the 1280 render cap (NH-USA-038). Migrate NH-S901's twelve specs.
6. Add `ows/cost_preflight.py` — every generation entry point prints its cost and refuses to run past a per-shot
   budget or below a balance floor; Veo's *observed* rate replaces the assumed one.

**Gate:** rebuild the whole backlot from `layout.yaml`; `cameras.json` and `control_points.json` regenerate
byte-identical; all twelve NH-S901 specs validate under schema v2.

### Phase 1 — Structure-locked keyframes (the half-day on the box, ~$15 GPU + ~$5 test spend)

7. Install on the ComfyUI box: FLUX.1-dev, a Union ControlNet (depth + canny), an IP-Adapter for look transfer from
   the LOCKED plates. Document exact versions in `ows/generation/MODELS.md`.
8. Create `ows/conditioning/render_passes.py` — headless Blender per shot: clay, depth (EXR, normalised), normal,
   segmentation-ID (one flat colour per object class: deck, post, beam, chair, building, paving), line-art.
9. Create `ows/generation/keyframe_from_world.json` (ComfyUI workflow) and `ows/generation/generate_keyframe.py` —
   inputs: shot spec → passes → prompt built from the spec (see Phase 4's linter) → FLUX + depth ControlNet at
   high weight + IP-Adapter from the plate → 2K key + sidecar.
10. Keep nano-banana for what it is good at and safe for: **single-reference** dressing, weather and cleanup edits
    that preserve the camera (NH-USA-046). Wrap the six incident scripts into one `edit_keyframe.py` with named
    presets (`harvest`, `overcast_drizzle`, `strip_platform`, `letter_from_plate`).
11. Validate on the three shots that failed most (SH003, SH006, SH009): generate five takes each through the
    ControlNet path, run the gate on all fifteen.

**Gate:** first-take pass rate on the geometry gate ≥ 90% over those fifteen (the run just finished was roughly
40%). If the ControlNet look is too CG, the pipeline becomes ControlNet-for-structure → nano-banana single-reference
restyle, and the gate runs again on the restyled key.

### Phase 2 — Verification before spend (~2 sessions, no generation spend)

12. Add segmentation IoU to the gate: mask the deck, posts and beam in the seg pass; mask the same classes in the
    key (a small open-vocabulary segmenter on the box, or the seg pass warped by the key's depth); IoU below
    threshold is a FAIL for the deck footprint — this is the check that catches a *turned* stage, which edges cannot.
13. Add OCR of every text plane: the banner must read exactly the spec's string; anything else routes to
    `letter_from_plate` automatically.
14. Add a VLM judge step: the comparison sheet plus the invariant list → a structured verdict per invariant
    ("posts at both ends of the deck: yes/no", "one row of chairs: yes/no"). Advisory at first; promoted to blocking
    per invariant once its false-positive rate is measured.
15. Wire the gate into every entry point: no Veo call without a PASS, no install of a key without its sheet saved
    beside it.
16. Add `ows/provenance/ledger.py` — one row per generation with the world version hash; back-fill NH-S901 from
    the sidecars; expose "reproduce this key" as a command.

**Gate:** rerun the gate over every archived bad take from v3–v10 (there are eleven); it must FAIL all of them and
PASS every installed key. That is the regression suite, and it is free.

### Phase 3 — World coverage (modelling time; interiors ~1 session each)

17. Take the north row, the axis street and the university from blockout to shot-ready cameras (frontages, awning,
    gate, quad) — same fit-by-overlay method against whatever plate is locked first for each.
18. Build the interiors as sets registered to the world: Pengold's office with its three windows on the drum wall
    (the POV contract in SET_BIBLE §4 becomes geometry), the PILF storefront office, LYSTERIA.
19. Add lighting states as world data (first light, overcast drizzle, dusk, tungsten interior) so a relight is a
    state change with a matching pass, not a prompt.
20. Build the Feast state of the square (Act III): the same stage, the portrait rig, the chorus marks.
21. Place character marks in the world (where Pengold stands at the glass, where Dick exits stage-left) so blocking
    is data the specs can reference.

**Gate:** every location in `setting.md` has at least one shot-ready camera and a survey render in
`03_design/environments/backlot/`; the SET_BIBLE's §4 contract is expressed as world geometry with no prose-only rules.

### Phase 4 — Motion and rules (~2 sessions)

22. Camera paths from Blender for Veo's first/last-frame mode: render the last frame of a move through the same
    ControlNet path so both ends are gated before the clip is bought.
23. Depth-video conditioning on the box (Wan 2.2 + depth) for the previz tier: cheap moving-camera layout checks
    before any Veo spend, from the same world.
24. Create `ows/rules/prompt_lint.py` from the findings: flags negations ("no second row"), flags a shot instruction
    that contradicts the set contract (parallel + ends-here from a camera that cannot show both), flags a second
    reference image on a shot whose camera is fixed, flags "platform/stage" ambiguity when both exist in frame.
25. Create `ows/rules/camera_lint.py`: exterior cameras square to the facade unless the spec says otherwise; a
    camera whose view cannot contain the invariants it asserts is refused.
26. Turn FINDINGS.md rows into rule IDs the linters cite, so a refusal names the finding that taught it.

**Gate:** the v10 SH009 prompt, fed to the linter, is refused with NH-USA-051 cited. The v8 SH009 camera is refused
by the camera lint with NH-USA-047 cited.

### Phase 5 — Operate (ongoing)

27. A one-page status per production: first-take pass rate, $ per accepted key, retakes per shot, continuity
    defects found after delivery (target: zero — every one becomes a finding and a rule).
28. Budget guard with a hard floor and per-shot caps; balance read from fal before every pass.
29. Fold OWS into the studio pipeline (`specs → world → passes → generate → gate → render → ledger → assemble`) so
    `batch_render` calls it rather than the incident scripts; retire the incident scripts.
30. Write `ows/README.md` — the method, the invariants, and how to add a set, a state, a camera, a rule.

---

## 4. What changes for the next production

Today a new scene costs: write prompts, generate, look, notice, re-prompt, generate, render, look, notice, re-render.
Under OWS it costs: place the camera in the world, name the state, run `generate_keyframe`, read a gate report, render
once. The models still invent — that is what they are for — but they invent *inside* geometry, and what they invent is
checked against the world before it is paid for. The ledger of findings stops being a diary of what went wrong and
becomes the list of what the pipeline refuses to let go wrong again.

## 5. Risks, stated plainly

- **Over-constraint looks CG.** A high-weight depth ControlNet can flatten the photographic look the teaser has now.
  Mitigation is built into Phase 1: structure from ControlNet, look from a single-reference restyle, gate both.
- **Video is still unconstrained.** Nothing here locks geometry *during* a Veo clip; it locks the still it starts
  from and, in first/last-frame mode, the still it ends on. Locked-off cameras and short clips remain the rule until
  a video ControlNet is worth its cost.
- **Modelling time.** Every set is an evening of Blender. The backlot proves it is tractable; it is still time.
- **Segmentation reliability.** The IoU check depends on a segmenter reading a photograph the way the seg pass reads
  the model. It is measured before it is trusted (Phase 2's regression suite), like everything else here.
- **The GPU bill.** The box runs for Phase 1 and for previz; Phase 0's cost preflight applies to it too.

## 6. What I need from Brad

- Confirmation that OWS means what §0 says it means, or the document it was meant to mean.
- Which location after the square matters first (Phase 3 ordering).
- Whether the ControlNet session on the box runs before or after the next teaser note — my recommendation is
  before: every note since v5 has been a continuity note.
