# Storyboard — NH-S101 · "The First 90 Seconds" (opening)

> Source: v11 §XI (The First 90 Seconds) + §XI (Load-Bearing Silences: The Twenty-Two Seconds). Every timing
> below is contractual. Scene cards: `../../02_script/numbers/NH-S101_opening.scenes.json`. Shot specs are
> generated from those cards by `bible_to_shotspecs.py --song-id NH-S101` (max 10 s per shot → long holds are
> split into consecutive `flf2v`-chained shots).

**Total ≈ 90 s.** Aspect: 21:9 preferred (16:9 fallback). Kernel look throughout. Sound: silence → cough → cold
wash (silence) → 22 s silence → a single low bass note held → recitative → blackout → chorus from all around.

| # | t (s) | Shot | Frame / camera | Action | Sound | Notes |
|---|---|---|---|---|---|---|
| 1 | 0–10 | **The house, lights up too long** | wide, static; the auditorium from the stage side (or an interior of an audience) | People begin looking around. | room tone; murmur | Filmed: the audience *is* the first image. If no audience footage: hold on the dark proscenium curtain with houselight spill. |
| 2 | 10–13 | **Hard cut to black** | black | Nothing. Three full seconds. | one cough "sounds like a gunshot" | No dimmer, no fade. |
| 3 | 13–17 | **The proscenium** | wide, locked-off; a single cold wash on the proscenium arch lit *from the house side* | The ornament of the theater itself. Held four seconds. | silence | The audience sees the place they paid to sit in. |
| 4 | 17–22 | **Reveal: the office at dawn** | wide, locked-off, anamorphic; one room | Pengold's mayoral office at dawn (plate: `03_design/environments/pengold_office_dawn.md`). Pengold already seated. Lamp still on. Coffee. Folded newspaper. Three mauve books on the credenza. He is reading. He does not react to being seen. | silence | Kernel look; single-source tungsten; dawn thin at the window. |
| 5 | 22–44 | **The Twenty-Two Seconds** | medium, locked-off (one very slow push-in permitted across the 22 s), 50–65 mm | He actually reads, silently, the full beat, **page turn included** at ~34 s. Nothing else happens. | silence | *Load-bearing.* Split into 3 shots (8/7/7 s) chained flf2v: read → page turn → read. No performance; no eyebrow. |
| 6 | 44–50 | **The paper set down** | medium → close-up on hands/desk edge | Sets the paper down carefully, aligned to the edge of the desk. | silence; paper on wood | Squared to the edge — the character in one gesture. |
| 7 | 50–58 | **The unspoken breath** | close-up, locked-off, 85 mm; eyes to the middle distance (past the lens, never into it) | Looks toward the audience — not at us, past us. Inhales to speak. Holds. Exhales without having spoken. | silence → **first bar: a single bass note, low, held** (enters at ~55 s) | No smile, no gesture (kernel `acting_at_camera` fix). |
| 8 | 58–72 | **The recitative** | medium, static; slow tighten allowed | Over the held note: *"Who among them / can I afford to lose?"* — "not to us, not to himself, but to the federal investigation he can feel circling the building." | bass note held; baritone recitative, low, unhurried | Lip-sync route: Seedance 2.0 with `audio_references` (scratch VO) or Kling; else render mute + score under. |
| 9 | 72–74 | **Blackout on him** | cut to black | — | note cuts / decays | — |
| 10 | 74–90 | **The house is claimed** | wide of the auditorium from the stage; then reverse — the vomitoria | Houselights up on the **audience**; the chorus streams in from the vomitoria around the house, already singing "Competing Anthems of Victimhood." By the time the chorus reaches the stage, the audience is inside New Harnomy. | chorus, surround, many anthems at once | Filmed: two shots — audience surrounded (8 s) + chorus arriving on stage (8 s). |

**Render plan (first pass, cheapest-first):**
1. Plates: office at dawn (Soul Location / ComfyUI); proscenium (Soul Location); auditorium (Soul Location or stock).
2. Pengold hero still seated reading (Soul Cinematic + Soul-ID `pengold`, or ComfyUI img2img from anchor).
3. i2v per shot from the still (Kling 3.0 std for the holds — cheap; Seedance 2.0 only for shot 8 if lip-sync is wanted).
4. Assemble at fixed timings; **do not tighten the 22 seconds.**

**QA gate specifics:** mauve reads brownish (credenza stack); no legible headline; no lens flare; no smile;
dawn stays off the desk; register held for 22 s of nothing.
