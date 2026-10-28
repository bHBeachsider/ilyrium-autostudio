# CLAUDE.md — Ilyrium AutoStudio

## Governance

This file is a STATIC WORKFLOW CONTRACT for the Ilyrium film studio repo. It defines
rules, conventions and session protocol. It is NOT a knowledge base.

BELONGS HERE: commit conventions, repo layout, pipeline invariants, hard-won tool
rules, cost discipline, the gates that must not be skipped.

DOES NOT BELONG HERE: per-project creative context, script CLI docs, model prices,
dynamic state. Those live in `projects/<name>/`, `docs/`, and the studio registries.

Max 160 lines. Directory-scoped CLAUDE.md files may add local context.

> Replaced 2026-09-01. This file previously contained PermitHub's contract by mistake;
> the original is archived at `docs/PERMITHUB_CLAUDE_md.archived`.

## What Is Ilyrium AutoStudio

An AI-native film studio: bible → script → characters → environments → keyframes →
shots → voice → music → edit → QA → key art, run as an agent pipeline with a
provenance ledger. Output is finished film, not clips.

## Repo Layout
```
apps/auto-studio/       — the pipeline: producer, render dispatch, console, CLI, scaffold
agents/stage_NN_*/      — per-stage ideation agents (00_bible … 10_keyart)
ilyrium-shots/          — the render box: shot specs, keyframes, batch_render, ledger
projects/<name>/        — one film per dir: 00_admin … 99_archive, PROJECT.yaml, kernel
manuals/                — agent-ready tool manuals (blender, davinci, comfyui, ue, …)
policies/ · evals/      — release policy, rubrics, golden sets
skills/                 — packaged studio skills
docs/                   — architecture, plans, research, specs, strategy
```

## Working Style
- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `test:`
- Direct assessment — no sycophancy
- Cost-conscious — prefer free/cheap; the box beats the cloud for drafts
- Automated workflows over manual processes

## Coding Discipline
1. **Ask, don't assume.** Unclear or underspecified → ask before writing code.
2. **Simplest solution first.** No abstractions that weren't requested.
3. **Don't touch unrelated code.** Not part of the task → don't modify it.
4. **Flag uncertainty explicitly.** Confidence without certainty causes more damage
   than admitting a gap.

## Pipeline Invariants
- **Specs are the contract.** Every shot is a `shot_spec.schema.json`-valid JSON file.
  Nothing renders that has not passed `conformance.py`.
- **Takes are append-only.** `regenerate_shot` adds a take; it never overwrites one.
  Selection is a separate, reversible act (`select_take`).
- **The ledger is the audit spine.** Every render appends to
  `ilyrium-shots/ledger/<song-id>.jsonl` and must verify `chain_ok`. Never rewrite,
  reorder or renumber ledger history — including to tidy up IDs.
- **Song IDs are owned.** `ilyrium-shots/SONG_ID_REGISTRY.json` records which project
  owns which ID prefix and which IDs are already claimed. Claim before you scaffold.
- **The kernel governs the look.** `style_kernel.json` per project; a change is a
  version bump and flags dependents.
- **Release is gated, not assumed.** `run_release_qa` + `approve_release` with the
  no-likeness legal check. A4 is non-delegable.

## Hard-Won Tool Rules (do not relearn these)
- **Script, don't click.** DaVinci and Blender work is Python. GUIs are for *previewing*
  results, never for configuration or fixes. (2026-05-27; cost 90 min once.)
- **PowerShell files must be ASCII-only.** Brad's PS 5.1 reads `.ps1` as Win-1252.
  Use `-` `->` `[OK]` `[FAIL]`, never em-dashes, arrows, checkmarks — they surface as
  cryptic "missing brace" parser errors.
- **Resolve `DeleteClips()` is unreliable** (20.3.3). Scripted ADD, manual DELETE.
- **SSH tunnels: `-L PORT:127.0.0.1:PORT`.** Windows EC2 resolves `localhost` to ::1
  and silently breaks the forward.
- **Check `$env:DATABASE_URL`** before running anything DB-backed; a global value
  overrides project `.env`.
- **Blender 4.4+**: `action.fcurves` is gone — use
  `action.layers[*].strips[*].channelbag(slot).fcurves`.
- **Blender 5.x VSE**: `sequences*` renamed to `strips*`.
- **`generate_first_cut` always exceeds the 60 s MCP timeout.** Poll
  `outputs/<campaign>/project.json`. Do not re-fire.
- **Restart the studio MCP after changing `producer.py`** — a running server keeps old
  code. If project state flip-flops, kill zombie `studio_mcp.py` processes.

## Cost Discipline
- **STOP the GPU box when idle.** A forgotten g6.2xlarge weekend is ~$60; a forgotten
  month is ~$650 (this happened, July 2026).
- AWS G-family quota is **8 vCPU** — one g6.2xlarge at a time. Path A does not
  parallelize until the quota is raised.
- Draft on the box; spend cloud credits only where the pilot said the difference shows
  (hero close-ups, lip-sync beats, 21:9-critical wides).
- Preview cost before any batch. Per-job caps live in `.env`.

## Session Protocol
1. Read the project's `START_HERE.md` and `PROJECT.yaml` before touching it.
2. Check `FINDINGS.md` (repo root and project-local) — do not rediscover a closed finding.
3. Confirm box state before rendering; confirm it is STOPPED before you finish.
4. Record decisions in the project's `00_admin/`, not in chat.

## The Findings Loop
Every recurring failure (frequency >= 3) must terminate in a durable artifact — a test,
gate, validator, prompt patch or policy — or an explicit accepted-risk record. Append to
`FINDINGS.md` with root cause, the layer that caught it, and the layer that should have.
