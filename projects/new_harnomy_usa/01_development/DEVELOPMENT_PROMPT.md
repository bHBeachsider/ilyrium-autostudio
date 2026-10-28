# Master Development Prompt

The single seed prompt that populates **every Stage-1 (bible) + Stage-2 (script) element** for a
new project, so nothing is missing before production. Run it once against your seed idea; it
emits structured output keyed to the checklist (`bible_checklist.json` / `stage_checklists.json`),
which you then write into the project (or let the Story Architect agent write). Adjust any field
after — this guarantees coverage, not finality.

**Where this lives:** canonical copy here (`docs/MASTER_DEVELOPMENT_PROMPT.md`); the project
scaffold drops a per-project working copy at `projects/<name>/01_development/DEVELOPMENT_PROMPT.md`.

---

## PROMPT (paste into Claude / the Story Architect agent)

> **You are the show's Story Architect + Showrunner.** Develop a complete production bible and
> scene-card script from the seed below. **Rules:** produce *structure, not prose flourishes*;
> describe every person **by attribute, never by likeness to a real public figure**; hold the
> Style Kernel; every claim must be specific and renderable. Where a fact is genuinely the
> author's to choose and isn't in the seed, propose a strong default and mark it `(proposed)`.
>
> **SEED**
> - Title idea: `{TITLE}`
> - Format: `{short | film | opera | music video | ad | series}` · length `{}` · aspect `{16:9|9:16|4:5}`
> - One-line idea: `{SEED IDEA}`
> - Real people depicted (consent state): `{none | name: consent confirmed/pending}`
> - Style Kernel — look: `{}` · register: `{}` · negatives: `{}` (leave blank to propose)
> - Known assets: `{e.g. trained LoRA, harvested reference set, locations}`
>
> **Emit each of these elements, labeled with its key, in this order:**
>
> **1 · NARRATIVE** — `logline` (PROTAGONIST wants X but OBSTACLE; STAKES) · `premise` (2–3 sentences)
> · `theme` (what it's really about) · `tone` · `genre_format` · `central_question` · `stakes` · `arc`.
>
> **2 · WORLD** — `setting` (place+period+geography) · `world_rules` (what is/isn't possible) ·
> `timeline` (dated chronology) · `factions` · `culture` · `visual_signature` · `motifs` ·
> `locations` (named hero sets, one block each: PLACE | FUNCTION | VISUAL SIGNATURE | MOTIFS).
>
> **3 · CHARACTER** (one block per character) — `identity` (NAME|ROLE|AGE|ORIGIN) · `physical`
> (build/features by attribute) · `psychology` (want/need/flaw/contradiction) · `wardrobe_signature`
> · `performance_register` · `voice` · `relationships`.
>
> **4 · VISUAL / STYLE** — `look`, `register`, `negatives` (fill the kernel if blank) ·
> `reference_imagery` (what to gather + which sources) · `continuity_anchors` (what the hero
> anchor must depict + whether a LoRA is needed).
>
> **5 · GOVERNANCE** — `consent_release` (who needs one) · `ip_rights` · `likeness_policy` · `canon_control`.
>
> **6 · PRODUCTION-BINDING** — `casting_canon` (emit as a JSON object per character: role, age,
> origin, build, features, wardrobe_signature, performance_register, voice_note, likeness) ·
> `reference_backlinks` (which research/refs prove which claims).
>
> **STAGE 2 — SCRIPT** — then break the story into an ordered `scene_cards` array. Each card:
> `{scene_number, location, characters[], action, visual_prompt, dialogue:[{speaker,line,delivery}],
> voiceover, performance, duration_target_s}`. Dialogue/VO = spoken words only. Restate each
> recurring character's physical description in every scene that needs it.
>
> **OUTPUT FORMAT:** Markdown sections per dimension with the element keys as sub-headers; the
> `casting_canon` and `scene_cards` as fenced JSON blocks ready to paste into `style_kernel.json`
> and `02_script/scenes.json`. End with a **COVERAGE CHECK**: list any required element you could
> not complete and why.

---

## How to use
1. Fill the SEED slots (the only human input).
2. Run the prompt; review the structured output.
3. Write each block to its target (the console's Stage panels do this, or paste manually):
   narrative/world/character → `01_development/bible/...`; `casting_canon`+kernel → `style_kernel.json`;
   scene cards → `02_script/scenes.json`.
4. Run `python apps/auto-studio/stage_scaffold.py status --project <name>` to see what's still missing.
