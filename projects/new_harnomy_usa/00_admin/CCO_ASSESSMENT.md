# CCO ASSESSMENT — NEW HARNOMY, U.S.A.

*Capacity assessment and process plan. 2026-09-01. Supersedes the sequencing (not the tooling) of `PRODUCTION_PLAN.md` v1, 2026-08-15.*

---

## 0. Verdict in three lines

- **Picture: YES.** Ilyrium can generate ~165 minutes of identity-locked, provenance-tracked picture for $500-$7,000 of generation cost. This capability is real, verified, and unusually well governed.
- **Sound: NO — not as currently resourced.** The studio has 20+ video/image engines and zero score capability proportionate to a three-hour sung-through opera. This is the binding constraint. It is a commissioning decision, not a tooling gap.
- **Endurance: UNPROVEN.** Longest finished Ilyrium piece to date is 2:00. Target is 165:00. An 82x jump.

**Ilyrium can produce this film. Not in the order the current plan proposes, and not until the score question is answered by hearing something rather than by choosing from a table.**

---

## 1. What the studio actually has (verified 2026-09-01)

### Generation
| Capability | State |
|---|---|
| Video engines | 20+ registered. Seedance 2.0 (i2v/t2v, start+end frame, 21:9, 4k), Seedance 2.5 (4-30s **native single takes**), Kling 3.0, Veo 3.1, Runway Gen-4.5 + Gen-4 Aleph (non-destructive edit) |
| Sung close-ups / lip-sync | `seedance2:ref` and `seedance2.5:ref` accept audio references. **This is the real unlock for opera** and it is already wired |
| Long holds | Seedance 2.5 does the 22-second read and the 20-second Listening beat as ONE take. No chaining artifacts on the two beats that most need stillness |
| Stills / keyframes | FLUX.2 Klein (4B + 9B), Z-Image Turbo on-box; Higgsfield Soul Cinematic at 0.12 cr/still; Soul Location for 21:9 plates; nano-banana-pro for 14-reference edits |
| Identity lock | On-box LoRA training per principal; Astria FaceID; Soul-ID **blocked on FREE plan** |
| Voice | ElevenLabs, wired |
| 3D | Unreal Engine on EC2 (proven on the Kathy flyby) |

### Governance — the studio's quiet advantage
Shot-spec schema with validation, an append-only provenance ledger with chain verification, C2PA signing, a release gate with a no-likeness legal check, style validation and eval rubrics, an append-only FINDINGS registry. Most AI production outfits have none of this. It is what makes a three-hour work auditable instead of a pile of clips.

### Project state — further along than it looks
`projects/new_harnomy_usa` was scaffolded 2026-08-15 and is genuinely at Stage 6 on the bookends:
- Full bible: 6 character files, world rules, timeline, THE_FRAMEWORK (Ten Principles), PRODUCTION_BLUEPRINT, canon reconciliation **decided** (reading A)
- 17 scene cards; both bookend numbers carded (NH-S101, 10 cards / NH-S348, 7 cards)
- **26 schema-valid shot specs** with manifests, render-ready
- Beat-timed storyboards for the opening 90 seconds and the finale six beats
- Voice-casting brief, score brief with the fixed cues, environment and prop specs

---

## 2. What it does not have

| # | Gap | Severity | Note |
|---|---|---|---|
| G1 | **A score.** 48 numbers, character-specific idioms, a motivic fragment that must return three hours later, a compositionally-specified bitonal final chord | CRITICAL | No AI tool composes this. `generate_music_bed` (Suno) is a bed generator, not a composer |
| G2 | **Sung diction at length.** AI vocals holding one character voice with intelligible operatic diction across 48 numbers | CRITICAL | Unproven anywhere, not just here |
| G3 | **A libretto.** 46 of 48 numbers are empty slots. No words exist between the bookends | CRITICAL | Brad's authorship. No money or GPU accelerates it |
| G4 | **Scale.** Kathy Flyby 2:00; King Size 0:50. Nothing longer has ever been finished | HIGH | 82x jump |
| G5 | **GPU serialization.** AWS G-family quota is **8 vCPU = exactly one g6.2xlarge**. Both boxes cannot run at once | MEDIUM | Verified via service-quotas. ~1,300 shots through one L4 is the Path A throughput floor. Request a quota increase before Act I |
| G6 | Higgsfield FREE plan blocks Soul-ID | LOW | Blocks the cheapest identity-locked keyframe (0.12 cr). On-box LoRA is the workaround already specced |
| G7 | Stage 3 not started. `anchors/` empty, `lora_library.json` empty | LOW | Canon was decided 2026-08-15. Nothing has been rendered since |

---

## 3. The creative problem no document has named

v11 §XI says it outright: the pre-show immersion, the chorus claiming the house from the vomitoria, and the refused curtain call **"are not atmospheric flourishes. They are load-bearing. Without them, the opera can still be performed; it cannot be experienced as intended."**

All three are liveness devices. They work because the audience is in a room, together, unable to leave. The thesis is literally *"You did not come to watch. You came to attend."*

**A film cannot trap anyone.** Streaming least of all. Someone will watch this in bed with a phone in their hand.

Film the opera as written and the satire survives, the tragedy survives, the warning survives — and the **witness** does not. v11 asks for four things. A straight capture delivers three.

This is the decision the whole production hangs on, and the current plan treats it as an asset-generation chore (Phase 10: "lobby/pre-show content"). It is not. The question is not how to reproduce the lobby. It is: **what is the film's equivalent of the closing fist?**

### Three frames

**Frame 1 — The Filmed Opera.** Capture the stage work. Cheapest fidelity to v11. But it inherits the problem and solves nothing: the camera becomes a spectator, which is precisely the posture the opera attacks. Not recommended.

**Frame 2 — The Feature Adaptation.** Drop the opera frame; a narrative feature with sung numbers. Solves liveness by not needing it — but discards the best idea in the document (a model opera inverted) and turns 48 numbers into an unfundable musical. Not recommended.

**Frame 3 — The Recursive Frame. RECOMMENDED.**

The film is a *recording of the world premiere of New Harnomy, U.S.A.* — a prestige artifact of a performance that never happened. House camera, lobby camera, backstage camera. The audience inside the film is New Harnomy's own progressive community, attending a satire about themselves and not recognizing it.

The viewer at home watches an audience fail to see itself — which is exactly what the opera does to its characters. **The Wildean law extends to the frame.** No wink, no narrator, no "based on."

Why this is better than the stage version rather than a lesser copy:

| v11 device | On stage | In Frame 3 |
|---|---|---|
| Pre-show immersion | Lobby dressing | Cold-open vérité: LYSTERIA table, petition volunteer, mauve program books, natural wine. No titles. The film starts before the film starts |
| Chorus from the vomitoria | Surrounds the room | The house camera is *inside* the surround. A camera problem you can actually win |
| The 22-second read | A long time in a theater | A long time on a face in close-up. **Longer** |
| The Mafia Wife Coronation | Read from row K | Pengold's hand, Summer's face, the smallest possible smile — held. The single strongest argument for a camera |
| The refused curtain call | Audience unsure whether to clap | **Hold on a filmed audience that does not know whether to clap.** Cut to black at eight seconds. The home viewer sits in a room having just watched a room fail |

It also solves a production problem: audience and chorus reaction shots are the cheapest thing this pipeline makes, and in Frame 3 they are the shots that carry the thesis.

**The risk** is the mockumentary trap. One wink and it dies. Mitigation: the Wildean law is already a constitutional invariant of this project. Extend it to the frame explicitly and enforce it at the release gate as a scored criterion.

---

## 4. Process plan — re-sequenced

`PRODUCTION_PLAN.md` v1 is sound operations and its tooling calls stand. Its **sequence is wrong**: it front-loads what Ilyrium is already good at (pixels) and defers what it has never done (music, endurance). Invert that. Prove the hardest thing first, on the smallest surface.

Every gate below is kill-or-continue.

### Gate 0 — The Frame Decision · 1 week · Brad alone
Pick Frame 1, 2, or 3. Nothing downstream is stable until this is answered — it changes shot specs, environment plates, the finale, and the entire marketing surface.
**Exit:** written decision in `01_development/bible/`, kernel version bumped.

### Gate 1 — The Music Proof · 4-6 weeks · BEFORE ANY MORE PICTURE
Not the score. Three artifacts, at final quality:
1. **The Cellist's Fragment** — 8-16 bars in Valencia's modal idiom
2. **Valencia's Final Aria** — ~90 seconds, sung end to end
3. **The Unresolved Chord** — bitonal, accumulating, severed

Why these three: the fragment-to-aria motivic return across three hours is the hardest thing in the score to fake, and the aria is the only music in the opera that must survive a sustained close-up. If (2) cannot be produced at a quality that holds that close-up, the entire enterprise is a $15k animatic and it is better to know now.

The A/B/C score decision (human composer / AI vocals / hybrid) gets made **by listening**, not by choosing from a table.
**Exit:** three audio files, and a named score path with a budget.

### Gate 2 — The Vertical Slice · 6-8 weeks · the finale, not the bookends
Ninety seconds — NH-S348, the six beats — finished to release quality. Score, sung, lip-synced, graded, C2PA-signed, with the eight seconds of black intact.

Not the opening. The finale contains every hard problem at once: sung close-up, crowd, a rising portrait, a locked stage picture, three contractual silences, and a hard cut. If the finale works, everything downstream is easier. If it does not, you learned it for ~$200 instead of $7,000.

Assets already exist: 12 shot specs, beat-timed storyboard, prop specs for the portrait and the mauve book.
**Exit:** $/finished-second, hours/finished-second, engine mix locked — and the honest question: *does it move you?*

### Gate 3 — The Libretto · 12-16 weeks · Brad's pacing item
The true critical path. No GPU touches it.

**Recommendation: do not write 48 numbers.** Write the **Act I spine — 16 numbers — to final**, and hold Acts II-III at treatment. Act I is where you learn whether the Economic Silence device survives 55 minutes, and that answer should shape Acts II-III rather than arrive after they are written.
**Exit:** Act I libretto, scene cards, timecode map.

### Gate 4 — Act I Production · 10-14 weeks
~430 shots. Box for holds and wides; Seedance for hero close-ups and lip-sync beats. Ledger on. Request the G-quota increase first (G5). Stop the box when idle.
**Exit:** Act I first cut.

### Gate 5 — The Endurance Test · 1 week · a real kill gate
Watch Act I straight through with someone who has not read v11.

The Wildean law's failure mode is **tedium, not offense**. Fifty-five minutes of characters being earnestly oblivious can flatten into one joke told sixteen times. This gate has a genuine kill option: if Act I does not hold, re-plan Acts II-III shorter rather than proceeding on faith.

### Gates 6-8 — Acts II-III · picture lock · release
As `PRODUCTION_PLAN.md` Phases 6-10. Unchanged.

---

## 5. Budget and schedule — honestly

Generation cost is the small number and the existing plan has it right: **$500-$7,000** for the whole opera depending on tier.

The real budget is elsewhere:

| Line | Estimate |
|---|---|
| Generation (mixed tier) | $500-$7,000 |
| **Original score + performances** (Frame 3, human composer path) | **$20,000-$60,000** |
| ElevenLabs, EC2, Higgsfield plan | ~$500 |
| Idle AWS storage (see 2026-09-01 cost review) | $47/mo — trim it |
| Brad's libretto authorship | Not purchasable |

The v1 plan's 26 weeks is optimistic by roughly 2x if the score is commissioned, because a composer cannot start on a libretto that does not exist. **Realistic: 12-18 months to a finished three-hour master.**

**Which is the strongest argument for the strongest recommendation in this document: do not produce the three-hour opera first.**

1. The finale, as a 90-second proof (Gate 2)
2. **Act I as a standalone ~55-minute film**, released

Act I ends with Summer beginning the affair, Dick awaiting a grant that will never come, and Pengold already calculating. That is a complete first movement and a far better fundraising artifact than a treatment. Ship something.

---

## 6. Housekeeping found during this audit

| Item | Action |
|---|---|
| `ilyrium-autostudio/CLAUDE.md` is **PermitHub's** project contract | Replace. It will mislead every future session in this repo |
| **Shared `NH-` ID namespace.** `NH-S05` is KING SIZE's song ID (23 specs, 27 keyframes, 177 ledger lines), and it sits in the same flat `ilyrium-shots/shots/` directory as New Harnomy's `NH-S101`/`NH-S348`. Two productions, one prefix, one folder | Namespace the shots directory per project, or re-prefix King Size, before Act I adds ~430 more specs |
| `anchors/` and `lora_library.json` empty since canon was decided | Stage 3 has not started. It is the input to everything at Gate 2 |
| Both GPU instances stopped since 2026-08-08; $47/mo idle EBS | Snapshot and trim, or accept the floor deliberately |
| v11 divorce-date inconsistency (FINDINGS NH-USA-002) | Writer decision, still open |

