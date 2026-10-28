# 02_script/numbers/ — one scene-card file per opera number (render unit)

`../scenes.json` is the master script (all authored cards, unique `scene_number`s). Because the
bible→shot-spec bridge emits **one song manifest per run** (`--song-id`), each opera number that is ready to
render also gets its own card file here, named `<SONG_ID>_<slug>.scenes.json`, and is bridged with `--scenes`:

```
python skills/ilyrium-project-setup/scripts/bible_to_shotspecs.py \
    --project projects/new_harnomy_usa \
    --scenes  projects/new_harnomy_usa/02_script/numbers/NH-S101_opening.scenes.json \
    --song-id NH-S101 --max-shot-s 10 --seed-base 101000 \
    --out-dir ilyrium-shots --schema ilyrium-shots/shot_spec.schema.json
```

Song IDs are act-based (`NH-S1nn` / `NH-S2nn` / `NH-S3nn`, nn = global number 01–48). Seed bases follow the ID
(`NH-S101` → 101000, `NH-S348` → 348000) so shot seeds are unique across the whole opera.

| File | Song ID | Cards | Total s | Status |
|---|---|---|---|---|
| `NH-S101_opening.scenes.json` | NH-S101 | 10 | 90 | bridged 2026-08-15 → `ilyrium-shots/song_NH-S101.json` |
| `NH-S348_finale.scenes.json` | NH-S348 | 7 | 98 (90 + 8 s black) | bridged 2026-08-15 → `ilyrium-shots/song_NH-S348.json` |

Card conventions used here (bridge-aware):
- Camera words in `visual_prompt` drive the shot spec: `extreme wide` / `wide` / `medium` / `close-up` /
  `two-shot` / `macro`; `locked-off` / `push-in` / `pull-out` / `tracking` / `pan` / `tilt` / `handheld`.
  The bridge matches substrings — avoid words like "company", "expand", "pane" (→ pan) unless intended.
- Every principal's 🔒 LOCKED VISUAL DESCRIPTOR (from `01_development/bible/characters/*/bible.md`) is restated
  verbatim in each card that features them (models have no memory between shots).
- `characters[0]` is the lead → `keyframe.ref_lora` forward-reference. Non-principal shots use `[]`.
- Cards with `location: "Black"` are slugs (post can replace with pure black; rendering them is harmless).
- `duration_target_s` > `--max-shot-s` splits into consecutive `flf2v`-chained shots (the 22-second read → 3 shots).
