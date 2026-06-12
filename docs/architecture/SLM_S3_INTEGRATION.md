# SLM-in-S3 → Studio Console Integration

**Status:** RECOMMENDED design, 2026-06-12. Generalizes the serving pattern the
Creative Loop v1 plan ratified for the Nast vertical into studio-wide plumbing.
**Decision owner:** operator.

## What exists (observed)

- `s3://ilyrium-slm-foundry/` already has an emergent, good convention:
  `data/<artist>/{brain,hand}/…` (training corpora) and
  `models/<artist>/{brain,hand}/…` (artifacts). Today: nast brain (PEFT adapter
  **and** merged `nast-q4_k_m.gguf`, 4.7 GB), nast hand (flux + sdxl LoRAs),
  broderick hand (`broderick_flux.safetensors`, trained 2026-06-12).
- Creative Loop v1 (satirist app) already commits to: **Ollama serves the brain**
  (`nast-brain`, HTTP :11434), **lazy `aws s3 cp` fetch with skip-if-present**
  for the hand LoRA, env-var host config, GPU-only render module.
- Studio invariants this must respect: MCP is the call layer; filesystem/DB is
  the state layer; models are pinned by registry/lock files
  (`models.lock.json`, `lora_library.json`); cost-conscious (the GPU box stops
  overnight; no idle-billed managed endpoints).

## Decision: registry-driven pull-through cache + Ollama, exposed as MCP tools

S3 is **cold storage for bytes**. Identity, versioning, and wiring live in a
**registry file** in the repo. Serving is **Ollama for brains** and **the
existing LoRA path for hands**. The console never touches S3 directly — it
calls MCP tools.

### 1. Registry — `ilyrium-shots/slm_registry.json`
One entry per artifact (sibling convention to `lora_library.json`):

```json
{
  "nast_brain": {
    "artist": "nast", "organ": "brain", "kind": "gguf",
    "s3_uri": "s3://ilyrium-slm-foundry/models/nast/brain/nast-q4_k_m.gguf",
    "sha256": "<filled on first fetch>", "base": "qwen3-…", "quant": "q4_k_m",
    "serve": {"engine": "ollama", "model": "nast-brain"},
    "status": "active"
  },
  "broderick_hand_flux": {
    "artist": "broderick", "organ": "hand", "kind": "flux_lora",
    "s3_uri": "s3://ilyrium-slm-foundry/models/broderick/hand/flux/broderick_flux.safetensors",
    "trigger": "brdrck",
    "serve": {"engine": "comfyui", "dest": "loras/"},
    "status": "candidate"
  }
}
```

A `--sync` mode lists `s3://ilyrium-slm-foundry/models/` and proposes new
entries (never auto-activates; operator promotes `candidate` → `active`).

### 2. Fetcher — `ilyrium-shots/slm_fetch.py`
Generalizes the satirist plan's `fetch_lora`: registry-name in → local path
out. `aws s3 cp` only when missing or sha-mismatched; dest chosen by
`serve.engine` (Ollama import dir for gguf; ComfyUI `loras/` for hands; HF
cache layout for PEFT adapters). For gguf it also runs
`ollama create <serve.model> -f Modelfile` if the model isn't registered with
Ollama yet. Idempotent; safe at session start.

### 3. Serving
- **Brains (text):** Ollama on the GPU box — one daemon, one tunneled port
  (:11434), exactly the ComfyUI :8188 pattern the EC2-session skill already
  manages. GGUF is the preferred artifact (merged, quantized, no GPU fight
  with render jobs at q4 on CPU if needed). Dev/cheap path: the same gguf runs
  in Ollama **on the local PC** for 3–4B models — zero cloud cost for script
  punch-up while the box is off.
- **Hands (image LoRAs):** not "served" at all — fetched into the render
  engine's `loras/` and **registered in `lora_library.json`**, which makes
  `bible_to_shotspecs` ref_lora auto-wiring pick them up. The hand path rides
  the existing Stage-3 machinery; nothing new to operate.

### 4. Console/workflow integration — MCP tools (the call layer)
Add to the ilyrium-studio MCP server (thin wrappers, ~a day):
- `list_slm_models()` → registry + fetch/served state
- `slm_ensure(name)` → fetch + ollama create (idempotent)
- `slm_generate(artist, prompt, json_mode=False)` → POST Ollama
  `/api/generate`, host from env (`ILYRIUM_OLLAMA_HOST`, default the tunnel)
- `stage_ideate(project, stage, message, brain=<artist>)` — optional param so
  any pipeline stage can ideate **in the artist's own voice** instead of (or
  A/B against) the cloud LLM. This is the actual product moment: broderick's
  brain punching up broderick scripts inside the existing stage rooms.

The Next.js control-panel console calls the same pipeline-service endpoints it
already uses; no direct S3/Ollama coupling in the UI.

## Rejected alternatives
- **SageMaker real-time endpoints** — idle-billed; violates cost discipline
  for a stop-overnight studio.
- **Per-call S3 → transformers load** — 4.7 GB cold load per session, no
  pin/verify story, couples every caller to boto3.
- **Hardcoded per-app S3 URIs** (satirist v1 style) — right for the vertical
  slice, wrong as studio plumbing; the registry subsumes it (satirist's
  `NAST_LORA_S3` env default can later point through the registry).

## Phase 2 (when needed, not now)
- **Bedrock Custom Model Import** from the same S3 safetensors for
  pay-per-token serverless brains when the GPU box is off and local CPU is too
  slow. No idle cost; adds region/architecture constraints. Evaluate only if
  "box-off inference" becomes a real workflow gap.
- Per-artist eval gates before `candidate` → `active` (style-fidelity prompts,
  the with/without-trigger grid for hands).

## Migration of the in-flight work
Nothing breaks: satirist v1 keeps its env-var config. When this lands, its
defaults resolve via the registry, and `broderick_hand_flux` (already in S3)
becomes the first registry-promoted model — wire it into
`lora_library.json` under name `brdrck` and the shot-spec auto-wiring lights up
with zero further changes.
