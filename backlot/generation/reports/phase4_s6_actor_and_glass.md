# Box session 6 — the actor fix, and the gate on an interior with a glass wall

2026-09-10. NH box i-0169c83c3cef9d621 (A10G), ~23 minutes of generation, 20 takes, stopped after. FLUX.1-dev fp8 +
ControlNet Union Pro 2.0, interior "soft" control (depth 0.6/0.8, edge 0.2/0.4), inverse depth. Passes rendered from
the stage at commit e608698 + this session's changes; Grounding DINO + SAM masks on the box; gate run here.

## Numbers

| shot | takes | gate PASS | person present (seg) | person by eye |
|---|---|---|---|---|
| S101_SH004 (Pengold's office, actor fix) | 10 | **10/10** | 8/10 | **8/10 a man at the desk**; 6002 a bust-like shape, 6009 the globe |
| LYST_DESK (Summer behind the glass wall) | 5 | **5/5** | 5/5 | 5/5 a woman at the desk; glass wall + mullion in every take |
| LYST_BOARD (the boardroom) | 5 | **5/5** | 5/5 | 5/5 her at the head, him at the window |

Session 5 (B, human-shaped mannequin, sphere head): real man **4/10**, on the mark 10/10, the sphere drawn as a globe
6/10. This session, with an ovoid head, hair cap, jaw and a neck it sits on: **8/10**, the globe 1/10. The seg
near-recall flagged exactly the two failures the eye finds (6002: no person; 6009: 0%), so the advisory is now worth
reading as a score for this shot.

Two changes rode together in the office passes and are not separable in this measurement: the head, and the glass
now hidden from the depth/edge passes (the French windows used to be a surface at 8 m; now the rays go through to the
square at 90 m and the room gets ~73% of the inverse-depth range instead of all of it). Layout held 10/10 either way.

## What the session found

**The glass wall works as a wall for the eye and as nothing for the passes.** Clay sees through it; lineart, seg,
depth and normal do not see it. Every LYST_DESK take shows the wall (reflection, the mullion) with the room legible
behind it. Workbench's outline pass could not draw what was behind a transparent surface — the first LYST_DESK
lineart was blank — so glass is hidden there too (`render_passes.py`). Not a gate rule: a rendering fact.

**What is beyond the window is invented.** In all ten LYSTERIA takes the band shows a city that is not New Harnomy —
towers, trees, a Georgian house, a Victorian street. Never the plaza, never the scaffold. The gate cannot see this
(nothing checks window content) and the eye sees it at once. The reason is in the passes: inverse depth gives the
room the range and leaves 60 m of square as a few grey levels, and the lineart through the band is faint. The POV
contract holds in the geometry and not yet in the generation. The two window shots (`LYST_WINDOW`,
`LYST_BOARD_VIEW`, linear depth, the window the subject) were not in this session; that is the next measurement, and
the thing to try first is a window-only control (the band's crop of the SH-style exterior passes, linear) composited
into the interior depth.

**The OCR check was blind to occlusion and to scale.** The TWEEEDS banner is on City Hall's outside face; the office
is inside City Hall; the check projected the banner into every office key and failed 10/10 on text nobody can see.
Fixed: `ocr_text.py --passes` reads the shot's depth pass at the plane and calls it n/a when something is nearer
(`occluded (10 m in front of the plane at 16 m)`). And through LYSTERIA's band the banner is 252 px for 45 characters
— 3.9 px per letter; autoletter lettered it and tesseract read dashes. Nothing can make that legible: n/a under 9
px/character, not FAIL.

**The RallyStage geometry check is now scoped.** `INTERIOR_SHOTS` in cameras.py marks a shot as inside a room; the
check reports posts, deck line and chair band as n/a there and runs the comparative clay check only. Before, it looked
for two 3-pixel uprights through the band.

## Bookkeeping

- `render_clay` and `render_passes` share the glass rule; `render_clay --variants` added for stateful survey views.
- Four LYSTERIA cameras promoted to shot cameras (states, variants, depth mode) so the passes renderer sees them.
- Keys: `backlot/renders/keyframes_s6/{S101_SH004,LYST_DESK,LYST_BOARD}` with `_segkey` masks and `_gate.json`.
- Prompt book `generation/prompts/NH-LYST.json`; Summer's line is the locked casting descriptor verbatim.
- Box disk: 2.6 GB free of 232. 160 GB is ComfyUI models, 18 GB a Qwen GGUF, 10 GB swap — nothing I should clear.
