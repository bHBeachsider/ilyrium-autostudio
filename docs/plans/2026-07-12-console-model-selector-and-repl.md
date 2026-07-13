# Spec: Console global model selector + in-console qwen3 REPL (for Fable 5)

**Target executor:** Fable 5. **Repo:** `C:\Users\bradu\Documents\ilyrium-autostudio`.
**Working dir:** `apps/auto-studio/`. **Approach:** EXTEND the existing `app.py` +
`console_helpers.py` you already built (the production console). Two focused additions. Do NOT
rewrite; do NOT touch git; do NOT boot the EC2 box (UI is verifiable offline).

## Problem being solved
Brad reports: in the console he "sees the models but it's not clear how to select them." Today the
only actionable model picker is buried in Production → (pick project) → Asset Gen → the "Render a
shot" control. `list_models` is a read-only catalog. Fix: (1) a **global, always-visible model
selector**, and (2) an **in-console conversational REPL** (chat) wired to qwen3 that generates and
edits images through the shared engine — the same loop as the desktop `cli/ilyrium.ps1`, but in the
Streamlit UI.

---

## Feature A — Global "Active image model" selector (sidebar)

- Add an **always-visible selectbox in the sidebar** titled "🎨 Active image model", populated from
  `console_helpers.comfyui_model_ids()` → `['comfyui', 'comfyui:zimage', 'comfyui:flux2',
  'comfyui:flux2-klein-9b-uncensored']`. Default to `comfyui:flux2` (or `comfyui:zimage` — pick the
  fast default; zimage). Store the choice in `st.session_state["active_image_model"]`.
- Make this the **default** for every render/edit control that uses a comfyui model:
  - `_render_shot_control` (stage-4 "Render a shot"): default its Model selectbox to the global
    choice (still allow per-render override, incl. the video engines).
  - `edit_image` / `inpaint_image` tool forms: default their model field to the **short id** derived
    from the global choice (`comfyui:flux2` → `flux2`; bare `comfyui` → `zimage`). Add a
    `console_helpers.short_model_id(model_spec)` helper for this mapping.
  - The new REPL panel (Feature B) uses it too.
- Add a one-line caption under it: "Used by Render, Edit, Inpaint, and the Studio Chat below."
- Keep it near the top of the sidebar, above or below the Box panel — visible without scrolling.

**Acceptance:** the selector is present in the sidebar on first load (box up or down); changing it
changes the pre-selected model in the shot-render control and the edit/inpaint forms.

---

## Feature B — Studio Chat: an in-console qwen3 REPL

A conversational panel (use `st.chat_input` + `st.chat_message`, history in
`st.session_state["studio_chat"]`) that mirrors the desktop `cli/ilyrium.ps1` loop, but calls the
shared engine **in-process** (the tunnel exposes ollama :11434 and ComfyUI :8188 locally — no SSM).

Place it as a **new top-level tab** `st.tabs([... , "💬 Studio Chat"])` (add to the existing tab
row) OR a prominent panel at the top of the Production tab — prefer a dedicated tab so it has room.

### Engine wiring (all via `from media import comfyui_engine as ce`)
- **Generate** (plain text): `prompt = ce.gen_prompt(idea, hint)` where hint is "flux"/"z-image"
  from the active model; then `graph = ce.build_graph(<model_spec>, prompt, seed=..., width=1024,
  height=1024)`; then `path = ce.submit_and_wait(graph)`. Display the returned image with
  `st.image`. Show the qwen prompt too.
- **Iterative edit** (a follow-up message when there's a current image): pass the previous prompt
  as `base=` to `ce.gen_prompt` AND run img2img — `ce.build_graph(model, prompt, img=<uploaded
  name>, denoise=<state>)`. To use the last image as the img2img reference, upload it first with
  `ce.upload_image(local_path)` and pass the returned name as `img=`.
- **Region inpaint**: if the user gives a region, `ce.make_region_mask("x1,y1,x2,y2", w, h)` then
  `build_graph(..., img=..., mask=<mask name>)`.
- Track in session_state: `last_image_path`, `last_prompt`, current model (from the global
  selector), denoise, seed.

### Chat commands (parse the message; anything else is a generate/edit)
Mirror the REPL's slash-style but adapt for chat — accept `:`-prefixed commands:
- plain text with **no** current image → fresh generate
- plain text **with** a current image → edit the current image (img2img + qwen base-prompt)
- `:new <text>` → clear context, fresh generate
- `:model <id>` → set the active image model (also updates the sidebar selection)
- `:region x1,y1,x2,y2 <change>` → inpaint that region of the current image
- `:denoise <0-1>` → set edit strength
- `:seed <n>` → set seed
- `:help` → list these
Guard: if ComfyUI is unreachable (`ce.is_up()` false), the chat input is disabled with "Start the
box + open the tunnel (Box & Status tab)."

### Saving results
Save produced images to `outputs/_chat/` (create it) with a stable name, and offer a download
button. Also `st.image` inline in the chat turn. (The engine returns the file on the box's ComfyUI
output; for in-process the console reaches it via /view — reuse `submit_and_wait` which already
downloads to a path. Confirm where it writes and surface that path.)

**Acceptance:** with the box up + tunnel open, typing "a red fox in snow" produces an image inline;
a follow-up "make it night" edits that same image; `:region 0.5,0,1,0.5 a full moon` inpaints only
that area. With the box down, the chat input is disabled with the helpful caption. (Do NOT boot the
box to test — verify the wiring/guards offline; live is Brad's to run.)

---

## Guardrails
1. Extend `app.py` + `console_helpers.py` only (a small new helper is fine). No other files. No git.
2. No tracebacks in the UI — wrap `ce.*` calls in try/except → `st.error`.
3. Data-driven: model lists from `comfyui_model_ids()`; don't hardcode ids in the UI.
4. Do NOT boot the box. The `gen_prompt`/`submit_and_wait` calls need the tunnel; gate them on
   `ce.is_up()` and make the offline path degrade cleanly.
5. Keep `gen_prompt`'s existing `keep_alive:0` behavior (it's in the engine already — don't change
   the engine).

## Verification (offline)
- `.\venv\Scripts\python -m py_compile app.py console_helpers.py` → 0 errors.
- `streamlit.testing.v1.AppTest.from_file("app.py").run()` → `at.exception is None`; assert the
  sidebar has a selectbox whose options include `comfyui:flux2`; assert a "Studio Chat" tab exists;
  assert `st.chat_input` is present (or the panel renders) and is **disabled** when `ce.is_up()` is
  False (box down — which is the case in the test env).
- `short_model_id("comfyui:flux2") == "flux2"`, `short_model_id("comfyui") == "zimage"`.
- Report: files changed + line ranges, the AppTest output, the assertions, a one-paragraph "how to
  use the Studio Chat" for Brad, and anything not wired with the reason.

Begin by reading `app.py` (esp. the sidebar block, `_render_shot_control`, `_render_tool_expander`,
and the `with tab_prod:` section) and `console_helpers.py`, plus `media/comfyui_engine.py`'s public
API (`gen_prompt`, `build_graph`, `submit_and_wait`, `upload_image`, `make_region_mask`, `is_up`).
