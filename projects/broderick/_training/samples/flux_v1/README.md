# Broderick Hand — Flux v1 sample renders

Mirror of `s3://ilyrium-slm-foundry/models/broderick/hand/flux/samples/`.
These all belong to the **v1 style LoRA** (`broderick_flux.safetensors`), which is
**superseded** by v2 (`brdrck` → `broderick_flux_v2.safetensors`). Kept here as the
provenance trail for the caption-binding investigation that motivated the v2 retrain.

Three groups:

| Prefix | What it is |
|---|---|
| `broderick_0000N` | ai-toolkit training samples emitted during the v1 run (2026-06-12). |
| `diag_*`, `bf16_*` | Caption-binding **diagnostics** (2026-06-13). `diag_trig_*` = bare `brdrck` trigger at varying steps → mannequins (trigger inert). `diag_rich_*` / `diag_richNoTrig_*` and `bf16_*` isolated the cause: the style bound to description **words**, not the trigger token — and bf16-base vs fp8-base was ruled out (same mannequins). This is the evidence that v1's trigger was dead. |
| `final1-4` | The 4 real Broderick ink deliverables, produced via the rich-prompt workaround while v1's trigger was inert. |

**Conclusion that drove v2:** long content+style captions made the `brdrck` trigger
inert. v2 retrains on 173 panels with short trigger-only captions (`brdrck style`) so
the bare trigger fires the style on its own. v2 samples will land under
`../flux_v2/` and the character LoRA samples under `../char/`.
