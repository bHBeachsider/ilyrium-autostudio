# Spec: Consolidate the ComfyUI render/edit engine (for Fable 5)

**Author:** hand-off spec. **Target executor:** Fable 5 (claude-fable-5).
**Repo:** `C:\Users\bradu\Documents\ilyrium-autostudio`
**Working dir for all paths below:** `apps/auto-studio/`

---

## 0. One-paragraph brief

Today there are **two independent ComfyUI implementations** that don't share code:
(1) the **production pipeline** renderer `media/comfyui_renderer.py` (token-injection into
pre-exported workflow JSON; render-only; used by `producer.py`), and (2) the **standalone
interactive CLI** `cli/ilyrium_gen.py` (builds workflows in code; has qwen3-coder prompt
writing + img2img + inpainting + region + iterative editing; driven from the desktop over
AWS SSM by `cli/box.ps1` / `cli/ilyrium.ps1`). The goal is to make the **production pipeline
able to run ANY registry model (including abliterated ones) via `comfyui:<model-id>`**, and to
**share ONE engine module** between the pipeline and the CLI so the editing tools
(img2img / inpaint / region / iterative) live in one place and both callers use the same code.
**No duplicate ComfyUI HTTP logic should remain.**

Do this as **two layers** (below). Do NOT turn editing into new pipeline stages — editing stays
a capability of the shared engine, invoked by the CLI and (optionally) by a studio tool; the
batch pipeline just gains model selection.

---

## 1. Ground truth (read these first — do not assume)

Read every file before writing code:

- `media/comfyui_renderer.py` — current pipeline renderer. Contract (VERBATIM from its
  docstring): *"Mirrors the other renderers' contract: returns the saved file path, raises on
  failure."* Mechanism: reads a workflow JSON, replaces `__PROMPT__` / `__IMAGE__` / `__SEED__`
  string tokens, POSTs `/prompt`, polls `/history/{id}`, downloads via `/view`. Note it has a
  **"fallback file" anti-pattern** (writes empty `.png` on failure instead of raising) — see §5.
- `ec2_session.py` — boto3 EC2 lifecycle (`status`, `ensure_running`, `stop`, `is_comfyui_up`)
  + `COMFYUI_URL` (default `http://127.0.0.1:8188`). Instance `i-04b439af98c8faf5e`.
- `cli/ilyrium_gen.py` — the interactive engine that RUNS ON THE BOX. Has: `gen_prompt()`
  (qwen3-coder via ollama :11434, with edit-mode base-prompt), `build_wf()` (programmatic
  graph for txt2img / img2img / inpaint via `VAEEncodeForInpaint` + `LoadImageMask`),
  `make_region_mask()` (PIL rectangle mask from coords), `render()` (POST/poll/return path),
  and hardcoded `MODELS` recipes for `flux2` and `zimage` (unet/clip/vae/latent/steps/etc,
  verified against ComfyUI `/object_info`).
- `producer.py` — the render dispatcher. `_render_video(model, ...)` is a **string-keyed
  router** (lines ~64-136): `if m == "comfyui": from media.comfyui_renderer import
  render_scene_comfyui`. Other engines: `tensorart:<id>`, `astria:<tune>`, `runway`, `keyframe`,
  `fal`. A new model form plugs in HERE.
- `model_registry.json` — `{version, note, modalities, models[]}`. Each model:
  `{id, name, provider, modality, base, strengths[], aspect[], cost_tier, requires_env,
  recommended_for[], notes}`. There is already a `provider: comfyui` entry `{"id":"comfyui",...
  "base":"configurable"}` and TensorArt entries for FLUX.1 and Z-Image-Turbo. `model_select.py`
  scores these against a project's `style_kernel.json`.
- `comfyui_workflows/*_api.json` — pre-exported API-format graphs already present:
  `zimage_img2img_api.json`, `flux2_klein_txt2img_api.json`, `flux2_klein_9b_uncensored_api.json`,
  `flux_img2img_api.json`, `flux_lora_img2img_api.json`, `chroma_img2img_api.json`,
  `pony_sdxl_api.json`, `pony_img2img_api.json`, `pony_bimbo_hires_api.json`, `wan22_i2v_api.json`.
- `studio_tools.py` — `TOOLS[]` + `execute_tool(name, tool_input, project_dir)` dispatcher
  (line ~319). `model` enums already list `comfyui`. `studio_mcp.py` exposes these as MCP tools.
- `cli/box.ps1` / `cli/ilyrium.ps1` — desktop SSM driver + REPL. They ship `cli/ilyrium_gen.py`
  to the box and run it with the ComfyUI venv python. `cli/README.md` documents the CLI.

**Also read** the sibling renderers `media/{tensorart,astria,fal,runway}_renderer.py` to match
the return-path-or-raise contract and the `compose_prompt(..., engine=...)` Style Kernel usage.

---

## 2. Layer 1 — Pipeline can run ANY registry model via `comfyui:<id>`

**Outcome:** `producer.py` accepts model specs like `comfyui:zimage`, `comfyui:flux2`,
`comfyui:flux2-klein-9b-uncensored`, `comfyui:<any comfyui-provider registry id>`. The bare
`comfyui` keeps working (defaults to a sensible model, e.g. `zimage`).

**How models are declared (this is where "any model incl. abliterated" lives):**
- Extend `model_registry.json`: add `comfyui`-provider entries for each on-box model, each with
  a new field **`workflow`** (path under `comfyui_workflows/`, the `_api.json` to use) OR a
  **`recipe`** block (unet/clip/vae/latent/steps/cfg/sampler/scheduler) mirroring
  `ilyrium_gen.py`'s `MODELS`. Add at minimum: `zimage`, `flux2`, and the uncensored/abliterated
  variants that already have files (`flux2_klein_9b_uncensored`, and the
  `qwen3_4b_zimage_abliterated` text encoder is already on the box). Abliterated models are just
  another registry entry pointing at their safetensors — no special handling.
- The registry entry is the ONLY place a model is defined. Adding a future model = one JSON entry
  + (if graph-based) one `_api.json`. Document this in the registry `note`.

**Dispatch change in `producer.py::_render_video`:** replace the `if m == "comfyui"` branch with
one that also matches `m.startswith("comfyui")`, parses `comfyui:<id>`, looks the id up in the
registry, and calls the shared engine (§3) with that model's workflow/recipe. Keep applying
`compose_prompt(visual_prompt, kernel, engine="comfyui")`.

**Acceptance:** `render_shot(project, dir, N, model="comfyui:flux2")` and `model="comfyui:zimage"`
each produce a real image via the box; an unknown `comfyui:bogus` raises a clear error (not a
silent fallback). Add the new model ids to the `model` enums in `studio_tools.py` (both places)
and to any `model_select.py` scoring that filters by provider.

---

## 3. Layer 2 — ONE shared engine module (no duplicate ComfyUI logic)

Create **`media/comfyui_engine.py`** — the single source of truth for talking to ComfyUI. It
absorbs the graph-building + edit logic currently in `cli/ilyrium_gen.py` and the HTTP
submit/poll/download logic currently in `media/comfyui_renderer.py`. Public API (keep it small
and typed):

```
build_graph(model_spec, prompt, *, seed, width, height,
            img=None, mask=None, region=None, denoise=0.65) -> dict   # ComfyUI API graph
submit_and_wait(graph, base_url, timeout) -> str                       # returns saved file path, RAISES on failure
upload_image(path, base_url) -> str                                    # /upload/image -> stored name
make_region_mask(region, w, h) -> str                                  # PIL rectangle mask -> input dir
gen_prompt(idea, hint, base=None) -> str                               # qwen3-coder (ollama), keep_alive:0
MODELS / load_model(model_id) -> recipe                                # from model_registry.json (see §2)
```

- `build_graph` supersedes `ilyrium_gen.build_wf` (txt2img / img2img / inpaint / region) AND the
  token-injection path. Support BOTH: (a) programmatic recipes (from registry `recipe`), and
  (b) a template `_api.json` with `__PROMPT__`/`__IMAGE__`/`__SEED__` tokens (from registry
  `workflow`). Choose based on which field the registry entry has.
- `submit_and_wait` replaces `comfyui_renderer._run_workflow` and `ilyrium_gen.render`. **It
  RAISES on failure** (see §5) — no empty fallback files.
- Reuse `ec2_session` for `COMFYUI_URL` / `is_comfyui_up`.

**Rewire both callers to the shared engine (delete their private copies):**
- `media/comfyui_renderer.py`: keep the public functions `render_scene_comfyui`,
  `render_i2v_comfyui`, `upload_comfyui_image` (producer + films/ depend on these — see
  `films/woods_of_west/render_film.py`, `app.py`), but reimplement them as **thin wrappers over
  `comfyui_engine`**. Preserve their exact signatures and return-path contract so nothing
  upstream breaks.
- `cli/ilyrium_gen.py`: it runs ON THE BOX (imports must work in the box venv). Reimplement it as
  a thin CLI over `comfyui_engine`. IMPORTANT: `comfyui_engine` must be importable on the box —
  either make it dependency-light and ship it alongside `ilyrium_gen.py` via `box.ps1`, or keep
  `ilyrium_gen.py` self-contained but factor the SHARED graph/edit logic into functions that are
  byte-identical to `comfyui_engine`'s (documented as the canonical copy). Prefer: `box.ps1`
  ships BOTH `ilyrium_gen.py` and `comfyui_engine.py` to the box. Confirm the box venv has PIL +
  requests (it does — z_imager uses PIL).

**Acceptance:** grep shows ComfyUI `/prompt` + `/history` + `/view` calls exist in exactly ONE
module (`comfyui_engine.py`). Both `comfyui_renderer.render_scene_comfyui(...)` and the CLI
produce images. The CLI's `:img` / `:mask` / `:region` / iterative-edit still work end-to-end
(verify via `cli/box.ps1 gen` and one REPL edit).

---

## 4. Editing through the pipeline (the "access all editing tools" half)

Editing does NOT become a batch stage. Instead expose it via **`studio_tools.py` + `studio_mcp.py`**
so an agent (or the console) can edit a shot/asset:
- Add tools: `edit_image(image_path|take_id, change, model, denoise)` and
  `inpaint_image(image_path|take_id, change, model, region|mask)` that call
  `comfyui_engine.build_graph(..., img=..., mask=..., region=...)` + `submit_and_wait`.
- These operate on an existing produced image (a take's file, or an arbitrary path) and write a
  new take/version. Register in `TOOLS[]` and `execute_tool`'s dispatch, mirroring the existing
  entries' shape. Expose in `studio_mcp.py` as `@mcp.tool()`.

**Acceptance:** `execute_tool("edit_image", {...})` returns a new image path; `inpaint_image`
with a `region` changes only that box (reuse the verified region-mask path).

---

## 5. Guardrails / non-negotiables

1. **Kill the fallback-file anti-pattern.** `comfyui_renderer.py` currently writes empty `.png`
   files on every failure and returns them as if success. In `comfyui_engine.submit_and_wait`,
   **raise** a clear exception instead. Update the pipeline's error handling
   (`producer.py` / `error_handling.py`) to treat a raise as a failed take (it already records
   failed takes) rather than depending on empty-file sentinels. This is a behavior change — call
   it out and keep it contained to the ComfyUI path.
2. **Preserve all public signatures** that `producer.py`, `app.py`, and `films/` import
   (`render_scene_comfyui`, `render_i2v_comfyui`, `upload_comfyui_image`). Grep for every caller
   first; don't break them.
3. **GPU VRAM (learned the hard way):** the L4 has 23GB and qwen3-coder alone loads ~21GB. The
   engine's `gen_prompt` MUST pass ollama `keep_alive: 0` so qwen releases the GPU before the
   image render, or ComfyUI OOMs. Keep this.
4. **Don't hardcode the stale instance id.** Use `ec2_session.INSTANCE_ID`
   (`i-04b439af98c8faf5e`). The old `i-030994c5371ee5de9` is dead.
5. **SSM payloads:** the box is driven over `aws ssm send-command`. Multi-line scripts must be
   base64-wrapped (see `box.ps1::Send-SsmCommand`) — Windows PowerShell 5.1's ConvertTo-Json
   mangles JSON. Don't regress this.
6. **Do NOT touch `intake-spine`** — it's an unrelated media-ingestion tool in a separate repo.
7. **Scope discipline:** don't refactor the other renderers (tensorart/astria/fal/runway) or the
   pipeline state machine. Only the ComfyUI path + registry + the two new studio tools.

---

## 6. Suggested task order (checkboxes for tracking)

- [x] Read §1 files; grep all callers of the three public renderer fns; list them.
- [x] Write `media/comfyui_engine.py` (build_graph + submit_and_wait[raises] + upload +
      make_region_mask + gen_prompt + registry-backed load_model). Unit-test build_graph offline
      (assert node graphs for txt2img/img2img/inpaint/region without hitting the box).
- [x] Add `comfyui:<id>` registry entries (zimage, flux2, abliterated variants) with
      `workflow`/`recipe` fields; document the "add a model = one entry" convention in the note.
- [x] Rewire `media/comfyui_renderer.py` to thin wrappers over the engine (keep signatures).
- [x] Rewire `cli/ilyrium_gen.py` to the engine; make `box.ps1` ship both files to the box.
- [x] Extend `producer.py::_render_video` to parse `comfyui:<id>` via the registry.
- [x] Add `edit_image` / `inpaint_image` to `studio_tools.py` + `studio_mcp.py`; update `model`
      enums.
- [x] Verify (box up): `render_shot(model="comfyui:flux2")`, `render_shot(model="comfyui:zimage")`,
      one CLI `:region` edit, one `execute_tool("inpaint_image", ...)`. Confirm only ONE module
      holds ComfyUI HTTP calls. Stop the box after (`cli/box.ps1 stop`) to end billing.

## 7. Verification commands

```powershell
# from apps/auto-studio/
cli\box.ps1 start                          # boot + ComfyUI (auto)
python -c "import producer; print(producer.render_shot.__doc__)"   # imports still resolve
# render via pipeline with an explicit model:
python -c "from media.comfyui_renderer import render_scene_comfyui; print('ok')"
cli\box.ps1 gen "a red fox" -Model flux2   # CLI path still works
# ... run the two studio tools ...
cli\box.ps1 stop                           # END BILLING
grep -rn "/prompt" media/ cli/             # expect hits in comfyui_engine.py ONLY
```

**Definition of done:** pipeline renders any `comfyui:<registry-id>` model (incl. abliterated);
CLI editing tools unchanged for the user; exactly one module owns ComfyUI HTTP; failures raise
(no empty fallback files); box stopped; a short note added to `cli/README.md` + this plan checked
off.
