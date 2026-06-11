# Stage 6 — Shots (render to video)

**Canonical home:** `05_production/shots/`  ·  **Stage key:** `05_shots`

**Purpose.** Animate keyframes / render each scene to a clip. Renders land in the auto-studio project.

**Produce (put your files in this folder):**
One rendered take per shot (engine per shot: grok/veo3/kling/comfyui/ue/keyframe).

**Template / how to make it:**
Video Master Prompt: SHOT_SIZE + SUBJECT + ACTION + CAMERA + LENS + LIGHTING + DURATION + on-camera dialogue(veo3/kling) + ambience + performance + kernel look. Continuity: first_frame=locked keyframe; restate character description each shot.

**Gate (must pass before this stage is done):**
Performance register held (no smile-at-camera, no winking). Dialogue native where on-camera.

**Ideation / refinement agent.** Via the Ilyrium MCP, call
`stage_ideate(project="<this project>", stage="05_shots", message="...")` to develop and refine this
stage in conversation — it works with the Style Kernel + casting canon in context, can read any
project file, and writes drafts back into this folder. (Autonomy A1: it proposes; you accept.)

---
*Production values are fixed by `../../style_kernel.json`; the continuity/legal gate is `../../08_qa/`
→ `../../QA_CHECKLIST.md`; consent/likeness releases live in `../../00_admin/rights_releases/`.
Creative content varies here — production values do not.*
