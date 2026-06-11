# Handoff prompt — Broderick style-LoRA training (paste into the training session)

Train a "broderick" comic-style image LoRA from a prepared, captioned dataset. All context you need is inlined below — do NOT re-derive or regenerate the dataset, and do not assume context from other sessions.

## Repo + branch state (verify first)
- Repo: C:\Users\bradu\Documents\ilyrium-autostudio (origin git@github.com:bHBeachsider/ilyrium-autostudio.git)
- The dataset-prep commit (f863a76, `ilyrium-shots/panels_to_dataset.py` + dataset manifests) is on branch `feat/creative-loop-v1`, NOT main. If you are on main and the files below are missing, `git log feat/creative-loop-v1 --oneline -2` and cherry-pick f863a76 or check out the files — do not rebase or reset that branch.
- Run `git branch --show-current` before any commit so your work lands where you intend.

## Dataset (already built and validated — use as-is)
- Location: `projects\broderick\_training\dataset_v0\`
- 190 training images in `images\` (173 grayscale / 17 color), each with a same-name `.txt` caption sidecar (kohya/ai-toolkit convention)
- `metadata.jsonl` = HF imagefolder format; `manifest.jsonl` = full provenance (sha256, dims, strip, color_mode, scene_numbers, rights_note)
- Trigger token: `brdrck` — every caption begins `brdrck style, <style line>. <scene content>.` Captions are natural-language (written for T5/Flux; fine for SDXL/Wan)
- `broderick_karate_kicks` (6 panels, vintage stock-art collage with residual watermarks) IS included — inclusion ratified by the artist (Broderick) 2026-06-11; its rows carry a rights_note in manifest.jsonl. The watermark remnants may teach watermark artifacts — if samples show watermark-like smudges, retrain filtering these 6 rows out via manifest strip == broderick_karate_kicks.
- Integrity check before training: 190 files in images\ matching 190 .txt sidecars and 190 metadata.jsonl rows; spot-verify 2-3 sha256 values against manifest.jsonl.

## Training targets (in priority order)
1. **Flux.1-dev style LoRA** (primary — best style fidelity + legible hand-lettering):
   - ai-toolkit (ostris) or kohya sd-scripts flux branch; low-VRAM mode if on the 24GB L4
   - resolution 1024, network dim 16 / alpha 16, lr 1e-4 (cosine), batch 1-2 + grad accum, ~2500-3500 steps for 184 images, save every ~500 steps
   - Consider a grayscale-only run first (filter via manifest color_mode == "grayscale", 167 images) since grayscale is the house style; the 17 color images can dilute it
2. **Wan-family LoRA** (pipeline compatibility — the render chain is Wan 2.2 t2i/i2v):
   - use the existing `ilyrium-shots/train_lora.py --config` flow (Tensor.art); images dir = `projects\broderick\_training\dataset_v0\images`, trigger `brdrck`, register with `--register` so it lands in `lora_library.json`
   - base_model must be the Wan-family base matching the render checkpoint (open question #1 in ILYRIUM-STAGE3-keyframe-and-lora.md — confirm before submitting)
3. SDXL only if Flux is blocked by VRAM/cost.

## Evaluation gate (before declaring done)
- Generate a 6-up sample grid per checkpoint: 3 prompts WITH `brdrck style` trigger, same 3 WITHOUT. The with/without delta should be obvious (scratchy grayscale ink, flat gray washes, white void, deadpan staging).
- Test prompts: (a) "brdrck style, two men arguing at an office desk, one holding a phone, white void background" (b) "brdrck style, a dog leaping at a child in a suburban yard" (c) "brdrck style, a man dancing alone, single red accent"
- LEGAL GATE: if any sample resembles a real public figure, note it and regenerate — characters are specified by attributes only.

## Outputs expected
- `.safetensors` + a `.meta.json` sidecar (settings, dataset sha manifest reference, base model id) under `ilyrium-shots/loras/brdrck_style/` (or Tensor.art download per train_lora.py flow)
- If Wan path used: entry registered in `ilyrium-shots/lora_library.json` (name matching `brdrck` enables auto-wiring into shot specs via bible_to_shotspecs ref_lora resolution)
- A short run report: steps, final loss curve shape, chosen checkpoint, sample grid path, and any deviation from the settings above with reasoning.

## Constraints
- Conventional commits; commit configs + sidecars + report, NOT image binaries or .safetensors >100MB (note storage location instead)
- Dataset is regenerated only via `python ilyrium-shots/panels_to_dataset.py` — never hand-edit dataset files
- Cost-conscious: confirm Tensor.art credit balance / GPU-hour estimate before launching paid runs; report estimate first if >$10
