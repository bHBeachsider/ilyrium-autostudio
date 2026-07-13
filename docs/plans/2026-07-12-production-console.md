# Spec: Professional-grade production console (for Fable 5)

**Target executor:** Fable 5 (claude-fable-5).
**Repo:** `C:\Users\bradu\Documents\ilyrium-autostudio`
**Working dir:** `apps/auto-studio/`
**Approach:** EXTEND the existing Streamlit `app.py` in place (do NOT create a new app or a
Next.js console). `app.py` already runs the pipeline in-process and already has a Cloud-GPU
sidebar; you are upgrading it into a full production console.

---

## 0. Goal (one paragraph)

Turn `apps/auto-studio/app.py` (779-line Streamlit "Ad Studio") into a **professional production
console** that (a) has a **ComfyUI/box control panel with Start/Tunnel/Stop buttons and live
connection status**, (b) presents **all 21 studio tools grouped by the production stage where
they're used**, each rendered as a usable control, and (c) lets any image render/edit use the new
**`comfyui:<id>`** models (`comfyui:zimage`, `comfyui:flux2`, `comfyui:flux2-klein-9b-uncensored`).
The console drives the pipeline **in-process** (it already imports `producer`, `ec2_session`,
`project_store`) — no separate HTTP service required.

Keep it tasteful and professional: clear sections, consistent status chips, no clutter. This is
internal ops tooling used by one operator (Brad), not a multi-tenant product.

---

## 1. Ground truth — read before editing

- `app.py` — the console. ALREADY HAS: a "☁️ Cloud GPU" sidebar (~lines 139-159) using
  `ec2_session.status()`, `ensure_running`, `stop`, `is_comfyui_up()`; a staged numbered layout
  (Brand Kit → Script → Review → per-shot render); and a per-shot **model selectbox +
  `render_shot(...)`** (~lines 610-625) whose model list is **STALE** — it lists bare `comfyui`,
  not the `comfyui:*` ids. Reuse and upgrade these, don't duplicate them.
- `ec2_session.py` — box lifecycle: `status() -> {instance_id, region, state, public_ip}`,
  `ensure_running(wait, timeout)`, `stop()`, `is_comfyui_up(url, timeout) -> bool`. Instance
  `i-04b439af98c8faf5e`, ComfyUI at `http://127.0.0.1:8188` (through the SSH tunnel).
- `cli/box.ps1` — the operator's box driver with verbs `start | stop | status | tunnel |
  tunnel-down | gen | prompt`. **The tunnel (`:8188` ComfyUI + `:11434` ollama) is opened by
  `box.ps1 tunnel`**, NOT by `ec2_session` (which only does the instance + a reachability probe).
  The console must be able to open/close the tunnel — call `box.ps1` via `subprocess` (prefer
  `pwsh`, fall back to `powershell`), e.g. `pwsh -ExecutionPolicy Bypass -File cli/box.ps1 tunnel`.
- `studio_tools.py` — `TOOLS[]` (21 tools) + `execute_tool(name, tool_input, project_dir)`
  dispatcher. Includes `list_tools` (returns all tools + summaries), `list_models`,
  `recommend_models`, `edit_image`, `inpaint_image`, `render`/film tools. Call `execute_tool`
  directly (in-process) for tool actions; use `list_tools` to build the menu dynamically.
- `producer.py` — `render_shot(project, project_dir, scene_number, model=..., progress_cb=...)`.
  Model spec `comfyui:<id>` routes to the consolidated `media/comfyui_engine.py`. Also
  `edit_shot`, `assemble_cut`, `produce_campaign`.
- `model_registry.json` — the model catalog. The comfyui-provider ids are `comfyui`,
  `comfyui:zimage`, `comfyui:flux2`, `comfyui:flux2-klein-9b-uncensored`. Load via
  `model_select.load_registry()` (used by the `list_models` tool) so the console's model pickers
  are data-driven, not hardcoded.
- The **8 pipeline stages** (canonical, from `studio_pipeline_service.py` stage comments):
  1 Brief · 2 Script · 3 Storyboard/keyframe · 4 Asset Gen (render) · 5 Review · 6 Assembly ·
  7 Rights/Release gate · 8 Delivery.
- `project_store.py` (imported in app.py as `ps`) — load/save/list projects. Projects live under
  `../../projects/` (e.g. `stripe`, `broderick`, `bank_associate`, `upham`).

Run the console with: `apps/auto-studio> .\venv\Scripts\python -m streamlit run app.py`.

---

## 2. Feature 1 — ComfyUI / box control panel (full lifecycle)

Upgrade the sidebar "Cloud GPU" block into a dedicated, always-visible **Box & ComfyUI** panel.
Requirements:

- **Three buttons:** `▶ Start box`, `🔌 Open tunnel`, `⏹ Stop box`.
  - Start → `ec2_session.ensure_running(wait=False)` (non-blocking) then let status polling show
    progress. (Optionally offer a "start + wait" variant.)
  - Open tunnel → subprocess `box.ps1 tunnel`. Stop → `ec2_session.stop()` (and best-effort
    `box.ps1 tunnel-down`).
- **Live status chips**, each a colored dot + label, refreshed on rerun (and via a manual
  "🔄 Refresh status" button; a `st.autorefresh`/periodic poll is a nice-to-have but keep it from
  hammering AWS — cache `status()` for ~5s):
  - **Instance:** 🟢 running / 🟡 pending|stopping / ⚪ stopped / 🔴 error (from `status()["state"]`).
  - **ComfyUI:** 🟢 reachable / 🔴 unreachable (from `is_comfyui_up()`).
  - **Tunnel:** 🟢 up / ⚪ down (detect by whether `is_comfyui_up()` succeeds on 127.0.0.1:8188 —
    if the box is running but ComfyUI is unreachable locally, the tunnel is likely down).
  - Show `public_ip` and instance id.
- **Gate rendering on readiness:** any comfyui render/edit control is **disabled with a helpful
  caption** ("Start the box + open the tunnel to render on ComfyUI") unless
  `is_comfyui_up()` is true. Non-comfyui models (grok/veo/tensorart/etc.) are not gated.
- Handle the box being mid-transition gracefully (buttons disabled during pending/stopping).
- Cost note in the panel: "g6.2xlarge ≈ $1.20/hr while running — Stop when done."

Wrap every `ec2_session` / subprocess call in try/except and surface errors as `st.warning`,
never a traceback. (AWS creds may be missing in some environments — degrade, don't crash.)

---

## 3. Feature 2 — Tools grouped by production stage

Build a **stage-organized tool menu**. Use `st.tabs` (or an expander per stage) — one group per
stage — and render each tool as an actual control (button/form) that calls
`execute_tool(name, input, project_dir)` and shows the result.

**Stage → tool mapping** (assign every one of the 21 tools; a tool may appear under its primary
stage). Derive the tool list at runtime from `execute_tool("list_tools", {})` so it self-updates,
but use this authoring map for the grouping:

| Stage | Tools |
|---|---|
| **1 Brief** | `scaffold_project`, `get_project_state`, `recommend_models` |
| **2 Script** | `set_script` |
| **3 Storyboard** | `recommend_models` (keyframe), `list_models` |
| **4 Asset Gen (render)** | `generate_first_cut`, `regenerate_shot`, `render` via `render_shot` with the **`comfyui:*`** model picker, `select_take` |
| **5 Edit** | `edit_image`, `inpaint_image`, `edit_shot` |
| **6 Review** | `run_release_qa`, `run_style_validation` |
| **7 Assembly** | `reassemble_cut`, `generate_music_bed`, `set_audio_duck` |
| **8 Rights/Delivery** | `get_release_gate`, `get_approval_queue`, `approve_release` |
| **Utility (always visible)** | `list_tools`, `list_models`, `get_tool_manual` |

- Each tool's form fields come from its `input_schema` (in `TOOLS[]`) — render string/int/number/
  enum properties as the matching Streamlit widgets; mark `required` ones. This keeps the UI in
  sync with the tools automatically. A generic `render_tool_form(tool_def)` helper is ideal.
- For **render / edit_image / inpaint_image**, the model picker MUST list the `comfyui:*` ids
  (image models filtered from `model_registry.json`, `provider == "comfyui"`), and for edits
  expose `denoise` and (inpaint) `region` "x1,y1,x2,y2" + optional mask upload.
- Long-running tool calls (renders) run inside `st.status(...)`/`st.spinner` and stream
  `progress_cb` output; never block the UI silently. Show the returned file path / result, and
  for image outputs, `st.image` the result.

Do NOT break the existing top-to-bottom ad-studio flow (Brand Kit → Script chat → shots) — either
keep it as one tab ("Ad Studio") alongside a new "Production Tools" tab, or fold it into the
stage groups. Prefer a top-level `st.tabs(["Production", "Ad Studio", "Box & Status"])` so the old
flow stays usable.

---

## 4. Feature 3 — Fix the stale model list

Replace the hardcoded model `st.selectbox` (~line 612) so comfyui models are the new ids. Build
image-model options from `model_registry.json` (provider comfyui) + keep the video/other engines.
The bare `comfyui` should still work (defaults to zimage) but present the specific ids as the
choices. Do this everywhere a model is chosen (per-shot render AND the new edit/inpaint controls).

---

## 5. Guardrails / non-negotiables

1. **Extend, don't rewrite.** Preserve `app.py`'s existing working sections and imports. Refactor
   into helper functions where it improves clarity, but the existing ad-studio flow must still run.
2. **No tracebacks in the UI.** Wrap backend calls (ec2, subprocess, execute_tool, render) in
   try/except → `st.error`/`st.warning` with a readable message.
3. **Gate comfyui renders on `is_comfyui_up()`** (§2). Don't let a user fire a render into a dead
   endpoint — that now RAISES (post-consolidation) and would surface as an error.
4. **Cache `ec2_session.status()`** (~5s TTL, `st.cache_data` or a timestamp in `st.session_state`)
   so Streamlit reruns don't spam AWS `describe-instances`.
5. **The tunnel is subprocess `box.ps1`** — resolve `cli/box.ps1` relative to `app.py`'s dir;
   prefer `pwsh`, fall back to `powershell`; run with `-ExecutionPolicy Bypass`. Don't block the
   UI waiting on it — fire it and let status polling reflect the result.
6. **Data-driven menus:** tool list from `list_tools`, model list from `model_registry.json`. No
   duplicating the 21 tool names or the model ids as literals in the UI.
7. **Scope:** only `app.py` (+ small new helper modules if genuinely cleaner, e.g.
   `console_helpers.py`). Do NOT touch `producer.py`, `studio_tools.py`, the engine, or the box
   scripts. Do NOT start a Next.js build.
8. **Don't commit** — leave changes staged/unstaged for review. Don't touch git.

---

## 6. Verification (do this before reporting done)

- `python -m py_compile app.py` (and any new helper) — 0 errors.
- Launch it headless to confirm it imports and renders without exception:
  `.\venv\Scripts\python -m streamlit run app.py --server.headless true --server.port 8501` in the
  background, then GET `http://127.0.0.1:8501/` (or check the process stays up ~10s with no
  import crash), then stop it. Capture any startup error.
- Static checks you CAN do without a browser: assert `execute_tool("list_tools", {}, None)`
  returns 21 tools; assert the comfyui model ids resolve from `model_registry.json`; assert the
  box panel code path handles `is_comfyui_up() == False` (box down) without raising.
- Do NOT boot the EC2 box for this (UI wiring is verifiable offline; a live render is Brad's to
  run). If you want to prove the render button end-to-end, note it as an optional manual step, not
  something you auto-run (it costs money).

---

## 7. Deliverable / final report

Report back with:
1. Every change to `app.py` (and any new helper file) — what/why, with the key line ranges.
2. A short description of the final layout: the tabs/sections, the box panel, and the
   stage→tools grouping as implemented.
3. Verification evidence: py_compile result, the headless-Streamlit import check (stdout showing
   it started or the exact error), and the static assertions from §6.
4. Anything you could NOT wire (e.g. a tool whose schema didn't map to a widget) with the reason.
5. A one-paragraph "how to run it" for Brad.

Begin by reading `app.py` in full, then `ec2_session.py`, `studio_tools.py` (the TOOLS list +
execute_tool), and `cli/box.ps1`'s verb list.
