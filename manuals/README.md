# Ilyrium tool manuals → agent knowledge

Source documentation for every tool the Ilyrium AI Studio drives, captured here so the
`manual-to-agent-transform` skill can convert each into a governed, source-traceable,
machine-readable **agent package** — giving the studio agents real, cited knowledge of how to
operate each tool (instead of guessing).

## Layout

Per app:
- `<app>/source/` — the raw manual(s): official PDF if one exists, else captured web docs (markdown/PDF).
- `<app>/agent_package/` — the skill output (the 16 artifacts + `agent_readable_manual.md`).

Run the skill per app:
> "make the manual in `manuals/<app>/source/` agent-ready" → output to `manuals/<app>/agent_package/`.

## Catalog & status

Priority is **API/CLI tools the agents actually call** (top), over GUI apps (bottom) where the
agent needs only specific headless/scripting sections.

| App | Role in studio | Source type | Status |
|---|---|---|---|
| tensorart-tams | image/video gen (TAMS API) | web docs → captured | **agent package ✓** (full worked example + qa gate) |
| runway | cinematic i2v / Aleph edit (API) | web docs → captured | **agent package ✓** |
| elevenlabs | voiceover / voice-casting (API) | web + our adapter | **agent package ✓** |
| ffmpeg | delivery: encode/captions/cutdowns (CLI) | docs + our delivery.py/qc.py | **agent package ✓** |
| comfyui | controlled generation (API + graphs) | web docs → captured | **agent package ✓** |
| igniter | engine/vehicle SFX (DAW plugin, human-led) | local PDF (35pp) → ingested | **agent package ✓** (human-led; no API) |
| blender | 3D / headless render (bpy) | local HTML manual (v5.10) | **agent package ✓** (headless subset; full bpy = follow-up) |
| unreal-engine | virtual production (UE + Python) | Epic docs (JS — grounded subset) | **agent package ✓** (headless MRQ subset; signatures = open_questions) |
| davinci-resolve | finishing / round-trip (scripting API) | local Resolve Scripting README (authoritative) | **agent package ✓** (full Scripting API) |
| filmcraft | edit: headless assembly, cut-as-code (CLI) | pinned clone docs (`agents.md`, `control-protocol.md`) + `commands --json` | **agent package ✓** (headless CLI subset; GUI/bridge/`ui_*` out of scope) |

## Capture notes (how to source each)

- **PDF available** (Blender, FFmpeg, UE, Resolve): download the official manual PDF — the skill
  ingests it directly. For huge manuals, capture only the **agent-relevant subset** (the scripting /
  headless / CLI sections the studio uses), not the whole GUI guide — the agent doesn't need the UI.
- **Web-only** (TAMS, Runway, ElevenLabs, ComfyUI): capture the key doc pages into a single
  markdown (or print-to-PDF). Keep page/section structure so `source_refs` stay meaningful.
- One `source_id` per physical doc; never merge two tools into one source.

## Why this matters

The skill's output is what lets a studio agent answer "which TensorArt stage params does Wan i2v
need?" or "what's the FFmpeg loudnorm target for a 9:16 social cut?" from a **cited** package
rather than improvising — and it carries the agent action boundaries (what's safe to automate vs.
escalate) per tool.
