# Models on the NH box (i-0169c83c3cef9d621, g5.2xlarge, A10G 24 GB)

ComfyUI runs as a systemd service (`comfyui`) on port 8188; reach it through an SSH tunnel
(`ssh -i ~/.ssh/ubuntu-qwen-gpu.pem ubuntu@<ip> -L 8188:127.0.0.1:8188`) or run the generation scripts on the box
itself. Model files live under `~/ComfyUI/models/`.

| Role | File | Source | Licence |
|---|---|---|---|
| Diffusion (keyframes from the world) | `diffusion_models/flux1-dev-fp8.safetensors` | black-forest-labs / Comfy-Org fp8 | **FLUX.1-dev Non-Commercial License** — see below |
| Text encoders | `text_encoders/t5xxl_fp8_e4m3fn.safetensors`, `text_encoders/clip_l.safetensors` | comfyanonymous/flux_text_encoders | Apache-2.0 (T5) / MIT (CLIP) |
| VAE | `vae/ae.safetensors` | black-forest-labs/FLUX.1-dev | FLUX.1-dev NC (ships with dev) |
| Depth ControlNet | `controlnet/flux1-dev-controlnet-union-pro-2.0.safetensors` | Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro-2.0 | FLUX.1-dev NC (derivative) |
| (present, unused by backlot) | flux-2-klein-4b, z_image_turbo, wan2.2 i2v 14B fp8, cyberrealistic Z | — | per model card |

## Licence flag — read before any paid delivery

FLUX.1-dev and every ControlNet trained on it are released under the **FLUX.1 [dev] Non-Commercial License**.
Generating keyframes with them for a commercial release of NEW HARNOMY (or any paid client work) needs a
commercial licence from Black Forest Labs, or a switch to a permissively licensed base:

- FLUX.1-schnell (Apache-2.0) — 4-step, weaker prompt adherence, fewer ControlNets.
- Pay-per-use hosted FLUX.1-dev / FLUX Kontext (BFL API, fal.ai) — commercial use covered by the API terms.
- Z-Image-Turbo (already on the box) — check its card for a depth ControlNet before relying on it.

Until that is settled, treat world-conditioned keyframes as **development/validation output** for the Phase 1 gate
measurement, and route final keyframes through the paid API path recorded in `cost_preflight.py` (nano-banana-pro
edits from the passes, or hosted FLUX with the same depth conditioning).

## Settings that worked (Phase 1)

`generate_keyframe.py` defaults: 1344×768, 28 steps, euler/simple, guidance 3.5, ControlNet strength 0.7,
end 0.8, depth pass from `usd/render_passes.py` (near 2 m white → far 120 m black, 16-bit PNG). Union Pro 2.0
does not need a control-type embedding; the depth image alone selects the mode.

## Not installed (deferred)

FLUX.1-Redux / IP-Adapter for plate-style transfer — deferred: the prompt's shared `dress`/`look` clauses carried
the look well enough for the gate, and Redux tends to override layout text. Revisit if the judge (Phase 2) flags
material drift between shots.
