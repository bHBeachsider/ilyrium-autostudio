# Nast Pack

Automated Thomas Nast political satirist. Shape A (Brain: event -> allegory + image prompt) and
Shape B (Hand: SDXL+Flux style LoRAs). See `../../docs/specs/2026-06-09-nast-reference-pack-design.md`.

Build (Brain): `python packs/nast/brain/build_dataset.py` -> `python src/prepare.py` ->
`python src/train.py --config packs/nast/brain/config.yaml` -> `python src/evaluate.py --config ... --judge`.
