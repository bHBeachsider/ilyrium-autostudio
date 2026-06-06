# Ilyrium OS Studio — UI Design Spec
**Date:** 2026-06-06  
**Status:** Approved for implementation planning  
**Scope:** Internal team UI for the 8-stage film production pipeline  
**Repo home:** `apps/control-panel/`

---

## 1. Purpose and Scope

The Ilyrium OS Studio is the **internal team interface** for producing short films, topical videos, and political satire. It is distinct from the customer-facing Ad Studio (Streamlit, separate port/process) — they share the same NeonDB but are separate applications with separate purposes.

The OS Studio serves a small team of collaborators (directors, editors, producers). Primary workflow: jump into a specific production stage mid-project, iterate deeply, hand off — while always being able to see the status of all active productions.

**What this spec covers:**
- Three-panel shell layout
- 8-stage pipeline navigation and stage workspace design
- HITL agent CLI (human-in-the-loop controls + file upload per stage)
- Visual style system (Obsidian Studio)
- Tech stack decisions and migration plan from Python

**What this spec does not cover:**
- Customer-facing Ad Studio (Streamlit — unchanged)
- Scaffold CLI (`scaffold.py` — unchanged, Python)
- EC2/ComfyUI session management (`ec2_session.py` — unchanged, Python)

---

## 2. Layout Architecture: Three-Panel Workspace

```
┌─────────────────────────────────────────────────────────────────────┐
│  TOP BAR: Logo · Project › Stage breadcrumb · Mode badge · Status   │
├──────────────┬──────────────────────────────────┬───────────────────┤
│  LEFT RAIL   │        CENTER: Stage Editor      │  RIGHT: Agent CLI │
│  (210px)     │           (flex: 1)              │     (300px)       │
│              │                                  │                   │
│  Productions │  Stage-specific controls         │  Stage agent      │
│  (cards with │  (tabs, cards, render controls,  │  conversation     │
│  progress    │  prompt editors, image grids,    │  + HITL controls  │
│  bars)       │  take management)                │  + upload         │
│              │                                  │                   │
│  ─────────── │                                  │                   │
│              │                                  │                   │
│  Pipeline    │                                  │                   │
│  (8 stages   │                                  │                   │
│  with A1–A4  │                                  │                   │
│  autonomy    │                                  │                   │
│  badges)     │                                  │                   │
└──────────────┴──────────────────────────────────┴───────────────────┘
```

All three panels are visible simultaneously. No mode switching — jump to a stage, work, the agent is always in context on the right.

### Top bar
- Logo + wordmark ("⬡ ILYRIUM OS")
- Breadcrumb: `Project name › Stage name`
- Pipeline mode badge: `MANUAL` / `ASSISTED` / `AUTO DRAFT` (pill, amber)
- Pipeline status: stage N of 8, overall state

### Left rail
Two sections, scrollable:
1. **Productions** — project cards with title, progress bar (stage N/8), active stage label. Click to switch active project.
2. **Pipeline — [active project]** — 8 stage items with: status dot (✓ done / ▶ active / ○ locked / ⛔ gate), stage name, autonomy badge (A1/A2/A3/A4). Click to jump to any completed or active stage.

Autonomy legend pinned at bottom of rail.

---

## 3. The 8 Pipeline Stages

Sourced from `studio_pipeline.py` STAGES. Each stage has a dedicated center-panel workspace and a dedicated agent in the right panel.

| # | Key | Name | Autonomy | Costly | Gate | Agent persona |
|---|-----|------|----------|--------|------|---------------|
| 1 | brief | Brief | A1 | No | No | Story Architect |
| 2 | script | Script | A1 | No | No | Screenwriter |
| 3 | storyboard | Storyboard | A1 | No | No | Storyboard Artist |
| 4 | asset_gen | Asset Gen | A3 | Yes | No | Art Director |
| 5 | review | Review | A2 | No | No | QA Supervisor |
| 6 | assembly | Assembly | A3 | Yes | No | Editor |
| 7 | rights | Rights / Release | A4 | No | Yes | Release Gate (non-delegable) |
| 8 | delivery | Delivery / Archive | A3 | No | No | Delivery Producer |

**Autonomy tiers:**
- **A1** — propose → approve. Agent drafts; human accepts before anything is written.
- **A2** — auto reversible. Agent acts; human can undo. No pre-approval needed.
- **A3** — auto within budget. Agent runs within the confirmed cost ceiling. Costly stages (4, 6) show a cost confirmation gate the first time.
- **A4** — non-delegable. Human must act. Agent can advise but cannot approve.

### Stage workspace types (center panel)

**Document stages (Brief, Script, Storyboard):**
Scene/section cards with structured fields (visual prompt, voiceover/dialogue, characters, duration target). Gate status banner. JSON export. Import from `scenes.json`.

**Asset Gen stage:**
Tabbed sub-sections (Characters / Environments / Props / Keyframes). Per-asset cards with: image grid (takes/attempts), prompt field, model selector, render controls (queue / cancel / regen), upload reference button, LoRA status, canon-lint indicator. Cost gate banner when first entered. Batch-render all button.

**Review stage:**
QA checklist runner per shot/asset. Pass/fail per gate criterion. Fail → regenerate with linked fix. Bulk approve.

**Assembly stage:**
Shot/scene ordering. Take selector per shot (radio). Music bed upload + gain slider. Re-assemble cut button. OTIO export for DaVinci.

**Rights / Release stage (A4 gate):**
Non-delegable checklist. Rights releases file list. Likeness flag review. Human signs off; agent cannot bypass. Status: pending human action.

**Delivery stage:**
Master export controls. Platform cut selector. C2PA manifest generation. R2 upload status. Archive.

---

## 4. Right Panel: HITL Agent CLI

Identical structure across all 8 stages; agent identity and capabilities change per stage.

### Header
- Agent avatar (emoji or icon) + name + role subtitle
- Context chips: autonomy tier, kernel loaded ✓, casting canon ✓, costly/confirmed (when applicable)

### Message area
- Scrollable conversation. Agent messages left-aligned (dark card, amber left-border). User messages right-aligned (amber-tinted card).
- Agent proactively flags: HITL flags (resemblance blocks, canon violations, missing fields), cost confirmations, questions when it needs direction.
- Attached files shown as attachment rows beneath the message that sent them.

### HITL control bar (above input)
- **Approve stage** (green) — marks stage done, advances pipeline
- **Reject / redo** (red) — reverts stage to pending, agent re-runs
- **Pause agent** — suspends A2/A3 autonomous execution
- **Re-enter stage** — re-opens a completed stage for fine-tuning (downstream stages marked stale)
- **Add note** — appends a note to the stage log without triggering re-run

A4 stages: only "Add note" is available from agent; Approve/Reject are the only HITL actions (no agent bypass).

### Input area
- Multiline text input (auto-grow, max 80px)
- **📎 Upload button** — accepts images (png/jpg/jpeg/webp), documents (md/txt/json/csv), audio (mp3/wav), video (mp4/mov). File is saved to project folder and injected into the next agent turn as a vision block (images) or inline text (documents).
- Send button
- Hint text: "Attach images · docs · audio · video · JSON — agent reads all formats"

---

## 5. Visual Style: Obsidian Studio

**Design language:** Near-black backgrounds with warm amber/gold primary accents. Inspired by DaVinci Resolve / high-end NLE tools. Craft-forward, not SaaS-dashboard.

### Color tokens
| Token | Value | Use |
|-------|-------|-----|
| `bg-base` | `#050508` | App background |
| `bg-surface` | `#0d0e0b` | Cards, panels |
| `bg-elevated` | `#0c0d0a` | Left rail, right panel |
| `border` | `#252010` | All borders |
| `accent` | `#d97706` | Active stage, CTA buttons, labels, agent border |
| `accent-hover` | `#b45309` | Button hover |
| `accent-subtle` | `#1a1508` | Active item backgrounds |
| `text-primary` | `#f1f5f9` | Headings, active items |
| `text-secondary` | `#94a3b8` | Body text |
| `text-muted` | `#4b5563` | Locked stages, hints |
| `status-done` | `#22c55e` | Done/approved |
| `status-running` | `#f59e0b` | In progress / rendering |
| `status-error` | `#ef4444` | Blocked / failed |
| `a1-badge` | `#6366f1` | Autonomy tier color |
| `a2-badge` | `#22c55e` | Autonomy tier color |
| `a3-badge` | `#f59e0b` | Autonomy tier color |
| `a4-badge` | `#ef4444` | Autonomy tier color |

### Typography
- Font: system stack (`-apple-system, BlinkMacSystemFont, 'Segoe UI'`)
- Stage labels: 10–11px, uppercase, 1.2–1.5px letter-spacing, amber
- Body: 13–15px
- Headings: 17–20px, weight 700–800
- Monospace: agent messages, prompt fields, JSON editors

### Component conventions
- Border-radius: 5–8px on cards, 4–5px on tags/badges, 20px on mode pill
- Progress bars: 4–5px height, amber gradient fill
- Scrollbars: 4px, `#252010` thumb, transparent track
- All borders: `1px solid #252010` (or amber variant `#d9770644` for active/highlighted)

---

## 6. Tech Stack

### Frontend (`apps/control-panel/`)
| Layer | Technology | Notes |
|-------|-----------|-------|
| Framework | Next.js 15, App Router | Already in place |
| Language | TypeScript 6 | Already in place |
| Styling | Tailwind CSS v4 | Already in place |
| Components | shadcn/ui | Add — unstyled primitives, override with Obsidian tokens |
| Data fetching | SWR | Add — polling for pipeline state |
| Streaming | Native SSE (`ReadableStream`) | Next.js API route → browser for agent message streaming |
| DB client | Prisma 7 + NeonDB | Already in place (two clients) |

### Database (extend existing Prisma schema)
Add to `prisma/schema.prisma`:
- `PipelineRun` — maps to a project, holds 8-stage state (status, mode, currentStage, log)
- `StageRecord` — per-stage state (status, result, notes, approvedBy, confirmedCost)
- `AgentMessage` — per-stage conversation history (role, content, attachments, timestamp)
- `UploadedAsset` — file uploads attached in agent turns (path, mimeType, stageKey, projectSlug)

Existing `Campaign` / `Scene` models — keep unchanged (used by Ad Studio path).

### Agent runtime (TypeScript — port from Python)
Port these three modules into `apps/control-panel/lib/`:

| Python source | TypeScript destination | What it contains |
|--------------|----------------------|-----------------|
| `studio_pipeline.py` | `lib/pipeline/state-machine.ts` | `plan()`, `run()`, `approve()`, `reenter()`, `confirmCost()`, `addNote()` — pure logic, no IO |
| `stage_agents.py` | `lib/agents/stage-agent.ts` | `buildSystemPrompt()`, `runAgentTurn()`, tool loop, **8 new pipeline-stage personas** (not a direct port — `stage_agents.py` has 11 scaffold-folder personas; this file defines 8 new ones aligned to the pipeline keys: brief/script/storyboard/asset_gen/review/assembly/rights/delivery) |
| `project_store.py` | `lib/pipeline/project-store.ts` | `loadProject()`, `saveProject()`, `getProject()` — JSON on disk + Prisma sync |

`lib/adapter-bus.ts` — **unchanged**. All render dispatch goes through here.

File I/O tools (currently `_exec_tool` in Python): re-implement in Node.js `fs/promises` — `readProjectFile`, `writeStageFile`, `listProjectFiles`.

### API routes (new)
```
app/api/pipeline/[projectId]/route.ts      — GET state, POST actions (approve/reject/reenter/pause)
app/api/agent/[projectId]/[stage]/route.ts — POST turn, returns SSE stream
app/api/upload/[projectId]/[stage]/route.ts — POST multipart, saves file, returns path
app/api/projects/route.ts                  — GET project list
```

### What stays Python (unchanged)
- `scaffold.py` — project scaffolding CLI
- `ec2_session.py` — ComfyUI/EC2 session management
- `apps/auto-studio/app.py` (Streamlit) — customer Ad Studio, separate process

---

## 7. Routing Structure

```
app/
  layout.tsx                          — root layout (fonts, theme)
  page.tsx                            — redirect → /studio
  studio/
    layout.tsx                        — three-panel shell (rail + outlet + agent panel)
    page.tsx                          — project list / dashboard (left rail expanded)
    [projectId]/
      page.tsx                        — redirect → active stage
      [stage]/
        page.tsx                      — stage workspace (center panel content)
```

The three-panel shell is the `studio/layout.tsx` — it renders the left rail and agent panel as persistent layout, and the center panel is the page outlet. Stage navigation = client-side route change, no full reload.

---

## 8. Data Flow

```
Browser
  │
  ├── SWR poll → GET /api/pipeline/[projectId]
  │     └── reads PipelineRun + StageRecords from NeonDB
  │
  ├── User sends agent message → POST /api/agent/[projectId]/[stage]
  │     ├── saves message to AgentMessage table
  │     ├── calls lib/agents/stage-agent.ts runAgentTurn()
  │     │     └── Anthropic SDK (claude-sonnet-4-6), tool loop
  │     └── streams response chunks as SSE → browser renders in real time
  │
  ├── User uploads file → POST /api/upload/[projectId]/[stage]
  │     ├── saves to projects/[slug]/[stage]/uploads/
  │     ├── records in UploadedAsset table
  │     └── returns path → injected as vision/doc block in next agent turn
  │
  ├── HITL action → POST /api/pipeline/[projectId] { action: 'approve' | 'reject' | ... }
  │     ├── calls lib/pipeline/state-machine.ts
  │     └── updates PipelineRun + StageRecord in NeonDB
  │
  └── Render dispatch → lib/adapter-bus.ts executeGeneration()
        ├── fallback chain across registered adapters (Veo 3.1, Grok, ElevenLabs, ...)
        ├── uploads result to R2
        └── writes RightsRecord (auto-quarantine until approved)
```

---

## 9. Out of Scope (not in this spec)

- Real-time multiplayer / collaborative cursors — single-user per session for now
- Mobile layout — desktop-only (large screen assumed for 3-panel)
- Customer-facing UI changes — Streamlit Ad Studio is frozen
- LoRA training UI — deferred to a future spec
- DaVinci Resolve deep integration — OTIO export is the handoff mechanism

---

## 10. Open Questions (resolved before implementation)

All resolved during brainstorming:
- ✅ Layout: three-panel workspace
- ✅ Style: Obsidian Studio (amber/near-black)
- ✅ Stages: 8 (from `studio_pipeline.py`), not 11 scaffold stages
- ✅ Agent runtime: TypeScript (port from Python)
- ✅ Existing app: build into `apps/control-panel/`, no new app
- ✅ Streamlit: stays as customer Ad Studio, no changes
