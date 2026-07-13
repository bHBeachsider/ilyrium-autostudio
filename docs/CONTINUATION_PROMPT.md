# Continuation Prompt — Ilyrium AutoStudio session

Paste this into a fresh Claude Code session started in `C:\Users\bradu\Documents\ilyrium-autostudio`.

---

You are continuing work on **Ilyrium AutoStudio** (`C:\Users\bradu\Documents\ilyrium-autostudio`),
an AI film/music-video production pipeline. Windows 11, PowerShell 7 (`pwsh`) + Git Bash both
available. Prior sessions built and debugged a full production stack. **Read `docs/plans/*.md` specs
and the memory notes for detail; don't re-derive what's below.**

## The stack (4 processes — all currently RUNNING)

| Layer | What / how to run | Port |
|---|---|---|
| **Pipeline service** (Python/Starlette, the "spine") | from `apps/auto-studio`: `.\venv\Scripts\python -m uvicorn studio_pipeline_service:app --port 8800 --host 127.0.0.1` | 8800 |
| **Control-panel** (Next.js console — the main UI) | from `apps/control-panel`: `npm run dev` → open `http://localhost:3000/studio/console` | 3000 |
| **EC2 GPU box** `i-04b439af98c8faf5e` (ubuntu-qwen-gpu, NVIDIA L4, ~$1.20/hr) — ComfyUI + ollama/qwen3 | driven from `apps/auto-studio/cli/box.ps1` (start/stop/status/tunnel/gen) over **AWS SSM (no SSH)** | 8188 / 11434 via SSH tunnel |

**Rule:** editing `studio_pipeline_service.py`, `producer.py`, `media/*`, or the repo `.env` needs a
`:8800` **restart** to take effect (it loads them once). Next.js hot-reloads. Restart pattern:
```bash
cd apps/auto-studio
OLD=$(netstat -ano 2>/dev/null | grep ':8800' | grep LISTENING | awk '{print $NF}' | head -1); [ -n "$OLD" ] && taskkill //PID "$OLD" //F
./venv/Scripts/python.exe -m uvicorn studio_pipeline_service:app --port 8800 --host 127.0.0.1 > /tmp/pipeline_8800.log 2>&1 &
```

## Two consoles exist (both work)
- **control-panel** (`:3000/studio/console`) — the fuller **clip-production** pipeline (8 stages
  Brief→Script→Storyboard→Asset Gen→Review→Assembly→Rights→Delivery). Has a Box/tunnel control panel
  + a **multi-provider "Studio Chat"** (local qwen3 default; Claude/Gemini/Grok/Qwen-cloud light up
  when their key env var is set — routing AROUND Anthropic to a local model on Brad's box is the
  intended "unregulated" path; do NOT build guardrail-bypass logic).
- **AutoStudio** (Streamlit) — `apps/auto-studio: .\venv\Scripts\python -m streamlit run app.py`.
  Has a sidebar model selector + Studio Chat + box controls. Simpler, one process.

## The image-gen CLI (separate from the video pipeline)
`apps/auto-studio/cli/` — desktop control of the box over SSM:
- `.\box.ps1 start|stop|status|tunnel|gen "<idea>" -Model zimage|flux2|flux2-klein-9b-uncensored`
- `.\ilyrium.ps1` = interactive REPL (`ilyrium-autostudio>`): text→image, iterative edit, `:region`
  inpaint, `:mask`, `:model`, etc. Images land in `apps/auto-studio/cli/renders/`.
- Desktop shortcuts **"Ilyrium Start" / "Ilyrium Close"** → `session-start.cmd` / `session-close.cmd`.
- Shared engine `apps/auto-studio/media/comfyui_engine.py` owns ALL ComfyUI HTTP; models declared in
  `apps/auto-studio/model_registry.json` (`comfyui:zimage`, `comfyui:flux2`, `comfyui:flux2-klein-9b-uncensored`).
  Pipeline renders any of them via `render_shot(..., model="comfyui:<id>")`.

## Bugs FIXED this session (all verified live — don't reintroduce)
1. **`.env` routed Anthropic calls to local Ollama** → pipeline's Claude Script stage 404'd
   ("model not found"). Fixed: repo-root `.env` now has the real `sk-ant-` key uncommented and
   `ANTHROPIC_BASE_URL`/`AUTH_TOKEN=ollama` commented out. Backup: `.env.bak-before-anthropic-fix`.
   Also bumped `claude-sonnet-4-6` → **`claude-sonnet-5`** in 6 pipeline files
   (pipeline_exec, stage_agents, ad_studio_agent, delivery, eval_tool_knowledge, app.py).
   **Current model IDs:** Sonnet=`claude-sonnet-5`, Opus=`claude-opus-4-8`, Haiku=`claude-haiku-4-5`.
2. **Render (Asset Gen) crashed with `UnicodeEncodeError ❌`** — emoji (❌) in `producer._logger`
   `print()` hit Windows cp1252 stdout. Fixed: emoji-safe print in `producer.py` + process-wide
   `sys.stdout/stderr.reconfigure(encoding="utf-8")` at top of `studio_pipeline_service.py`.
3. **Assembly (Stage 6) crashed `index 0 is out of bounds for axis 0 with size 0`** — moviepy audio
   bug: when a voiceover outlasts a shot's video, `_extend_to(...,'loop')` loops the video's native
   audio and the reader hits a zero-length window on write. Fixed in `media/post_production.py`:
   on extended clips, use ONLY the voiceover mp3 (drop looped native audio) + try/except guard.
   Verified: produced a valid 12MB / 65.7s master from the stripe project's 4 shots.
4. Earlier: **multi-file uploads** in Stage-1 Bible (Stage1Bible.tsx + bible_media/bible_scaffold)
   now accumulate all media types (img/video/mp3/text/pdf) with list+delete; box/tunnel switch +
   provider CLI added to control-panel; `list_tools` studio tool added.
5. The ComfyUI consolidation (Fable 5 refactor) — one engine, any registry model incl. abliterated,
   edit_image/inpaint_image studio tools. Committed + pushed (commits `b14b653`, `26e9e7b`).

## Active work / project
Brad is producing **"KING SIZE — The Ballad of Stripe"** (1990s Bronx boom-bap rap video), character
**Stripe** (canon: `projects/stripe/03_design/characters/CASTING_CANON.md` — B&W ink cartoon,
bald+horseshoe, sunglasses, gold chain, white speedo; comfyui-friendly, reference-driven).
Active project dir: `outputs/1990s_style_rap_video_featuring_the_main_charact_20260713_153408`
(4 shots rendered via grok-imagine default; assembly now works).

## IMPORTANT operational notes
- **Box is RUNNING (~$1.20/hr).** If Brad is done, stop it: `apps/auto-studio/cli> .\box.ps1 stop`
  (or Box & Status → Stop, or the Ilyrium Close shortcut).
- **ComfyUI on the box dies/deactivates** sometimes after stop/tunnel cycles — if a `comfyui:*`
  render errors, restart it: `.\box.ps1 run "sudo systemctl start comfyui"` (waits ~30s).
- **Video encoding is slow** (~2 min for a 65s clip) — not a hang.
- **Windows cp1252 gotcha:** set `$env:PYTHONIOENCODING='utf-8'` (or `PYTHONIOENCODING=utf-8` in bash)
  before running Python that prints emoji, or it raises UnicodeEncodeError in YOUR shell (the service
  itself is already UTF-8-safe).
- **SSM multi-line scripts** must be base64-wrapped (PowerShell 5.1 ConvertTo-Json mangles JSON) —
  `box.ps1::Send-SsmCommand` handles it.
- **Nothing is committed** since the two pushed consolidation commits: ~18 modified + ~465 untracked
  on `main`, incl. this session's fixes (.env, model IDs, encoding fix, assembly fix, upload/console
  work). A **private key `slm-foundry-key-v2.pem`** and `.pyc`/media are gitignored now — never commit
  the key. If asked to commit, do focused commits and exclude key/pyc/media.

## Verification habit (expected)
Independently verify fixes (compile + run the real path) before claiming done; stop the box to end
billing when finished. Memory notes in `~/.claude/projects/C--Users-bradu/memory/` cover the box/SSM,
image-gen CLI, and stale-instance history.

---
**Start by asking Brad what he wants to do next** (continue the Stripe video? commit the session's
fixes? something new?) — the stack is up and the last three pipeline bugs are fixed.
