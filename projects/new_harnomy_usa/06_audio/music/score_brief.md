# Score brief — NEW HARNOMY, U.S.A.

> Stage 8 template: MOOD/GENRE/INSTRUMENTATION, TEMPO, STRUCTURE, instrumental?, emotional arc, must-not-overpower-VO;
> per-scene SFX/ambience. Source: v11 §VII, §X, §XI. This is an opera: **the score IS the drama** — the
> "VO ducking" rule of the ad pipeline does not apply; sung lines lead, orchestra under them.

## Musical language (binding)
Contemporary operatic; sophisticated techniques presenting earnest content whose contradictions surface over
time. "Earnest and slightly off": beautiful surfaces that don't quite resolve; harmonic progressions that
promise satisfaction and deliver something slightly different. Winter, barrenness, scarcity as tonal weather.
No comedic scoring, ever (Wildean law).

## Idioms
| Voice | Idiom |
|---|---|
| Summer (soprano) | soaring idealism |
| Pengold (baritone) | measured authority; "They, the People" = genuinely moving, soaring melody, orchestral swell — the lyrics alone reveal the paternalism |
| Dick (tenor) | revolutionary fervor |
| Valencia (mezzo) | direct, economically precise; blues / work song / actual-labor references, contemporary; her material predates and outlasts the others' fashions |
| Chorus | "Competing Anthems of Victimhood" (opening) — many anthems at once; the TWEEEDS theme (finale) — triumphant major, brass forward |

## Fixed cues (do not alter)
1. **Pre-show** — a cellist "warming up" in the pit plays **the fragment** (Valencia's modal idiom) over and
   over among scales and tuning. Seeded three hours before it returns.
2. **NH-S101 opening** — after 22 s of silence: **a single bass note, low, held**; Pengold's recitative over it
   ("Who among them / can I afford to lose?"); blackout; the chorus streams in already singing.
3. **NH-S348 finale beats** — (1) TWEEEDS theme, most triumphant orchestration, brass forward, full chorus →
   (2) orchestra *thins* (strings out, brass out) to **a single clarinet holding the TWEEEDS melody** under Dick's
   unamplified "Pengold — you know me. You know the work. Tell them." → (3) clarinet sustains; **stops mid-phrase**
   as Dick exits → (4) **silence** for the Coronation → (5) Valencia, one line, quiet: "What won't you do?" →
   (6) **the chord**: every instrument, one by one, joining a single sustained chord — not a triad; TWEEEDS major
   and Valencia's modal minor at once; accumulation not crescendo; "grows until it is almost unbearable";
   **hard cut** (severed, not faded); **eight seconds of silence** before any house light.
4. **Valencia's final aria** — begins as reflection on the evening (grift, sacrifice, the machine consuming its
   own); midway she receives word Dick is dead; the language shifts (blues/work-song references emerge most
   fully); she sings of what remains when ideologies fade — the work, the bills, the bodies, the questions.

## Generation guidance (Ilyrium tools)
- Sung numbers: **not** Suno-bed material; treat as composed score + recorded/synthesized voice. Suno/APIFrame
  (`generate_music_bed`) can prototype orchestral beds and the chord for animatics only.
- Higgsfield audio (adapter): `seed_audio` for ambience/foley/room tone (a cough in a silent house; a paperback
  hitting the floor — "a single unamplified thump"; a page turn); `text2speech_v2` (variants incl. elevenlabs)
  for recitative scratch tracks. Not for the sung line.
- ElevenLabs (wired) for spoken/recitative scratch; ELEVENLABS voice ids locked at Stage 7.
- SFX list (per bookend): silent house + one cough (opening); page turn; paper set on desk; low bass note;
  chorus from the vomitoria (surround); brass tutti; clarinet solo; shackles/steps; a book hitting the floor;
  the accumulating chord; absolute silence.

## Licensing
Original score assumed (record composer agreement in `../../00_admin/contracts/`). No licensed tracks anticipated.
