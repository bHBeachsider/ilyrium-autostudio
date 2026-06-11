# Stage 1 — Story / World / Character Bible

**Canonical home:** `01_development/bible/`  ·  **Stage key:** `00_bible`

**Purpose.** The canonical record every later stage reads. Define structure, not prose.

**Produce (put your files in this folder):**
logline_treatment.md, world/ overview, characters/<NN_name>/bible.md

**Template / how to make it:**
Character entry: NAME | ROLE | AGE | ORIGIN | BUILD | WARDROBE SIGNATURE | AFFECT/PERFORMANCE REGISTER | ARC | VOICE NOTE.
World entry: PLACE | FUNCTION | VISUAL SIGNATURE | RECURRING MOTIFS.

**Gate (must pass before this stage is done):**
Every character's ORIGIN/AGE/BUILD matches casting_canon in style_kernel.json. People described by attribute, never by likeness to a real person.

**Ideation / refinement agent.** Via the Ilyrium MCP, call
`stage_ideate(project="<this project>", stage="00_bible", message="...")` to develop and refine this
stage in conversation — it works with the Style Kernel + casting canon in context, can read any
project file, and writes drafts back into this folder. (Autonomy A1: it proposes; you accept.)

---
*Production values are fixed by `../../style_kernel.json`; the continuity/legal gate is `../../08_qa/`
→ `../../QA_CHECKLIST.md`; consent/likeness releases live in `../../00_admin/rights_releases/`.
Creative content varies here — production values do not.*
