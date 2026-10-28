---
name: qwen-ec2
description: Manage the Ilyrium Qwen EC2 box (Ollama models behind Claude Code) - connect, check status, list/select/pull models, warm swaps, stop the instance. Use when Brad says "connect to qwen", "start the qwen box", "qwen status", "is the tunnel up", "switch model", "use qwen3", "select the coder model", "pull a model", "write video prompts with qwen3", "stop the qwen box", or anything about choosing which local LLM the EC2 connection serves.
---

# Qwen EC2 box - connection and model selection

The box: a **g6e.xlarge** (NVIDIA L40S 48GB, us-east-1, Name tag
`ubuntu-qwen-gpu`) running Ollama with an Anthropic-compatible API. An SSH
tunnel maps `localhost:11435` -> box `11434`. Claude Code sessions in this
project route to it via `.claude\settings.local.json` (ANTHROPIC_BASE_URL).
Cost: ~$0.70/hr while running - always offer to stop it when work is done.

> **CHANGED 2026-09-02.** The box was snapshotted and TERMINATED as part of the
> AWS trim (540 GB of idle gp3 was costing $43/mo). There is no instance to
> start. Relaunch from `ami-04ef6582604f56a4a`
> (`ilyrium-qwen-ollama-20260901`) with
> `Ilyrium\tools\skills\ilyrium-ec2-session\scripts\launch_from_ami.ps1 -Box qwen`,
> then run `start_qwen.ps1`. The instance ID below is resolved from the Name
> tag at runtime - do not hardcode one, a terminated instance never returns
> under the same ID.
>
> Earlier revisions of this file called the box a g6.2xlarge with an L4 24GB.
> That was wrong; it is a g6e.xlarge with an L40S 48GB, which is why two large
> models were tight rather than impossible.

Helper scripts (all in the worktree root, all ASCII, PowerShell 5.1):

| Task | Command |
|---|---|
| Bring everything up (start instance, refresh SG, tunnel, verify) | `powershell -ExecutionPolicy Bypass -File .\start_qwen.ps1` |
| List models on the box (+ which is loaded / default) | `powershell -ExecutionPolicy Bypass -File .\qwen_model.ps1 list` |
| Set the project-default model and warm it | `powershell -ExecutionPolicy Bypass -File .\qwen_model.ps1 select <name>` |
| Load a model into VRAM without changing default | `powershell -ExecutionPolicy Bypass -File .\qwen_model.ps1 warm <name>` |
| Download a new model onto the box | `powershell -ExecutionPolicy Bypass -File .\qwen_model.ps1 pull <name>` |
| Relaunch the box (nothing exists to start) | `..\..\..\..\Ilyrium\tools\skills\ilyrium-ec2-session\scripts\launch_from_ami.ps1 -Box qwen` |
| Stop the instance (compute off, EBS still bills) | `aws ec2 stop-instances --region us-east-1 --instance-ids (aws ec2 describe-instances --region us-east-1 --filters "Name=tag:Name,Values=ubuntu-qwen-gpu" "Name=instance-state-name,Values=running" --query "Reservations[0].Instances[0].InstanceId" --output text)` |
| Terminate (preferred if idle more than a few days) | same lookup, `terminate-instances` - relaunch from the AMI later |

## Quick status check

1. Tunnel + models: `Invoke-RestMethod http://localhost:11435/api/tags` - if it
   fails, the tunnel or box is down; run `start_qwen.ps1`.
2. What is loaded right now: `Invoke-RestMethod http://localhost:11435/api/ps`
3. Instance state: `aws ec2 describe-instances --region us-east-1 --filters "Name=tag:Name,Values=ubuntu-qwen-gpu" --query "Reservations[].Instances[].State.Name" --output text`

## Model roles

- `qwen3-coder:30b` - coding sessions (the usual default).
- `qwen3:30b` - general/creative text. Use it to WRITE PROMPTS for the video
  and image generation models (Wan, Kling, Veo, Runway, flux, z-image - see
  `apps/auto-studio/model_registry.json`). It is better than the coder at
  cinematic language, shot descriptions, and camera direction.

Only ONE large model fits comfortably at a time; `select`/`warm` swaps it
(~30-60s). Both stay on disk, so swapping back is equally fast.

## Selecting a model

Two ways, pick per situation:

- Per-session (no config change): launch with an explicit model, e.g.
  `claude --model qwen3:30b` - Ollama loads whatever is asked.
- Project default: `.\qwen_model.ps1 select qwen3:30b` - updates
  ANTHROPIC_MODEL in `.claude\settings.local.json` and warms the model.
  Every subsequent plain `claude` (and `qwen-lite.ps1` / `qwen-render.ps1`)
  session uses it.

## Video-prompt workflow (qwen3 writes prompts for render models)

1. Ensure box + tunnel are up (`start_qwen.ps1` if needed).
2. `.\qwen_model.ps1 select qwen3:30b` (or launch `claude --model qwen3:30b`).
3. Ask it for shot prompts - give it subject, mood, camera, duration, and the
   target engine's strengths from `apps/auto-studio/model_registry.json`.
4. Stills can be test-rendered immediately via
   `python apps/auto-studio/render_image.py --model flux|z-image --prompt "..."`.
5. Switch back for coding: `.\qwen_model.ps1 select qwen3-coder:30b`.

## Gotchas (learned the hard way)

- Ollama env on the box is tuned in `/etc/systemd/system/ollama.service.d/override.conf`
  (context 65536, flash attention, q8 KV cache, parallel=1). If Claude Code
  ever gets empty or one-token replies again, check `journalctl -u ollama | grep truncat`
  on the box - truncated must be 0.
- To run a REAL Anthropic model in this project use `.\anthropic.ps1`
  (the local settings redirect everything else to the box).
- The instance IS currently terminated (2026-09-02). Relaunch from AMI
  `ilyrium-qwen-ollama-20260901` (`ami-04ef6582604f56a4a`), then re-run
  start_qwen.ps1. The older `ami-08e9e64ea96722690` is superseded.
  Models pulled after the snapshot are NOT in the AMI - re-pull after relaunch.
- Only ONE GPU box can run at a time: the AWS G-family quota on this account is
  8 vCPU. A g6e.xlarge is 4, so a g6.2xlarge cannot run alongside two of them.

## Routing fixes (2026-07-11) - read before debugging connection errors

- The tunnel is canonical on LOCAL port 11435 -> box 11434. Do NOT bind the
  local side to 11434: the Windows Ollama app (ollama.exe) owns 11434 when it
  runs, and every helper script here assumes 11435. start_qwen.ps1 is the one
  true way to open it.
- Claude Code NEVER reads .env. Routing lives in .claude\settings.local.json
  (env block). The ANTHROPIC_* lines still in .env are dead weight.
- settings.local.json pins "model": "qwen3-coder:latest" at PROJECT scope.
  Reason: a user-level default from /model (e.g. opus[1m]) OUTRANKS the
  ANTHROPIC_MODEL env var and would be sent verbatim to Ollama -> "model may
  not exist or you may not have access". That error in this dir almost always
  means the request went to the tunnel, not an Anthropic entitlement problem.
- Ollama 0.31+ (strict llama.cpp grammar validation) 400s with "Failed to
  initialize samplers: failed to parse grammar" when Claude Code sends the
  full global plugin toolset. Global plugins are therefore DISABLED at
  project scope in settings.local.json and RE-ENABLED in
  settings.anthropic.json so anthropic.ps1/qwena sessions keep them.
- anthropic.ps1 (alias: qwena) is the only way to use real Anthropic models
  in this dir. Verified working 2026-07-11 with sonnet-4-6, fable-5 and
  fable-5[1m].
