# Ilyrium Persona Studio — Program Spec

**Date:** 2026-06-11
**Status:** Design (program-level; decomposes into sub-specs)
**Home:** `ilyrium-autostudio` (all content creation), drawing models from `slm-foundry`

## 1. Purpose
An agentic **creator-content platform**: any fine-tuned **persona SLM** — its captured *taste/style* —
drives and guardrails the generation of finished media, which is then **editable downstream** and
optionally distributed. It runs as a production inside the **Ilyrium AutoStudio spine**, fed by a
**reusable media-intake tool**, with a recursive self-improving eval loop and human-gated publishing.

**The persona's captured taste is both the creative director and the safety rail** — wide creative
latitude *within* the captured style.

**First instance:** the Thomas Nast political-cartoon satirist. The *same* platform serves any future
persona (other satirists, illustrators, writers, designers, domain explainers) as a `slm-foundry`
domain pack — political satire is one application, not the scope.

## 2. Core principle (separation of concerns)
- **`slm-foundry` = model factory.** Trains persona models: the **Brain** (text SLM: event → `{allegory_rationale, image_prompt, labels}`) and **Hand** style LoRAs (SDXL fast, Flux high-fidelity).
- **`ilyrium-autostudio` = production spine.** Consumes those artifacts (Brain via Ollama, LoRAs via ComfyUI) and runs the studio stages: ideate → render → composite → QA → publish. Reuses Ilyrium's Style Kernel, prompt taxonomy, asset graph, oversight console, autonomy ladder (A0–A4), governance/policy packs, and C2PA provenance.
- **Intake spine = reusable tool** (see §4), feeding current events into ideation.

## 3. Pipeline (per cartoon)
```
feeds → INTAKE SPINE → signal/topic ──(RAG: live facts)──► BRAIN (ideate)
   → {allegory_rationale, image_prompt, label set, caption}
   → HAND: SDXL (drafts/variants) ─choose─► Flux (final render)
   → ComfyUI COMPOSITE: overlay labels + caption banner + upscale   ← Nast's labels are TEXT;
   → QA + HITL GATE (rights/safety/disclosure)                         diffusion can't render them,
   → multi-platform PUBLISH (X, Instagram, …)                          so they are composited in post
```

## 3A. Persona as creative director AND guardrail
The fine-tuned SLM persona encodes a *taste* (Nast's allegorical logic; for others: a visual style, a
prose voice, an editorial sensibility, a domain methodology). That taste is the platform's organizing
constraint:
- **Creative latitude:** the agent freely explores ideas, compositions, and variants — wide latitude.
- **Guardrail:** every candidate is scored against the persona's captured taste, where the eval rubric is
  **derived from the persona's own gold exemplars**. Off-taste outputs are rejected or revised. The hard
  governance rails (§7) apply to every persona on top of this.
- **Generality:** the platform is persona-agnostic. Swapping the `slm-foundry` domain pack swaps the entire
  creative identity *and* its guardrails — no platform changes.

## 3B. Recursive self-improving eval loop
Two nested loops:
1. **Per-artifact (generate → critique → revise):** the production generates candidate(s); an independent
   **judge** (different model than the generator, à la Sonnet-4.6) scores each against the persona's taste
   rubric + governance; the agent revises (re-prompt, re-render, inpaint/composition tweaks) and resubmits,
   looping until the taste bar is met or an iteration/token budget is hit. (Same loop-until-quality /
   adversarial-verify pattern as the foundry's eval gate.)
2. **Model self-improvement (production feedback → retrain):** accepted/rejected verdicts, HITL approvals,
   and downstream signals (edits made, audience engagement) become **new labeled data** fed back to
   `slm-foundry` to fine-tune the next version of the persona's Brain/LoRA. The persona gets better at its
   own taste over rounds.

**Guardrails on the loop (so "recursive self-improvement" cannot drift or reward-hack):**
- a **fixed, human-curated gold exemplar set** the loop is *always* re-evaluated against (anti-collapse);
- convergence + iteration/token budgets;
- **HITL stays non-delegable** at publish and at each model-promotion;
- **eval-vs-base gate before any new persona model ships** (no regression).
The loop optimizes quality; it never bypasses human oversight.

## 3C. Downstream adjustability (non-destructive)
Generated output is a **starting point, not a final**. Every artifact is tweakable without re-running:
- ComfyUI **img2img / inpaint / regional re-prompt / ControlNet** to adjust composition, fix a figure,
  restyle a region.
- The **label/caption layer is a separate composite** → editable independently of the render.
- **Non-destructive takes** (Ilyrium already supports this): each edit is a new version; nothing is
  overwritten; the asset graph tracks lineage.
- The persona/style stays locked while only the `author`-layer specifics change.

## 3D. Output formats: single-panel, comic-strip, film (taste != format)
A creator's *taste* (voice/style/logic) is **format-independent**; single-panel / multi-panel strip / film
is a structural *mode*. A persona that worked across formats is trained as **one taste + format
conditioning**, not separate models:
- **Hand style LoRA — format-agnostic.** Train on ALL the creator's visual output flattened to single
  images: single panels as-is, **strips cropped into panels**, **film/animation sampled into frames**. The
  LoRA learns the *look*, independent of layout — one LoRA covers every format.
- **Brain — format-aware.** Train on the union of works, each example **tagged with its format**, so it emits
  the right STRUCTURE per request under one voice:
  - `single_panel` -> `{rationale, image_prompt, labels}`
  - `strip` -> `{beats, panels:[{image_prompt, dialogue, label}], layout}`
  - `film` -> `{logline, shots:[{image_prompt, action, dialogue, duration}], style_notes}`
  Format is a **generation parameter** ("single panel" / "3-panel strip" / "15s film"), same persona voice.
- **Mixed-format corpus is an asset** — it reinforces the unified voice; the format field handles the
  structural difference. **Per-format gold eval sets** keep each mode honest.
- **Character anchors** (shared) carry recurring characters across panels/frames (Ilyrium consistency engine).

**Film dimension:** film = shots over *time*. The Brain emits a **shot list / storyboard** (the `artboard`
skill's 4x4 grid is the bridge to text-to-video); the Hand renders **keyframes** in the persona style;
**Ilyrium's keyframe->image-to-video + non-destructive takes** animate them with character consistency —
this is exactly what the AutoStudio film pipeline already does. The persona supplies style + storyboard voice.

**Persona packs declare supported formats** (`formats: [single_panel, strip, film]`); the render slice
(sub-project 3) branches accordingly: single image | per-panel + composite | keyframes -> image-to-video.

## 4. The reusable Intake Spine (MCP + Plugin + REST)
Lift PermitHub's A20 / `media-share-intake` **pattern** (url_router → platform adapters → media_items →
classify → segment → signals → HITL) into a standalone, reusable component. Layered exposure:
- **Core library** (`intake-core`): framework-agnostic ingestion + signal-extraction engine. Single source of truth.
- **MCP server** (`intake-mcp`): tools `ingest_url`, `ingest_feed`, `get_signals`, `query_media` — for the studio agent and 3rd-party agent builders.
- **REST API** (`intake-api`): same core behind HTTP + API keys + usage metering — for non-agent 3rd-party apps and as a monetization surface.
- **Claude Code plugin** (`intake-plugin`): bundles the MCP server + a skill + commands for one-command install in Claude Code.
Decision: **not MCP-or-Plugin** — core engine → MCP (agents) + REST (everyone else) → plugin packages the MCP for Claude Code. 3rd-party use: AI builders → MCP; conventional apps → REST (metered); CC devs → plugin.
**Do NOT reuse the contaminating full-text-search path; intake is feed/URL/category-scoped** (lesson from the Nast harvest).

## 5. Feeds + ideation
- **Feeds:** GDELT (events/tone, free), X/Twitter trends (adapter exists in PermitHub), NewsAPI/AP/Reuters, Reddit r/politics, Google Trends, political RSS (Politico/The Hill), C-SPAN/congress.
- **"Ideate politician X / issue Y":** a query → **RAG over ingested feeds** for *current* facts (the Brain has no live knowledge) → Brain emits the cartoon concept + labels + caption → render.
- **Multi-persona:** each artist persona (Nast now; Daumier/Herblock/Low/modern later) is a `slm-foundry` domain pack (Brain + LoRAs), **selectable** at ideation.

## 6. Distribution
Approved cartoon + Brain-written caption → platform adapters (X API; Instagram Graph API [business acct]; optional TikTok/YouTube via Ilyrium's video pipeline) → schedule/post. Reuses Ilyrium's **final-publication HITL gate** — publishing stays human-approved.

## 7. Governance (throughline — non-negotiable)
Satire of public figures is protected, but: platform impersonation/AI policies apply, false-*factual* implication risks defamation, AI-disclosure is required. Therefore: **nothing auto-publishes** (HITL approval per piece), every output carries an **AI-generated satire** label, C2PA provenance retained, no defamatory factual claims, no private individuals. Maps onto Ilyrium gates (expressive intent, rights/consent, safety, final publication) + PermitHub's HITL queue.

## 8. Monetization (separate track, audience-first)
1. Branded X/IG account, daily Nast-style takes (near-zero marginal cost: local models).
2. Patreon/Substack + print-on-demand (Printful).
3. Platform payouts (X/YouTube).
4. Licensing / commissioned satire (B2B).
5. Engine-as-product: satirist-as-a-service + **the foundry's "lens engine" training** as a paid service (and the metered intake REST API).

## 9. Decomposition into sub-projects (build order)
Each gets its own spec → plan → build:
1. **Intake Spine v1** — core lib + MCP server (feed/URL ingestion + signal extraction). *Foundational; reusable immediately.*
2. **Ideation slice** — RAG over intake signals → Nast Brain → `{concept, labels, caption}`. (Brain already trained.)
3. **Render+composite slice** — ComfyUI graph: SDXL/Flux LoRA render → label/caption compositing → upscale. (LoRAs from foundry.)
4. **Studio integration** — wire 2+3 as an Ilyrium production (Style Kernel asset + taxonomy `author` layer + oversight console + HITL gate).
5. **Distribution** — platform adapters + scheduling behind the publish gate.
6. **Monetization** — REST API metering + the audience/print/licensing surfaces.
7. **Recursive eval loop** — built in two stages: the **per-artifact critique→revise** loop ships *inside*
   the render slice (3); the **production-feedback→retrain** loop is added after studio integration (4),
   wiring HITL/engagement signals back into `slm-foundry`.

> Everything in 2–7 is **persona-agnostic** — the Nast pack is the first fill-in; a new persona reuses the
> whole platform by supplying its own `slm-foundry` domain pack (Brain + LoRAs + gold exemplars/rubric).

## 10. First slice (recommended scope for the first plan)
**End-to-end manual-publish vertical:** intake one feed → RAG on a chosen politician/issue → Nast Brain
concept → SDXL draft + Flux final in ComfyUI → composite labels+caption → **one round of per-artifact
critique→revise** (judge scores against the Nast gold rubric; agent revises once if below bar) →
**save file for manual posting** (no auto-distribution, no monetization, no retrain loop yet). Proves the
creative loop + the minimal eval loop + downstream-editable output before automating publish/money/retrain.
Governance gate present from day one (manual review = the gate).

## 11. Open questions
- Intake Spine home: shared repo vs. inside `ilyrium-autostudio`? (Reusable → leans shared/standalone.)
- Hosted MCP/REST infra (Railway? the env shows a Railway MCP) for 3rd-party access.
- Which 2nd persona after Nast (validates multi-persona).
- Instagram requires a business account + Graph API review; X API tier/cost.
