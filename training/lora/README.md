# training/lora - image-LoRA toolchain (relocated from slm-foundry)

Relocated on 2026-11-06 by the RELOCATION lane (Phase B). These are image-LoRA tools (ostris
ai-toolkit bootstrap, Flux/SDXL render, diagnostics, EC2 box queue scripts), not SLM engine code.
Provenance and per-file SHA-256: `docs/receipts/2026-11-06-relocation-packs.md`.

## Files
- `bootstrap_aitk.sh`, `bootstrap_vision.sh`, `bootstrap_smoke.sh` - ai-toolkit install and smoke check on the box.
- `smoke_flux.py`, `diag_loras.py`, `diag_features.py`, `render_loras.py`, `render_samples.py` - Flux/LoRA diagnostics and renders.
- `auth_check.sh`, `run_queue.sh`, `run_render_validation.sh`, `run_train_both.sh`, `run_broderick_only.sh` - box queue and validation scripts.
- `launch_stripe_train.sh` - legacy Flux-only launcher (bounded capacity retry). Whole file moved; local source
  paths were rewritten to `projects/stripe/_training/`. Test: `tests/test_stripe_launch_errors.py`.
- `RENDER_COMFYUI.md` - ComfyUI render notes.

## Known caveats (open decisions, see the receipt)
- **Box paths are unchanged.** The scripts run on the EC2 box and still reference `~/slm-foundry/packs/...`
  and `~/slm-foundry/.env` there. The box layout is not part of this repository; changing it needs a
  deliberate box-side decision.
- **CRLF.** The files that were untracked in the Foundry checkout (`bootstrap_smoke.sh`, `smoke_flux.py`,
  `diag_*.py`, `render_loras.py` here; others under `projects/stripe/`) were committed byte-for-byte with
  Windows line endings so their SHA-256 matches the source. Normalise with `dos2unix` before running a
  shell script on Linux.
- Nothing here has been run as part of the relocation (no model calls, no box start).
