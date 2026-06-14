# Broderick local artifacts (moved from Downloads 2026-06-14)

Working artifacts for the Broderick hand LoRAs. Curated proof images also live in
`../samples/{char,flux_v2,flux_v1}/`; this is the fuller raw dump.

- **`loras/`** — the trained `.safetensors` (broderick_char, broderick_flux_v2, and v1
  broderick_flux). **Gitignored** (165MB each) — canonical copies are in
  `s3://ilyrium-slm-foundry/models/broderick/hand/{char,flux_v2,flux}/` and registered
  in `ilyrium-shots/lora_library.json`.
- **`renders/`** — first validation pass (bare-trigger; mostly failed — generic/photoreal).
- **`diag/`** — controlled base/v1/v2 × rich/bare comparison that proved the diffusers path
  is fine and the bare trigger is inert on Flux (`*_rich` strong, `*_bare` weak).
- **`char_salvage/`** — char LoRA + rich ink prompt + identity description → consistent avatar.
- **`samples_v1/`** — v1-era samples, diagnostics, sweeps; `keep/` holds final1-4 deliverables.

See [[reference_flux_lora_bare_trigger_inert]]: use the style block (+ avatar description
for characters), not a bare trigger.
