# broderick autobiography 707b

Master production folder, scaffolded by the Ilyrium studio (canonical scaffold v2).
**Type:** SHORT  ·  **Genre packs:** narrative

The tree is a **governed, phase-based roadmap** — walk it top to bottom. Each stage folder's
`README.md` states what to produce, the template, and the gate it must pass.

**Production values are fixed and enforced** by:
- `PROJECT.yaml` — manifest: asset-graph key (externalId), type, genre packs, kernel, status.
- `style_kernel.json` — the look/register/casting/motifs/negatives for THIS production.
- `QA_CHECKLIST.md` — the continuity + legal gate every render must pass (the release gate's rubric).
- `NEGATIVE_PROMPTS.txt` — the negative-prompt library.

**Governance is structural:** `00_admin/` (rights releases, contracts, licenses, policy pack) and
`08_qa/` map to the asset graph's RightsRecord + the enforced release gate;
`09_delivery/c2pa_manifests/` maps to ProvenanceRecord.c2paManifestUri.

**Look (from the kernel):** hand-drawn indie comic illustration, bold confident ink linework, flat color fills, iPad/Procreate texture, single-pane and multi-pane comic composition, hand-lettered speech balloons…

**Pipeline stages (canonical homes):**
- `01_development/bible/` — Story / World / Character Bible  *(stage `00_bible`)*
- `02_script/` — Screenwriting / Scene cards  *(stage `01_script`)*
- `03_design/characters/` — Character design + anchors + LoRAs  *(stage `02_characters`)*
- `03_design/environments/` — Environment & prop plates  *(stage `03_environments`)*
- `04_preproduction/keyframes/` — Keyframes (the bridge to motion)  *(stage `04_keyframes`)*
- `05_production/shots/` — Shots (render to video)  *(stage `05_shots`)*
- `06_audio/voice/` — Voice / Dialogue / VO  *(stage `06_voice`)*
- `06_audio/music/` — Music / Sound  *(stage `07_music`)*
- `07_post/edit/` — Editorial / Assembly  *(stage `08_edit`)*
- `08_qa/` — Continuity / QA / Governance  *(stage `09_qa`)*
- `10_marketing/keyart/` — Marketing / Key art  *(stage `10_keyart`)*

**Wiring into the auto-studio:** set the campaign/project's `style_kernel` to this `style_kernel.json`
(or the kernel name). Generate character anchors in `03_design/characters/anchors/`, then use model
`keyframe` so shots --cref against them.

**Prompting:** each stage's required information categories come from the shared taxonomy
(`apps/auto-studio/prompt_taxonomy.json`). Get a stage's fill-in checklist with
`python prompt_kit.py checklist <stage>` (browsable copies in `apps/auto-studio/prompt_templates/`),
auto-fill the kernel layer with `compose`, and lint a finished prompt for missing categories with
`lint`. See `docs/PROMPT_SYSTEM.md`. References: `docs/PROMPT_PIPELINE_TEMPLATES.md`,
`docs/PROJECT_SCAFFOLD_PROPOSAL.md`.
