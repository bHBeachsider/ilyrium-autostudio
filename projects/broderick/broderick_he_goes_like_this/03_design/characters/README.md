# Stage 3 — Character design + anchors + LoRAs

**Canonical home:** `03_design/characters/`  ·  **Stage key:** `02_characters`

**Purpose.** Lock each character's face/wardrobe. Anchor stills feed --cref; trained character LoRAs feed the keyframe path's ref_lora (see loras/README.md + lora_library.json).

**Produce (put your files in this folder):**
Per character: a portrait prompt + a locked hero-portrait still in anchors/, and (optional) a trained LoRA in loras/<character>/lora/ registered in loras/lora_library.json.

**Template / how to make it:**
Character Portrait Template (docs/PROMPT_PIPELINE_TEMPLATES.md Stage 3): SUBJECT_BY_ATTRIBUTE + WARDROBE + SETTING + LIGHTING + GAZE + PERFORMANCE + kernel look. Anchor order: render the hero portraits first, then --cref everywhere.

**Gate (must pass before this stage is done):**
No resemblance to real public figures. Anchor matches the character bible. Motifs correct.

**Ideation / refinement agent.** Via the Ilyrium MCP, call
`stage_ideate(project="<this project>", stage="02_characters", message="...")` to develop and refine this
stage in conversation — it works with the Style Kernel + casting canon in context, can read any
project file, and writes drafts back into this folder. (Autonomy A1: it proposes; you accept.)

---
*Production values are fixed by `../../style_kernel.json`; the continuity/legal gate is `../../08_qa/`
→ `../../QA_CHECKLIST.md`; consent/likeness releases live in `../../00_admin/rights_releases/`.
Creative content varies here — production values do not.*
