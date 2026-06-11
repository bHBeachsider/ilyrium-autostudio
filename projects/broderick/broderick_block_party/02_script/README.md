# Stage 2 — Screenwriting / Scene cards

**Canonical home:** `02_script/`  ·  **Stage key:** `01_script`

**Purpose.** Break the story into ordered scene cards — the unit the render pipeline consumes.

**Produce (put your files in this folder):**
scenes.json (array of scene cards)

**Template / how to make it:**
Scene card: {scene_number, location, characters[], action, visual_prompt, dialogue:[{speaker,line,delivery}], voiceover, performance, duration_target_s}.

**Gate (must pass before this stage is done):**
voiceover/dialogue lines contain ONLY spoken words (no stage directions). Every recurring character's physical description is restated in each scene that needs it.

**Ideation / refinement agent.** Via the Ilyrium MCP, call
`stage_ideate(project="<this project>", stage="01_script", message="...")` to develop and refine this
stage in conversation — it works with the Style Kernel + casting canon in context, can read any
project file, and writes drafts back into this folder. (Autonomy A1: it proposes; you accept.)

---
*Production values are fixed by `../../style_kernel.json`; the continuity/legal gate is `../../08_qa/`
→ `../../QA_CHECKLIST.md`; consent/likeness releases live in `../../00_admin/rights_releases/`.
Creative content varies here — production values do not.*
