# Stage 3.9 / 3.10 — the four character LoRAs

Four FLUX.1-dev character LoRAs, 125 MB each, trained 2026-09-03 on fal's
`flux-lora-portrait-trainer` at 2000 steps from the 18-image sets in
`../training/sets/`. About 35 minutes and **$19.20** for all four.

| Character | File | sha256 (first 12) | Verdict |
|---|---|---|---|
| Valencia Strong | `valencia_strong_nh.safetensors` | `f514cc3825b7` | PASS |
| Summer Winters | `summer_winters_nh.safetensors` | `fe7fb5926f3d` | PASS |
| Pengold Heavens | `pengold_heavens_nh.safetensors` | `f54f380aa45f` | PASS |
| Dick Suede | `dick_suede_nh.safetensors` | `093d00976fb0` | PASS, one gap |

All four registered in `ilyrium-shots/lora_library.json` (schema-validated).

**The weights are NOT in git.** At 125 MB each they follow this studio's existing
convention (see the broderick and stripe entries): they live at
`s3://ilyrium-slm-foundry/models/new_harnomy/` and are pulled onto the render box with
`aws s3 cp ... ComfyUI/models/loras/`. The repo keeps the `.meta.json` sidecars, the
training configs, the verification sheet and the scripts.

## Why fal and not the repo's own trainer

`ilyrium-shots/train_lora.py` drives Tensor.art against endpoint paths that were
never verified — every one returns 405 — and its urllib transport sends no
User-Agent, so Cloudflare answers 403 `error code: 1010` whatever the token is
(NH-USA-019). No trainer is installed on the EC2 box either. fal's portrait
trainer is verified, runs on the funded balance, needs no box, and returns a real
portable `.safetensors` — unlike Astria, whose tunes expire and yield no
checkpoint (NH-USA-013).

`flux-lora-portrait-trainer` over `flux-lora-fast-training` because these are
faces: it crops to the subject and trains multiresolution. 2000 steps rather than
its 2500 default — 18-image sets converge well before 2500 and it bills per step.

## HOW TO USE THESE — read before prompting

**1. The trigger token does not bind. Describe the character anyway.**
This library has validated twice that a bare Flux trigger is inert
(`broderick_char`, `broderick_flux_v2` in `lora_library.json`). Name the trigger
*and* describe the character in the prompt. Verified again here — the tests that
pass do both.

**2. Summer's radiance is NOT in her weights, by design.**
Her beatific quality is a *lighting* fact (NH-USA-020), and the training set
deliberately varied lighting so the LoRA learns her face rather than her key
light. The shot must supply it: a soft luminous key from just above and in front
wrapping the cheekbones, a glow at forehead and temples, a bright catchlight in
each eye, the brow unfurrowed, the lips resting closed rather than pressed.
Baking it in would have given us a woman who glows in a basement.

**3. Dick's man-bun is a known gap.**
All 18 of his training frames wear the hair down, so the LoRA does not reliably
produce the Act III bun even when prompted — confirmed in verification. For bun
shots, supply `../casting/finals/DIC-K02-bun-v2.png` as reference conditioning,
or train a small supplementary set. This matters to the plot: Summer's initiative
is *The Man Bun Collective*, and the rhyme only lands if the bun appears.

## Verification (3.10)

Each LoRA was tested on **two out-of-set scene prompts** — a bus stop in the rain,
a boardroom, a corridor, a beach — never a portrait, because a LoRA that only
works on its own training shots is worthless. Contact sheet: `_verify/_VERIFY_SHEET.jpg`.
Identity generalised on all four. Dick showed the most variance between his two
tests and is the weakest of the set, though still recognisably one man.

## Reproducing

The training images are gitignored (100 MB of PNGs) but fully reproducible: the
seeds are pinned at `770000 + index` in `../training/gen_trainset.py`. Regenerate
the set, re-zip, re-run `train_loras.py`.
