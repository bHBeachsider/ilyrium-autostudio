# Soul-ID plan — Higgsfield character lock for the four principals

> Stage 3 (character design + anchors). Complements `CASTING_CANON.md`, `anchors/` (--cref stills) and
> `loras/` (ComfyUI LoRAs). A **Soul Character** is Higgsfield's trained identity model: train once from
> 5–20 photos → a `reference_id` → pass `--custom_reference_id` (alias `--soul-id`) to `soul_cinematic` /
> `text2image_soul_v2` for identity-faithful stills, which then seed image-to-video. Adapter:
> `apps/auto-studio/media/higgsfield_renderer.py` (`soul_create`, `register_soul`, `resolve_soul_id`).

## Prerequisite (blocking)
Soul training requires a **paid Higgsfield plan (Basic+)**. As of 2026-08-15 the studio workspace
(`bupham@ilyrium.io`, "Private") is on the **free plan with 10 credits** and `higgsfield soul-id list` is
empty. Until upgraded: use the ComfyUI LoRA path (`loras/`) + `--cref` anchors; keep this plan ready.

## Order of operations (per principal — do not skip the anchor)
1. **Lock the hero portrait first** (`anchors/<key>.png`) from the bible's 🔒 LOCKED VISUAL DESCRIPTOR
   (kernel look; 21:9 or 3:2; no likeness to any real person — LEGAL GATE). Approve it. Everything downstream
   derives from this file, exactly as Higgsfield's Brand Lock derives from one authoritative asset.
2. **Build the training set from the anchor, not from the wild**: 8–12 renders of the SAME face — front, ¾ left,
   ¾ right, slight up/down; three lighting setups (tungsten key, cool dawn, podium/gold); neutral / speaking /
   listening expressions; head-shot, head-and-shoulders, ¾ body. Single person per image, eyes visible, no
   glasses for Summer/Pengold/Valencia (Dick keeps his wire-frames — they are canon; include a few frames without
   so the model learns the face), ≥1024×1024, no heavy filters. (Higgsfield photo-guide rules.)
   Tools: `higgsfield:nano_banana_pro` reference edits from the anchor (14 refs), or ComfyUI img2img from the anchor.
3. **Train**: `higgsfield soul-id create --name <key> --soul-cinematic --image ...` (cinematic variant for
   film work) → `soul-id wait`. Adapter: `soul_create(name, images, cinematic=True)`.
4. **Register**: `03_design/characters/soul_ids.json` → `{"souls": {"<key>": {"soul_id": "...", "variant": "soul-cinematic", ...}}}`
   (adapter `register_soul(project_dir, key, soul_id)`); `resolve_soul_id(key, project_dir)` is what the render
   path uses. One Soul per character key; retrain = new revision (record the old id in notes).
5. **Verify** with three cheap stills (0.12 cr each): a close-up, a medium in a new setting, a 21:9 wide — QA
   against the anchor (face-similarity + the QA checklist). Two identical failures → fix the training set, not
   the prompt.

## Per-principal notes
| Key | Variant | Training-set notes | First verification still |
|---|---|---|---|
| `pengold` | soul-cinematic | greying temples must survive every angle; include the "settled, smallest smile" expression once | seated at the dawn desk, reading (NH-S101 SH005 keyframe) |
| `summer` | soul-cinematic | hair drawn back in every frame; composure; also feeds the Socialist-Realist portrait (style-transfer from the Soul still, keep geometry) | frozen beneath the portrait (NH-S348 SH007) |
| `dick` | soul-cinematic | with AND without wire-frames; grown-out hair; earnest open expression + one "at the threshold" look | in chains at the stage-left threshold (NH-S348 SH005) |
| `valencia` | soul-cinematic | flat, truthful light in most frames (documentary register); no makeup performance | one step into her own light, closed book (NH-S348 SH009) |
| `philip`, `bildersatz` | deferred | only if staged / if the 1996 portrait is used | — |

## Canon reconciliation gate — CLEARED 2026-08-15
Reading A applied: `casting_canon` = the cast face (European for Summer/Dick, American for Pengold); the bibles = the
v11 character. Souls/anchors derive from the casting_canon face. (A Soul encodes the face; if the casting ever
changes, retrain — the Higgsfield "changing a foundation slot invalidates dependents" rule applies to identity assets.)
