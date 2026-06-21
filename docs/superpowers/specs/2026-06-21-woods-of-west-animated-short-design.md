# Design — "The Woods of the West" animated short

**Date:** 2026-06-21
**Source:** hand-drawn 6-panel comic strip (`C:\Users\bradu\Downloads\woods_of_west.png`)
**Goal:** Turn the comic into a short animated film (~2 min) with voiced dialogue, music, and SFX.

---

## 1. Creative decisions (locked)

| Decision | Choice |
|---|---|
| Visual style | **Bake-off then commit** — render a signature beat in 3 styles, pick one, finish in that style |
| Candidate styles | (a) Ballpoint sketch on lined paper, (b) Clean 2D cartoon (flat vector), (c) Stylized cinematic western (painterly) |
| Punchline | **Faithful — show the bulge**, run as-is (lumpy cartoon outline, framed like the comic). Local render = no content filter |
| Audio | Voiced dialogue + western music score + SFX |
| Length | ~2 min, fully expanded from the 6 panels |
| Aspect ratio | 16:9 cinematic |
| Voices | ElevenLabs TTS, per-character casting |
| Renderer | **Wan 2.2 image-to-video** in local ComfyUI (no external content filter) |

Dialogue is reproduced **verbatim** from the comic. No lines are rewritten.

---

## 2. Story & beat sheet (~24 shots @ ~5s)

Spine = the comic's 6 panels. Expansion adds establishing/tension shots for cinematic pacing.

**Cold open**
1. Black. Distant train whistle.
2. The 4:55 hisses into a dusty depot, steam billowing.
3. A stovepipe-hatted silhouette (Cal) steps down onto the platform.

**Act 1 — the warning** (Panel 1–2)
4. Jail/office interior. **Shakes** bursts in, pointing: *"Sheriff!! Ol' Cal Dalton just arrived on the 4:55, says he's got an old score to settle with you!!"*
5. **Sheriff Pringle** at the window, deadpan: *"Well, Shakes, I guess the time has come to play this hand..."*

**Act 2 — the walk** (Panel 3)
6. Empty street, shutters closing.
7. Tumbleweed / spurs / a ticking wall clock (tension inserts).
8. Cal strides up the street, top hat low.
9. Wide two-shot, the men face each other down the street. Cal: *"Sheriff Pringle... well well..."*
10. Pringle: *"H'lo, Cal..."*

**Act 3 — the face-off** (Panel 4)
11. CU Cal: *"It's been a while, but now it's payback time..."*
12. CU Pringle: *"You wouldn't shoot me, Cal..."*
13. CU Cal: *"Oh yeah? Why's that?"*

**Punchline** (Panel 5–6)
14. Pringle, smug: *"You wouldn't shoot a man with serious wood..."*
15. The reveal — lumpy cartoon outline, framed exactly as the comic.
16. Cal's flabbergasted reaction; a comedic button (he lowers the gun / is dumbfounded).
17. Freeze → **END** card.

> Shot count above is illustrative (17 named beats); the full ~2-min cut interleaves reaction inserts and holds to reach ~24 clips. Final shot list is produced in the planning step.

---

## 3. Character bible (kept on-model via bespoke-character-pipeline)

- **Shakes** — scruffy grey-bearded prospector, battered cowboy hat, gap-toothed, jabbing finger. Comic-relief informant. Appears Act 1 only.
- **Sheriff Pringle** — tall, gaunt, long pointed nose, droopy half-lidded eyes, star-badge hat. Deadpan straight man. The "serious wood" gag is his.
- **Cal Dalton** — villain. Stovepipe top hat, handlebar mustache, dark vest/suit, weathered glare. Appears cold-open onward.

Each character gets a reference sheet (front + 3/4 + profile) generated once and reused as image-edit refs so the face/wardrobe stays consistent across shots and across the style choice.

---

## 4. Voice casting (ElevenLabs)

| Character | Voice direction | `voice_id` |
|---|---|---|
| Shakes | Gravelly, frantic old-timer | TBD at cast time |
| Sheriff Pringle | Dry, slow Western drawl, deadpan | TBD at cast time |
| Cal Dalton | Low, menacing, smug | TBD at cast time |

Casting picks concrete ElevenLabs `voice_id`s in the planning step; `audio_generator.py` already accepts per-character `voice_id` + stability/similarity.

---

## 5. Pipeline (per shot)

```
character sheets   (Fal nano-banana-pro via bespoke-character-pipeline)
        |  reused as refs for consistency
keyframe still per shot   (Fal image gen, in chosen style)   <- the Wan start frame
        |
Wan 2.2 i2v in local ComfyUI   (comfyui_renderer.py, __PROMPT__ inject)  -> 5s clip
        |
audio: ElevenLabs dialogue + western score + SFX   (audio_generator.py)
        |
assemble / sync / color / END card   (post_production.py)  ->  outputs/woods_of_west/
```

**Why local Wan/ComfyUI:** the punchline renders as-is with no external content filter. ComfyUI runs on the EC2 GPU box over the existing SSH tunnel (`ec2_session.py` / `COMFYUI_URL`). Wan 2.2 blueprints already present: `ComfyUI/blueprints/Image to Video (Wan 2.2).json`.

**Workflow prep:** export the Wan 2.2 i2v blueprint via ComfyUI "Save (API Format)", place `__PROMPT__` in its positive prompt, set `COMFYUI_WORKFLOW` to that file.

---

## 6. Phases

**Phase 1 — style bake-off (do first)**
- Signature beat = the final face-off + "serious wood" reveal (shots 14–16, ~2–3 clips).
- Render that beat in **all three styles**.
- Deliver 3 comparison clips (~10–15s each) + their keyframes.
- **User picks the winning style.** Gate.

**Phase 2 — full film (winning style only)**
- Generate character sheets + all ~24 keyframes in the chosen style.
- Render all clips via Wan 2.2 i2v.
- Generate dialogue (ElevenLabs), score, SFX.
- Assemble the ~2-min 16:9 MP4 in `post_production.py`.

---

## 7. Deliverables

All under `apps/auto-studio/outputs/woods_of_west/`:

- **Phase 1:** `bakeoff/ballpoint/`, `bakeoff/cartoon/`, `bakeoff/cinematic/` — comparison clips + keyframes.
- **Phase 2:** `final/woods_of_west.mp4` (~2 min, 16:9, full audio) + `final/keyframes/` + `final/clips/` + `characters/` (reference sheets).

---

## 8. Risks & open items

- **Render time:** Wan 2.2 i2v is minutes-per-5s-clip on one GPU. ~24 clips for the full film is a multi-hour local render. Bake-off de-risks the look before committing that time.
- **Character drift across Wan motion:** i2v can warp faces. Mitigation — strong keyframes + short clips + the character-sheet refs; re-roll bad clips.
- **EC2/ComfyUI availability:** requires the GPU box up and the tunnel open before any render.
- **ElevenLabs voice fit:** `voice_id`s are provisional until audition in the planning step.
- **Music source:** which generator/library for the western score is TBD (ElevenLabs handles voice, not score) — resolve in planning.
