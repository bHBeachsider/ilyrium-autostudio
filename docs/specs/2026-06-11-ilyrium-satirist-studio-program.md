# Ilyrium Satirist Studio — Program Spec

**Date:** 2026-06-11
**Status:** Design (program-level; decomposes into sub-specs)
**Home:** `ilyrium-autostudio` (all content creation), drawing models from `slm-foundry`

## 1. Purpose
An agentic production system that turns a politician or political issue into a finished,
period-accurate **satirical cartoon** (Thomas Nast first; other personas later), and distributes it.
It runs as a **production inside the Ilyrium AutoStudio spine**, fed by a **reusable media-intake tool**,
with a human-gated publish step.

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

## 10. First slice (recommended scope for the first plan)
**End-to-end manual-publish vertical:** intake one feed → RAG on a chosen politician/issue → Nast Brain concept → SDXL draft + Flux final in ComfyUI → composite labels+caption → **save file for manual posting** (no auto-distribution, no monetization yet). Proves the creative loop before automating publish/money. Governance gate present from day one (manual review = the gate).

## 11. Open questions
- Intake Spine home: shared repo vs. inside `ilyrium-autostudio`? (Reusable → leans shared/standalone.)
- Hosted MCP/REST infra (Railway? the env shows a Railway MCP) for 3rd-party access.
- Which 2nd persona after Nast (validates multi-persona).
- Instagram requires a business account + Graph API review; X API tier/cost.
