# Nast Reference Pack — Design Spec

**Date:** 2026-06-09
**Status:** Approved design (pending written-spec review)
**Repo:** `slm-foundry`
**Author:** Brad Upham (with Claude)

## 1. Purpose & context

`slm-foundry` is a working pipeline for fine-tuning small models on an AWS EC2 g6.2xlarge
(NVIDIA L4 24 GB) — Unsloth QLoRA → eval → Ollama deploy, artifacts in
`s3://ilyrium-slm-foundry/`. A QLoRA smoke test and the full merge→GGUF→Ollama deploy loop
are already proven.

This spec defines the **first real domain** built on that foundry: an **automated Thomas Nast
political satirist**. Nast (1840–1902; all work public domain) is deliberately chosen as the
*first of many* because it exercises **two distinct model shapes plus orchestration**, forcing
the foundry's reusable template to be complete rather than text-only.

## 2. Goals / non-goals

**Goals**
- Build the Nast satirist end-to-end: text **Brain** (event → allegory + image prompt), vision
  **Hand** (prompt → 1870s engraving), and an **orchestration** layer joining them.
- Extract a reusable **domain-pack template** so future domains (philosophical lens engines,
  GIA, etc.) are "fill in the blanks," not re-architecture.
- Establish a lightweight **governance/rights** standard carried by every pack.

**Non-goals**
- No new generic training machinery — reuse `src/{prepare,train,evaluate,export_gguf}.py`.
- No second domain in this spec (a Shape-A-only domain validates the template in a later spec).
- Not a public/hosted product; this is an internal foundry capability.

## 3. Core concept: two model shapes

The foundry produces **domain packs**. Every pack is one or both of:

- **Shape A — Logic/Lens (text SLM):** text in → analyzed/transformed text out. Proven path
  (Unsloth QLoRA → Ollama). Covers the Nast *Brain*, future lens engines, extractors, PermitHub,
  GIA, Ilyrium style. Most domains are Shape A.
- **Shape B — Aesthetic/Style (vision LoRA):** image style capture. Different framework
  (Kohya / ai-toolkit), different data (images + captions), different deploy (ComfyUI). Only some
  domains need it. The Nast *Hand* is the foundry's first Shape B.

Nast = Shape A + Shape B + orchestration → the complete reference case.

## 4. Architecture

```
modern news/event ─▶ NODE 1: BRAIN ─▶ NODE 2: HAND ─▶ finished cartoon
                     text SLM           vision LoRA(s)
                     (Qwen3-8B,         (SDXL + Flux,
                      Unsloth/L4)        Kohya/ai-toolkit/L4)
                          │                  │
                  allegory + image      1870s wood-engraving
                       prompt                style
                          └───── ORCHESTRATION (Python) ─────┘
                          event → Brain(Ollama) → prompt → Hand(ComfyUI) → cartoon.png
```

**Infra reuse:** the Brain trains/serves via the existing foundry path. The Hand's LoRAs load
into **Ilyrium AutoStudio's existing ComfyUI** (`apps/auto-studio/ComfyUI`, supports SDXL + Flux)
— the foundry *trains* the style; Ilyrium *serves* it.

## 5. Domain-pack contract (reusable unit)

Each domain is a self-contained folder; generic machinery stays in `src/`.

```
packs/<domain>/
  pack.yaml            # contract (see schema below)
  data/
    brain/             # train/val/test JSONL (gitignored -> S3)
    hand/              # image scans + .txt captions (gitignored -> S3)
  brain/               # Shape A: pack-specific config (points at src/train.py etc.)
  hand/                # Shape B: Kohya/ai-toolkit configs + caption tooling
  orchestrate/         # event -> brain -> hand pipeline
  GOVERNANCE.md        # rights + AI-satire disclosure (1 page)
  README.md
```

**`pack.yaml` schema (v1):**
```yaml
name: nast
shapes: [A, B]                 # which model shapes this pack builds
governance: GOVERNANCE.md      # required; presence enforced by template
brain:                         # present iff shape A
  base: unsloth/Qwen3-8B
  chat_template: qwen-2.5
  output_schema: {allegory_rationale: str, image_prompt: str}
  data: {train: data/brain/train.jsonl, val: ..., test: ...}
  eval_gate: beat_base         # ship only if it beats the base model
hand:                          # present iff shape B
  bases: [sdxl, flux]          # build one LoRA per base
  trigger: thomas_nast_style
  scans: data/hand/            # PNG + matching .txt captions
  deploy: ilyrium-comfyui
artifacts_s3: s3://ilyrium-slm-foundry/models/nast/
```

## 6. Node 1 — The Brain (Shape A)

- **Base:** Qwen3-8B (Apache-2.0; strong creative reasoning).
- **Task:** ingest a modern event/news summary → output structured JSON
  `{"allegory_rationale": "...", "image_prompt": "<SDXL/Flux-ready Nast prompt>"}`. The rationale
  makes the choice auditable; the prompt drives Node 2.
- **Data recipe (hybrid, ~275 pairs):**
  - **~25 hand-curated gold pairs** (canonical Nast allegories: Tammany Tiger, the Ring, the
    Republican Elephant, the Democratic Donkey, the Catholic-school "crocodiles," inflation/"rag
    baby," etc.). These **double as the held-out eval set**.
  - **~250 distilled pairs** generated by an **open-weight teacher** (DeepSeek/Qwen via OpenRouter,
    ToS-clean) mapping historical event summaries → Nast-style prompts, then verified. Source text:
    *Harper's Weekly* OCR (Internet Archive) + LOC metadata.
  - Format: messages-JSONL via existing `prepare.py` (dedup + split).
- **Train / eval / deploy:** existing `train.py` (QLoRA) → `evaluate.py` extended with an
  **LLM-as-judge** rubric (allegory quality, period-correct visual vocabulary, prompt validity)
  plus a regression check vs. base → ship gate → Ollama.

## 7. Node 2 — The Hand (Shape B)

- **Targets:** two style LoRAs from one scan set — **SDXL 1.0** and **Flux.1-dev**
  (`pack.yaml` selects; default builds both).
- **Trainers:** Kohya_ss (SDXL); Kohya sd-scripts Flux or ai-toolkit (Flux) — chosen at impl.
- **Data:** 50–100 public-domain Harper's Weekly Nast scans via **LOC API** (Nast d. 1902 → PD),
  cropped to clean panels. **Two caption styles from the same images:** tag-style (WD14) for SDXL,
  natural-language (BLIP/long-form) for Flux; both carry the `thomas_nast_style` trigger; captions
  hand-corrected.
- **VRAM:** SDXL LoRA trains comfortably on the L4 (24 GB). **Flux is heavier (12B)** — feasible on
  24 GB only with **fp8 / low-VRAM** settings and slower; if tight, run the Flux LoRA once on a
  one-off **L40S (48 GB)**. This is the single place a larger GPU may be needed.
- **Output:** two LoRA safetensors (~100–200 MB each) → S3 → loaded in Ilyrium ComfyUI.

## 8. Orchestration

`orchestrate/satirist.py`: `event/headline → Brain (Ollama API) → image_prompt → Hand (ComfyUI
API + Nast LoRA + chosen base) → cartoon.png`. This is the end-to-end "automated satirist" demo,
runnable against the trained artifacts.

## 9. Governance (one page per pack, enforced by template)

- **Data:** public-domain, owned, or licensed only (Nast = clean PD).
- **Outputs:** carry an **AI-generated satire** disclosure.
- **Scope:** satire of public figures/officials/institutions is in scope; **no defamatory
  depictions of private individuals**; no protected-class hate content.
- The template refuses to be "complete" without a `GOVERNANCE.md`.

## 10. Data sources

| Source | Use | Access |
|---|---|---|
| **LOC Prints & Photographs API** | Hand image scans + metadata | JSON API (primary) |
| **Internet Archive** (`internetarchive`) | *Harper's Weekly* OCR for Brain context | Python lib |
| **DPLA / NYPL APIs** | Supplementary scans + rich metadata | free key/token |
| Macculloch Hall / Billy Ireland | High-quality curation (manual) | scrape if needed |

## 11. Phasing (all in this spec; delivered in order)

- **Phase 0 — Scaffolding:** `packs/nast/` tree, `packs/_template/` stub, `pack.yaml` schema,
  LOC fetch script stub, `GOVERNANCE.md`, wired into repo + committed. *(Low-risk; lands first.)*
- **Phase 1 — Brain:** dataset build (gold + distilled) → train → judge-eval → Ollama. Ships alone.
- **Phase 2 — Hand:** LOC scrape → caption (2 styles) → Kohya SDXL LoRA → Flux LoRA → S3.
- **Phase 3 — Orchestration + template extraction:** wire Brain→Hand; lift `packs/_template/`
  from the finished `packs/nast/`; document "how to build domain N+1."

## 12. Risks & mitigations

- **Flux VRAM on L4** → fp8/low-VRAM; fall back to one-off L40S.
- **Distilled Brain data quality** (teacher hallucination) → verification pass + the 25 gold pairs
  as an honest eval set; never let synthetic grade itself.
- **Caption quality drives style fidelity** → hand-correct auto-captions; keep the scan set small
  and clean over large and noisy.
- **GGUF export on Amazon Linux** (known: Unsloth uses apt-get) → use the proven Ollama-import
  deploy path (`deploy/serve_ollama.sh`).
- **Cost** → L4 ~$0.98/hr; stop between phases; budget a few dollars per training run.

## 13. Deliverables

- `packs/nast/` complete (Brain config, Hand configs, orchestrator, governance).
- `packs/_template/` reusable skeleton + "build a new domain" guide.
- Trained artifacts in S3: Brain adapter/GGUF + two Hand LoRAs.
- Registry rows in `registry/models.csv` for each artifact.
- A working `satirist.py` end-to-end demo.

## 14. Success criteria

- Brain beats base Qwen3-8B on the judge rubric over the 25-gold eval set.
- Hand LoRAs produce recognizably Nast-style engravings in ComfyUI (SDXL and Flux).
- One command turns a modern headline into a Nast-style cartoon.
- A second domain can be started by copying `packs/_template/` and filling `pack.yaml` — no
  changes to `src/`.
