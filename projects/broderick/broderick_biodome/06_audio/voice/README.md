# Stage 7 — Voice / Dialogue / VO

**Canonical home:** `06_audio/voice/`  ·  **Stage key:** `06_voice`

**Purpose.** Lock one voice per character (the audio equivalent of --cref).

**Produce (put your files in this folder):**
voice_casting.md (per-character ElevenLabs voice_id + settings) + line specs.

**Template / how to make it:**
Voice-casting sheet: NAME: provider, voice_id, stability, similarity, style, accent/age, baseline delivery. Line: SPEAKER | line | delivery — spoken words only.

**Gate (must pass before this stage is done):**
One locked voice per character. Delivery matches the character's register.

**Ideation / refinement agent.** Via the Ilyrium MCP, call
`stage_ideate(project="<this project>", stage="06_voice", message="...")` to develop and refine this
stage in conversation — it works with the Style Kernel + casting canon in context, can read any
project file, and writes drafts back into this folder. (Autonomy A1: it proposes; you accept.)

---
*Production values are fixed by `../../style_kernel.json`; the continuity/legal gate is `../../08_qa/`
→ `../../QA_CHECKLIST.md`; consent/likeness releases live in `../../00_admin/rights_releases/`.
Creative content varies here — production values do not.*
