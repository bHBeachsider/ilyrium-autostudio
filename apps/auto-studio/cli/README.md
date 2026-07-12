# ilyrium studio CLI

Interactive, desktop-driven image generation on the ilyrium EC2 GPU box
(`ubuntu-qwen-gpu`, `i-04b439af98c8faf5e`, NVIDIA L4). No SSH keys needed for
control — the box is driven over **AWS SSM**; finished images are pulled down
over scp into [`renders/`](renders/).

## Quick start

From this folder (`apps/auto-studio/cli/`):

```powershell
.\session-start          # boot box + ComfyUI, open the interactive REPL
# ... generate / edit images ...
.\session-close          # stop the box (ends ~$1.20/hr billing)
```

Or the desktop shortcuts **Ilyrium Start** / **Ilyrium Close**.

## Files

| File | Role |
|---|---|
| `ilyrium.ps1` | The interactive REPL (`ilyrium-autostudio>`). Text-to-image, iterative editing, inpainting. |
| `box.ps1` | Box control + the `gen`/`prompt` engine. Verbs: `start stop status run shell ip gen prompt tunnel tunnel-down`. Ships `ilyrium_gen.py` + `comfyui_engine.py` + `model_registry.json` to the box over SSM and pulls results into `renders/`. |
| `ilyrium_gen.py` | Runs **on the box**: thin CLI over `media/comfyui_engine.py`. qwen3-coder writes the prompt (ollama :11434) → ComfyUI (:8188) renders any registry model → PNG. Supports txt2img, img2img, and inpainting (mask or `--region`). |
| `session-start.cmd` / `session-close.cmd` | Double-clickable launchers (targets of the desktop shortcuts). |
| `switch-backend.ps1` | Flip Claude Code's own backend between the Anthropic API and the box's local Ollama. |
| `renders/` | Where generated images land (gitignored). |

## REPL commands

Type an idea to generate; any follow-up text **edits** that image. `:help`
inside the REPL lists everything. Highlights: `:new`, `:edit-of <img> <change>`,
`:region x1,y1,x2,y2` / `:mask <file>` (inpainting), `:model`, `:seed`,
`:subtle`/`:strong`, `:img`, `:ask`, `:tunnel`, `:stop`.

## Relationship to `media/comfyui_engine.py` (consolidated 2026-07-12)

The CLI and the pipeline now share ONE engine:
[`../media/comfyui_engine.py`](../media/comfyui_engine.py) owns ALL ComfyUI
HTTP (`/prompt`, `/history`, `/view`, `/upload/image`) plus the graph-building
and editing logic (txt2img / img2img / inpaint / `--region`). `ilyrium_gen.py`
is a thin CLI over it; the pipeline's
[`../media/comfyui_renderer.py`](../media/comfyui_renderer.py) is a thin
wrapper over it (same public signatures as before, but failures now RAISE —
no more empty fallback `.png`s). `box.ps1 gen` ships **three** files to the
box: `ilyrium_gen.py`, `comfyui_engine.py`, and `model_registry.json`.

Models are defined ONLY in [`../model_registry.json`](../model_registry.json)
(`provider: "comfyui"`, ids `comfyui:zimage`, `comfyui:flux2`,
`comfyui:flux2-klein-9b-uncensored`, …). Adding an on-box model = one registry
entry with a `recipe` (programmatic graph, supports editing) or a `workflow`
(`comfyui_workflows/*_api.json` template, txt2img only). The pipeline renders
any of them via `render_shot(..., model="comfyui:<id>")`, and the agent tools
`edit_image` / `inpaint_image` (studio_tools/studio_mcp) edit stills through
the same engine.
