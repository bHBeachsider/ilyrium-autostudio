# Stage 5 — Keyframes (the bridge to motion)

**Canonical home:** `04_preproduction/keyframes/`  ·  **Stage key:** `04_keyframes`

**Purpose.** One locked still per scene that becomes the first frame of the video shot.

**Produce (put your files in this folder):**
A keyframe still per scene card, --cref'd to the character anchor.

**Template / how to make it:**
Use the scene card's action + character anchor (--cref) + environment. In the console/agent, model 'keyframe' generates this and animates it.

**Gate (must pass before this stage is done):**
Continuity with the character anchor and the prior shot. Kernel look held.

**Ideation / refinement agent.** Via the Ilyrium MCP, call
`stage_ideate(project="<this project>", stage="04_keyframes", message="...")` to develop and refine this
stage in conversation — it works with the Style Kernel + casting canon in context, can read any
project file, and writes drafts back into this folder. (Autonomy A1: it proposes; you accept.)

---
*Production values are fixed by `../../style_kernel.json`; the continuity/legal gate is `../../08_qa/`
→ `../../QA_CHECKLIST.md`; consent/likeness releases live in `../../00_admin/rights_releases/`.
Creative content varies here — production values do not.*
