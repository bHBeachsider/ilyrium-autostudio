# Spec: Box/tunnel switch in control-panel + multi-provider chat CLI (for Fable 5)

**Target executor:** Fable 5. **Repo:** `C:\Users\bradu\Documents\ilyrium-autostudio`.
**Apps:** backend `apps/auto-studio/studio_pipeline_service.py` (the :8800 service) and frontend
`apps/control-panel/`. **No git.**

## Goal
Two features for the control-panel studio console (`/studio/console`):
1. A **ComfyUI / box + SSH-tunnel on-off control panel with live status** — same capability the
   AutoStudio Streamlit app already has, but in the Next.js console, driven by new :8800 endpoints.
2. A **multi-provider chat CLI**: a chat panel with a **provider/model dropdown** that routes each
   message to the chosen LLM. **Ship local qwen3 (on the EC2 box via ollama :11434) FIRST** — it
   runs entirely on Brad's hardware, no external provider in the loop. Structure the provider layer
   so Claude / Gemini / Grok / Qwen-cloud plug in later via their own API keys (add stubs that
   activate when the key env var is present; do NOT hardcode or require keys that aren't set).

**Framing note (important):** this is legitimate multi-provider routing + local-model use. The
"unregulated" property comes from *choosing a provider that applies no policy layer* — i.e. the
local qwen3 / open models on Brad's box — NOT from defeating any provider's safety systems. Do NOT
build jailbreak/guardrail-bypass logic. Just route requests to the selected backend; each provider
(including local) is responsible for its own behavior. Local qwen3 goes direct to ollama.

## Ground truth (read first)
- **Backend:** `apps/auto-studio/studio_pipeline_service.py` — Starlette app, routes registered in a
  `Route(...)` list near the bottom. It ALREADY imports project/producer modules; import
  `ec2_session` (has `status()`, `ensure_running(wait, timeout)`, `stop()`, `is_comfyui_up(url,
  timeout)`). The box is `i-04b439af98c8faf5e`; ComfyUI at `http://127.0.0.1:8188` via the tunnel;
  ollama/qwen3 at `http://127.0.0.1:11434` via the tunnel. The SSH TUNNEL itself is opened by
  `apps/auto-studio/cli/box.ps1 tunnel` (and `tunnel-down`) — the service must shell out to it
  (subprocess, `pwsh` preferred then `powershell`, `-ExecutionPolicy Bypass`, resolve
  `cli/box.ps1` relative to the service file).
- **Frontend:** `apps/control-panel/app/studio/console/` — `ConsoleShell.tsx` (panel/zone layout),
  `Pipeline.tsx`, `Workspace.tsx`, `Stage1Bible.tsx`. The :8800 base URL is
  `process.env.NEXT_PUBLIC_PIPELINE_URL` (default `http://127.0.0.1:8800`); components read it as
  `pipe`. Match the existing dark UI classes (bg-panel/border-edge/text-fg/text-dim, small text).
- **Precedent:** `apps/auto-studio/app.py` already implements the box panel (status chips +
  Start/Tunnel/Stop, gating, 5s cache) and a qwen3 chat (`media/comfyui_engine.gen_prompt`). Mirror
  its behavior/wording. `apps/auto-studio/console_helpers.py` has `run_box_verb`, `box_status`,
  `comfy_up` — reference for the subprocess + status pattern (but the control-panel path goes
  through :8800, not in-process).

## Feature 1 — Box / tunnel control (backend endpoints + UI panel)

### Backend: add to studio_pipeline_service.py
- `GET  /box/status` → `{state, public_ip, comfyui_up, tunnel_up}` where state from
  `ec2_session.status()`, `comfyui_up` from `is_comfyui_up()`, `tunnel_up` inferred (ollama :11434
  reachable OR comfyui reachable while running). Cache the AWS `status()` ~5s (module-level
  timestamp) so polling doesn't spam AWS. Wrap in try/except → `{error}` (creds may be missing).
- `POST /box/start` → `ec2_session.ensure_running(wait=False)`; return status.
- `POST /box/stop`  → best-effort `box.ps1 tunnel-down` then `ec2_session.stop()`; return status.
- `POST /box/tunnel` → subprocess `box.ps1 tunnel` (fire-and-forget); return `{ok}`. Optionally also
  start ComfyUI on the box if it's not up (nice-to-have; if easy, run `box.ps1 run "sudo systemctl
  start comfyui"` — but keep it non-blocking).
- Register all four routes. Traversal/creds errors must return JSON errors, never 500 stack HTML.

### Frontend: a Box panel in the console
- A compact panel (in `ConsoleShell` as a zone, or a header strip) polling `GET /box/status` every
  ~5s: three status chips — **Box** (🟢 running / 🟡 pending|stopping / ⚪ stopped / 🔴 error),
  **ComfyUI** (🟢/🔴), **Tunnel** (🟢/⚪) — plus instance id + IP and a $1.20/hr note.
- Buttons: **▶ Start · 🔌 Tunnel · ⏹ Stop · 🔄 Refresh**, each POSTing the matching endpoint then
  refreshing status. Disable during pending/stopping. Errors shown inline, no crash.

## Feature 2 — Multi-provider chat CLI (provider layer + chat panel)

### Provider layer (new `apps/control-panel/lib/llm/`)
Create a small, pluggable text-chat abstraction (this is separate from the media `adapter-bus.ts`,
which is for image/video — do NOT overload it):
- `types.ts`: `LLMProvider { id, label, available(): boolean, chat(messages, opts): Promise<string>
  | AsyncIterable<string> }` and a `ChatMessage { role, content }` type.
- `providers/localQwen.ts`: talks to ollama at `NEXT_PUBLIC_OLLAMA_URL` (default
  `http://127.0.0.1:11434`) `/api/chat` with model `qwen3-coder:latest` (or
  `NEXT_PUBLIC_LOCAL_LLM_MODEL`). `available()` = a quick reachability check (or just true; the chat
  will error clearly if the tunnel's down). This is the DEFAULT provider. No API key.
- `providers/anthropic.ts`, `providers/gemini.ts`, `providers/grok.ts`, `providers/qwenCloud.ts`
  as STUBS: each `available()` returns true only when its key env var is set
  (`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`/`GOOGLE_API_KEY`, `XAI_API_KEY`/`GROK_API_KEY`,
  `DASHSCOPE_API_KEY` or an OpenAI-compatible `QWEN_BASE_URL`+`QWEN_API_KEY`). Implement the actual
  call where trivial (OpenAI-compatible POST covers grok/qwen-cloud/gemini-openai-compat); for ones
  needing an SDK you don't have, leave a clear `throw new Error("provider X not configured")` and
  mark `available()=false` — do NOT add heavy deps. The point is the ABSTRACTION + local qwen3
  working; cloud providers light up when keys exist.
- `index.ts`: `listProviders()` (only `available()` ones, local always first) + `getProvider(id)`.
- Do NOT route local qwen3 through any cloud SDK — it must hit ollama directly (no external calls).

### Backend passthrough (recommended to avoid browser CORS/keys)
The browser calling ollama :11434 directly may hit CORS. Cleaner: add a small proxy route the chat
posts to. EITHER a Next.js route `app/api/llm/chat/route.ts` that dispatches to the provider layer
server-side (keys stay server-side; ollama reached via localhost), OR a :8800 endpoint
`POST /llm/chat {provider, messages}`. Prefer the **Next.js `/api/llm/chat` route** (keeps LLM
concerns in the frontend app, keys in its server env). Local qwen3 from that server-side route hits
`http://127.0.0.1:11434` fine.

### Chat panel (in the console)
- A chat UI (message history + input) with a **Provider dropdown** at the top populated from
  `listProviders()` (label + a lock/○ hint for unavailable ones). Default = local qwen3.
- Send → POST `/api/llm/chat {provider, messages}` → render the reply (stream if easy). Show which
  provider answered. If local qwen3 is chosen and the tunnel/box is down, show a helpful message
  ("start the box + tunnel in the Box panel") — reuse the box status.
- This is a TEXT chat (conversation). It does NOT itself render images — but a nice bridge: if the
  user's message clearly asks for an image, you MAY (optional, only if clean) offer a "generate this"
  affordance that hands the text to the existing image path. Keep that optional; core deliverable is
  the multi-provider text chat with local qwen3.

## Guardrails
1. Scope: `studio_pipeline_service.py` + new `app/api/llm/chat/route.ts` + new `lib/llm/**` + the
   console panel components (Box panel + Chat panel, added via ConsoleShell/console page). Don't
   refactor unrelated console code. No git.
2. No new heavy dependencies. Use `fetch` for OpenAI-compatible/ollama providers. If a provider
   needs an SDK you don't have, stub it (available=false) rather than installing it.
3. Local qwen3 must NOT touch any cloud provider — direct ollama only.
4. No guardrail-bypass / jailbreak logic. Just route to the selected provider.
5. Box endpoints: cache AWS status ~5s; subprocess to box.ps1 for the tunnel; JSON errors not 500 HTML.
6. Restart note: the :8800 change needs a service restart to take effect; Next.js hot-reloads.

## Verification
- Backend: `py_compile studio_pipeline_service.py`. Start it on a temp port (or restart :8800) and
  curl `GET /box/status` → JSON with state/comfyui_up/tunnel_up (box may be running now — either way
  no 500). `GET /box/start` etc. exist (405 on wrong method proves the route). Show output.
- Provider layer: a node/tsx check that `listProviders()` returns local qwen3 first and that
  `getProvider('local-qwen')` exists; `npx tsc --noEmit` in control-panel → 0 errors.
- `/api/llm/chat`: if the box tunnel is up (ollama :11434 reachable), POST a tiny message with
  provider=local-qwen and show the reply. If not reachable, show that it returns a clean error, not
  a crash. (Do NOT boot the box just for this; if ollama is already reachable, do the live call.)
- Report: files changed + ranges; box-status curl output; provider-list + tsc output; a local-qwen
  chat reply (or the clean-error path); anything not wired + why; and a paragraph for Brad on how to
  use the box switch + pick a provider in the chat, incl. the :8800 restart reminder.

Begin by reading studio_pipeline_service.py (the route list + how existing endpoints are written),
ec2_session.py, the console page + ConsoleShell.tsx, and app.py's box-panel + chat for the pattern.
