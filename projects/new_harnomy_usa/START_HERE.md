# NEW HARNOMY, U.S.A. — production start (2026-08-15)

Scaffolded through the studio MCP (`scaffold_project`, canonical scaffold v2): **type FEATURE**, genre packs
**opera + narrative**, kernel **new_harnomy**. Source of truth ingested: `01_development/research/NEW_HARNOMY_USA_Overview_v11.pdf`.

**Production plan (phases, gates, costs, owners): `PRODUCTION_PLAN.md`.**

## What is populated (Stage 1–2 + the two bookends)

| Stage | Files | State |
|---|---|---|
| 1 Bible | `01_development/bible/narrative/{logline_treatment,tone}.md` · `world/{setting,factions,motifs,visual_signature,WORLD_RULES,TIMELINE,culture}.md` · `characters/{summer,pengold,dick,valencia,philip,bildersatz}/bible.md` · `THE_FRAMEWORK.md` (Ten Principles) · `PRODUCTION_BLUEPRINT.md` (pre-show, first 90 s, curtain-call problem, load-bearing silences) · `sequences.md` · `CANON_RECONCILIATION.md` (**decided 2026-08-15: reading A**) | drafted from v11; Stage-1 gate green except reference backlinks |
| 2 Script | `02_script/scenes.json` (17 cards) · `02_script/numbers/NH-S101_opening.scenes.json` (10 cards, 90 s) · `NH-S348_finale.scenes.json` (7 cards, 98 s) · libretto/song list skeleton `06_audio/score/song_list.md` (only v11-named numbers; 44 slots) | bookends authored; everything between is Screenwriter work |
| 3 Characters | `03_design/characters/SOUL_ID_PLAN.md` (Higgsfield Soul-ID per principal; blocked on Basic+ plan) · `CASTING_CANON.md` (reading A) · `anchors/` empty | anchors may be rendered now (canon decided) |
| 4 Env / props | `03_design/environments/{pengold_office_dawn,feast_stage_finale}.md` · `03_design/props/{mauve_framework_book,summer_portrait}.md` | plate prompts ready |
| 5 Storyboards | `04_preproduction/storyboards/NH-S101_OPENING_FIRST_90_SECONDS.md` · `NH-S348_FINALE_SIX_BEATS.md` | shot-by-shot with contractual timings |
| 6 Shots | **`ilyrium-shots/shots/NH-S101-SH001…014.json` (14) + `NH-S348-SH001…012.json` (12)**, manifests `ilyrium-shots/song_NH-S101.json`, `song_NH-S348.json` — all schema-valid | render-ready specs (keyframes/LoRAs forward-referenced) |
| 7 Voice / 8 Music | `06_audio/voice/voice_casting.md` (fach + line specs; voice ids TBD) · `06_audio/music/score_brief.md` (fixed cues: bass note, clarinet line, the chord, 8 s black) | briefs |

## Song / number IDs (studio decision)
Act-based: `NH-S1nn` (Act I) / `NH-S2nn` (Act II) / `NH-S3nn` (Act III), nn = global number 01–48.
Opening = **NH-S101**, finale = **NH-S348**. NH-S03 / NH-S05 belong to other pieces.

## Next commands
```
# develop any stage in conversation (kernel + canon in context)
stage_ideate(project="new_harnomy_usa", stage="01_script", message="...")

# re-bridge a number after editing its cards
python skills/ilyrium-project-setup/scripts/bible_to_shotspecs.py --project projects/new_harnomy_usa \
  --scenes projects/new_harnomy_usa/02_script/numbers/NH-S101_opening.scenes.json --song-id NH-S101 \
  --max-shot-s 10 --seed-base 101000 --out-dir ilyrium-shots --schema ilyrium-shots/shot_spec.schema.json

# cost a manifest through Higgsfield before spending (read-only)
python apps/auto-studio/media/higgsfield_renderer.py cost ilyrium-shots/song_NH-S101.json higgsfield:kling3_0

# render on the box (Wan 2.2) — start it with the ilyrium-ec2-session skill first
python ilyrium-shots/keyframe_to_comfy.py --spec ilyrium-shots/shots/NH-S101-SH005.json --template wan_t2i.api.json --emit-json
python ilyrium-shots/batch_render.py render --manifest ilyrium-shots/song_NH-S101.json --models models.lock.json --ledger-dir ledger
```

## Decisions needed from Brad
1. ~~Canon reconciliation~~ — **decided 2026-08-15: reading A** (kernel = casting, v11 = character); Stage-3 anchors may start.
2. Higgsfield plan upgrade (Basic+) if Soul-ID character lock is wanted; and a deliberate `HIGGSFIELD_MAX_CREDITS_PER_JOB`.
3. Whether the "Confirmation" line sits inside finale beat 4 or after it (v11 places it with the hand on the shoulder).
