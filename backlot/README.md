# backlot — One World Set (Phase 0 + Phase 1)

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
  gate/check_keyframe_geometry.py   the geometry gate (projected posts, deck line, chair rows, clay|key sheet)
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
