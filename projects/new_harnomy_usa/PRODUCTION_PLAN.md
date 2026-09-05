# NEW HARNOMY, U.S.A. — step-by-step production plan

*Version 1 — 2026-08-15. Runs the whole 3-hour / 48-number opera through the Ilyrium autostudio pipeline
(scaffold v2 stages → ilyrium-shots render engine → editorial → release gate). Every step names the tool
that does it, who owns it (Brad / agent / me from the studio MCP), the gate it must pass, and whether the
studio UI is involved. Cost lines are generation costs at the prices verified 2026-08-15; music, voice talent
and human time are called out separately.*

## 0. The shape of the job (so the numbers below make sense)

| Quantity | Estimate | Basis |
|---|---|---|
| Running time | ~10,800 s (3 h incl. two intermissions; ~165 min of picture) | v11 §VII |
| Numbers | 48 (Act I ≈16 · II ≈16 · III ≈16; split adjustable) | v11; IDs NH-S1nn/2nn/3nn |
| Shots | **~1,250–1,400** at a 7–8 s average (opera holds run long; the bookends came out at 7.2 s/shot) | bookends: 26 shots / 188 s |
| Keyframes | one per shot (~1,300) + ~25 environment plates + prop macros + 4–6 hero anchors | Stage 5 |
| Principals / ensemble | 4 principals + Philip (offstage) + chorus types (6–8 recurring faces) + City AG, officers, house manager, cellist | bibles |
| Locations | ~15–25 (office, LYSTERIA, PILF, festival grounds, gala, feast hall, lobby, theater, streets/bodega/church) | world files |

Two production paths exist and both are already wired; the plan uses each where it is strongest:

- **Path A — the box (`ilyrium-shots`)**: spec → keyframe (FLUX + character LoRA) → Wan 2.2 i2v → chained
  provenance ledger, on the EC2 L40S. Cheapest by far (~EC2 hours), full control, LoRA identity, but 640×640-class
  output today (upscale later) and no native lip-sync until Wan2.2-S2V is installed (`docs/ON_BOX_LIPSYNC_PLAN.md`).
- **Path B — cloud engines via `producer.py`** (campaign/take model in `outputs/<project>/project.json`):
  `seedance2` / `seedance2.5` (fal), `kling` / `veo3.1` (fal), `higgsfield:*` (optional), `keyframe:*`, `runway`.
  Higher fidelity, 21:9, native audio/lip-sync, priced per second.

The default mix this plan assumes: **Path A for drafts and every hold/wide; Path B (Seedance 2.0/2.5 or Kling std)
for hero close-ups, lip-sync beats and anything 21:9-critical.** The pilot (Phase 1) exists to test that mix.

## 1. Do we need to open the studio UI? — No, not to produce it. Yes, to look at it.

Everything below is scriptable or callable through the Ilyrium studio MCP from this chat (I already used
`scaffold_project` that way), through the CLI scripts, and through the box's `box.ps1` / the `ilyrium-ec2-session`
skill. Studio rule "script, don't click" applies (memory 2026-05-27): the two UIs — the control-panel console
(`:3000/studio/console`, needs the `:8800` pipeline service) and the Streamlit AutoStudio — are for **previewing
results, browsing takes visually, and the Studio Chat**, not for configuration or fixes.

When the UI is worth opening: (a) selecting among takes for a whole number (a grid beats reading `project.json`),
(b) the A4 release approval if you want the risk queue in front of you (`get_approval_queue` / `approve_release`
work from MCP too), (c) DaVinci Resolve for the final 3-hour assembly (driven by the OTIO export + Resolve
scripting, per "script don't click"; the GUI is for watching).

Operational notes for the MCP path: restart the studio MCP once so it loads the new `producer.py` (a running server keeps
old code); if project state "flip-flops", kill zombie `studio_mcp.py` processes; `generate_first_cut` always exceeds the
60 s MCP timeout — poll `outputs/<campaign>/project.json`, don't re-fire.

## 2. Phases, steps, gates

### Phase 0 — Ready-to-run checks (½ day; me + Brad)
| # | Step | Tool / command | Gate |
|---|---|---|---|
| 0.1 | Restart studio MCP; confirm tools list | `list_tools`, `list_models` (should show `seedance2`, `seedance2.5`, `higgsfield*`) | 29 registry entries visible |
| 0.2 | Keys present in `.env`: FAL_KEY, ELEVENLABS_API_KEY, APIFRAME_API_KEY (Suno/MJ), R2, XAI; optional Higgsfield plan | `account_status` / env check | no missing key for the chosen engine mix |
| 0.3 | Box health: start, tunnel, ComfyUI 8188 up, `models.lock.json` roles resolve; STOP when idle | `ilyrium-ec2-session` skill / `apps/auto-studio/cli/box.ps1 start|tunnel|status|stop` | ComfyUI green |
| 0.4 | Set the per-job cost caps deliberately | `.env`: `HIGGSFIELD_MAX_CREDITS_PER_JOB=…`; fal budget policy (E1 generic hook proposed) | written down |
| 0.5 | Confirm canon (done: reading A) and the number split per act | `CANON_RECONCILIATION.md`; `06_audio/score/song_list.md` | Brad sign-off |

### Phase 1 — Pilot: the two bookends end-to-end (1–2 weeks; proves the pipeline and fixes the engine mix)
Inputs already exist: `02_script/numbers/NH-S101_*.scenes.json`, `NH-S348_*.scenes.json`, 26 shot specs, storyboards, plates/prop macros.

| # | Step | Tool | Owner | Gate |
|---|---|---|---|---|
| 1.1 | Hero anchors for the 4 principals (front, ¾, close-up; 21:9 + 3:2), from the 🔒 LOCKED VISUAL DESCRIPTORs | `higgsfield:soul_cinematic` (0.12 cr/still) or `comfyui:flux2` on the box; save `03_design/characters/anchors/<key>.png` | me → Brad approves | QA_CHECKLIST: no real-person likeness; canon (reading A) honored |
| 1.2 | Identity assets: train one LoRA per principal on the box (`train_lora.py`, register in `03_design/characters/loras/lora_library.json`); Soul-IDs only if the Higgsfield plan is upgraded (`SOUL_ID_PLAN.md`) | ilyrium-shots Stage-3 tools | me | verification stills match the anchor |
| 1.3 | Environment plates: Pengold's office at dawn; the Feast stage (portrait half-height + apex); auditorium/proscenium | `soul_location` 21:9 or FLUX on box; `03_design/environments/<loc>/plate_v1.png` | me | kernel look; mauve reads brownish; no legible text |
| 1.4 | Prop macros: mauve book (4 states), Summer's Socialist-Realist portrait from her anchor | `higgsfield:nano_banana_pro` (14 refs) / fal nano-banana-pro (`edit_image_text`) | me | portrait face == anchor |
| 1.5 | Keyframes for the 26 shots (anchor + plate refs; descriptors restated) | Path A: `keyframe_to_comfy.py --spec … --template wan_t2i.api.json` · Path B: `higgsfield:soul_cinematic` w/ Soul or FLUX.2 multi-ref | me | storyboard framing; continuity to prev shot |
| 1.6 | Scratch audio: Pengold's recitative, Dick's line, Valencia's line, the Confirmation (ElevenLabs), room tone/thump/cough (seed_audio or library) | `render_voiceover` / `voice_gen.py`; `06_audio/voice/voice_casting.md` | me → Brad picks voices | lines are words only; register held |
| 1.7 | Render A: whole NH-S101 + NH-S348 on the box (Wan 2.2 i2v, FLF2V for holds) | `batch_render.py render --manifest ilyrium-shots/song_NH-S101.json --models models.lock.json --ledger-dir ledger` | me | ledger chain_ok; 26 takes |
| 1.8 | Render B: the same 26 shots through cloud engines for comparison — holds via `higgsfield:kling3_0` or fal `kling`; lip-sync beats via `seedance2:ref` (audio ref = 1.6 takes); the 22-s read + 20-s Listening as single takes via `seedance2.5` | MCP: `set_script` (cards → project) → `generate_first_cut(model="seedance2")`, `regenerate_shot(..., model="seedance2.5")`; or `render_i2v_fal` / `render_reference_video_fal` directly | me | cost per shot logged; takes in `project.json` |
| 1.9 | Assemble both bookend cuts at the **contractual timings** (22 s / clarinet line / 8 s black; hard cut, no fade); score placeholder from `score_brief.md` cues | `reassemble_cut` (campaign) or OTIO → Resolve (`otio_export.py`) | me | silences intact; durations exact |
| 1.10 | QA + eval on both cuts; decide the engine mix, resolution target, and $/finished-minute | `run_style_validation`, `run_eval`, `run_release_qa`; A/B review | Brad | **Pilot gate:** look locked; mix decided; budget per act approved |

Pilot generation cost (from live prices): box ≈ 1–2 h EC2; cloud B ≈ 23 shots × 8 s: Kling std ≈ $17–26 (Higgsfield) or fal Kling; Seedance 2.0 720p ≈ $57 per full pass; stills ≈ $4 or box time.

### Phase 2 — Script: libretto → scene cards → shot specs for all 48 numbers (4–8 weeks, parallel with 3–4)
| # | Step | Tool | Owner | Gate |
|---|---|---|---|---|
| 2.1 | Number plan: fix the act split and title every slot in `06_audio/score/song_list.md` (only v11-named numbers exist today) | Story Architect / Screenwriter agents: `stage_ideate(project="new_harnomy_usa", stage="00_bible" / "01_script", …)` | Brad (author) + agents | no invented plot; Wildean law; Economic Silence |
| 2.2 | Libretto per number (`02_script/libretto/libretto.md`; surtitles) — sung/spoken words only, stage directions in brackets | `stage_ideate("01_script")`; Screenwriter | Brad + agent | writer decides the two open v11 items (divorce date; Confirmation placement) |
| 2.3 | Scene cards per number → `02_script/numbers/NH-S<id>_<slug>.scenes.json` (descriptors restated; camera words the bridge understands; `duration_target_s` from the score's timecode map once it exists) | Screenwriter agent → `conformance.py` lint | agent → me | strict-conformant cards; durations sum to the number's length |
| 2.4 | Bridge each number → shot specs + manifest | `bible_to_shotspecs.py --scenes … --song-id NH-Sxyz --max-shot-s 10 --seed-base xyz000 --schema …` | me | all specs schema-valid; ref_lora resolves after 3.2 |
| 2.5 | Register sequences/scenes/shots in the asset graph | `graph_sync` (best-effort, automatic) | — | Project→Sequence→Scene→Shot rows |

### Phase 3 — Score, voices, and the timecode map (critical path; parallel with 2; owner Brad)
The score IS the drama, and this is where the plan needs your decision, not a tool: **(A) human composer + recorded
singers**, lip-synced onto picture via `seedance2:ref` / on-box S2V; **(B) AI-synthesized vocals** (Suno v5.5 voice
clones per character; open ACE-Step) — fast, but sung diction/legato over 3 h is the quality risk; **(C) hybrid** —
AI demo score for animatics and timing (Phase 2–5), human performances replace it before Phase 8. Whatever the answer:
| # | Step | Tool | Gate |
|---|---|---|---|
| 3.1 | Fixed cues composed/produced first: the fragment; the bass note; "Competing Anthems"; the TWEEEDS theme; the clarinet line; the chord | `score_brief.md`; Suno prototypes via `generate_music_bed` for animatic only | Brad approves |
| 3.2 | Voice casting locked (ElevenLabs ids in `voice_casting.md`) for recitative/scratch; singers per (A/C) | ElevenLabs; `06_audio/voice/` | one voice per character |
| 3.3 | **Timecode map per number** (music-video-pack pattern: the track is the fixed input; the edit locks to it) → feeds `duration_target_s` in 2.3 | `06_audio/track/timecode_map.md` (add the music_video pack dirs) | every shot has a TC in/out |

### Phase 4 — Character & world lock (2–3 weeks; before mass keyframes)
| # | Step | Tool | Gate |
|---|---|---|---|
| 4.1 | Anchor set for every recurring face (4 principals + ~8 chorus/ensemble types + City AG etc.), 3 angles each; wardrobe boards from the bibles | as 1.1; `gather_references()` for period/wardrobe research | LEGAL GATE (no likeness); canon |
| 4.2 | LoRA (box) — and Soul-ID if plan upgraded — per principal; registry entries | 1.2 | verification stills pass |
| 4.3 | Environment plates for all locations (day/night variants; 21:9) | `soul_location` / FLUX; `03_design/environments/` | look; motifs |
| 4.4 | Prop macros: mauve book states, portrait states (poster/small/half/apex), program book, lanyards | nano-banana refs | mauve spec |
| 4.5 | Kernel revision if the pilot changed anything (`style_kernel.json` version bump; dependents flagged) | — | recorded |

### Phase 5 — Keyframes, act by act (~1,300 stills; 1–2 weeks per act with batching)
| # | Step | Tool | Gate |
|---|---|---|---|
| 5.1 | Batch keyframes per number from specs (Path A `keyframe_to_comfy.py`, or Soul/FLUX.2 multi-ref) | manifests | storyboard framing; descriptor restated |
| 5.2 | Continuity pass: prev-shot chaining, portrait seeding, book states | `continuity.py` / QA | flagged drift → regenerate only that keyframe |
| 5.3 | Approve keyframes per number (Brad, visual — the one place a UI grid genuinely helps) | console / contact sheets | approved set |

Cost: box time, or ~$0.01/still on Higgsfield Soul; nano-banana ~2 cr for reference edits.

### Phase 6 — Shots, act by act
| # | Step | Tool | Gate |
|---|---|---|---|
| 6.1 | Path A renders for every shot (draft/first cut) | `batch_render.py` per manifest; ledger | chain_ok; every shot has a take |
| 6.2 | Path B upgrades where the pilot said so (hero close-ups, 21:9 wides, lip-sync beats, long holds via 2.5) | `regenerate_shot(scene, model="seedance2"|"seedance2.5"|"kling"|"higgsfield:kling3_0")`; `render_reference_video_fal` for audio | cost cap per job; take appended, never overwritten |
| 6.3 | Select takes per number | `select_take` (MCP) or console | rubric: register held; cut on stillness |
| 6.4 | Fixes without re-rolling: Runway Aleph edits (`edit_shot`), Seedance 2.5 edit/extend (`seedance2.5:ref`), on-box inpaint (`inpaint_image`) | studio tools | regenerate only the failing take |

Cost per **hour of finished picture** (~450 shots): box ≈ 12 EC2-hours (~$25); Kling std ≈ $300–550 per pass (Higgsfield 2 cr/s) or fal Kling; Seedance 2.0 720p ≈ $1,080 per pass ($2,700 at 2.5 takes avg); Seedance 2.5 ≈ $1,700 per pass. Mixed default (box + 20% premium) ≈ $300–600 per hour of picture.

### Phase 7 — Performance & lip-sync passes
Sung close-ups: `seedance2:ref` (audio ref = the recorded/synth line; ≤3 audio) or Wan2.2-S2V on the box once installed;
wides/holds need no lip-sync (opera convention). Barrier rule (Higgsfield-derived): all audio takes for a number complete
before any lip-sync render; 1:1 pairing recorded in the manifest.

### Phase 8 — Editorial (per act, then whole)
`otio_export.py` → DaVinci Resolve (scripted add; manual delete — `DeleteClips` is unreliable); timings contractual (22 s
read; clarinet line; 8 s black; intermissions); surtitles from `libretto/surtitles.md`; the chord is a hard cut. Deliver
act masters, then the 3-hour master. Gate: `edit_notes.md` rubric; runtime.

### Phase 9 — QA, rights, release (non-delegable)
`run_style_validation` + `run_eval` per act; `run_release_qa` (no-likeness legal gate, negatives scan); rights records
(composer, singers, any voice clone consent) in `00_admin/rights_releases/`; C2PA manifests (`c2pa_sign.py`) into
`09_delivery/c2pa_manifests/`; `approve_release(no_likeness_confirmed=true, …)` — Brad, A4.

### Phase 10 — Delivery & marketing
Masters to R2 (`publish.py` / `delivery.py`); platform cuts (`reframe` 9:16 for teasers); captions; key art (Ideogram/Recraft
for text; hero portraits reused; `10_marketing/keyart/`); trailer from NH-S101 + finale beats; lobby/pre-show content
(program book, LYSTERIA table poster) per `PRODUCTION_BLUEPRINT.md`.

## 3. Milestones & rough calendar (agent-assisted; Brad's authorship is the pacing item)
| Milestone | Deliverable | When (from 2026-08-15) |
|---|---|---|
| M1 Pilot reel | both bookends assembled, QA'd, engine mix + budget decided | +2 weeks |
| M2 Libretto + number plan | 48 numbers titled, libretto v1, timecode maps for Act I | +6 weeks |
| M3 Act I cards + specs + keyframes approved | ~430 keyframes | +8 weeks |
| M4 Act I first cut | box renders + premium upgrades, assembled | +10 weeks |
| M5 Acts II–III | same, staggered | +16–20 weeks |
| M6 Picture lock + score final | 3-hour master, QA green, release approved | +24 weeks |
| M7 Delivery | masters, platform cuts, key art, trailer | +26 weeks |

## 4. Budget scenarios (generation only, whole opera, ~1,300 shots / 10,800 s)
| Scenario | Video | Stills/keyframes | Total order of magnitude |
|---|---|---|---|
| Draft / animatic — all box | ~35 EC2-hours ≈ $70 | box | **~$100** |
| Standard — box holds + Kling std for ~30% (hero/lip-sync) | ~3,000 s × $0.10–0.15 ≈ $300–500 + box | Soul stills ≈ $15 or box | **~$500–700** |
| Premium — Seedance 2.0 720p everywhere, 2 takes avg | 10,800 × 2 × $0.30 ≈ $6,500 | — | **~$7k** |
| Prestige — Seedance 2.5/2.0 + Veo 3.1 hero shots, 3 takes | — | — | **$10–15k** |
Not included: composer/singers or Suno credits, ElevenLabs, EC2 for LoRA training, Higgsfield plan (Basic+ only if Soul-ID wanted), Brad's and agents' time.

## 5. Owner map
- **Brad**: libretto/number plan (with agents), score decision (A/B/C), voice picks, keyframe/take approvals, canon changes, release approval, money.
- **Me / studio agents (MCP + scripts)**: everything mechanical — bridging, batching, renders, QA runs, assembly, docs, cost previews, ledger, delivery.
- **The box**: drafts, holds, LoRAs, plates; must be STOPPED when idle.

*Companion docs:* `START_HERE.md` · `01_development/bible/PRODUCTION_BLUEPRINT.md` · `04_preproduction/storyboards/*` ·
`docs/HIGGSFIELD_PROCESS_FLOW.md` · `docs/ON_BOX_LIPSYNC_PLAN.md` · `docs/PIPELINE_ALIGNMENT.md`.
