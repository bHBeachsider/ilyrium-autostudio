# Sequences / act map

Multi-scene arcs → Sequence rows in the asset graph. Numbering follows the studio decision (2026-08-15):
**ilyrium-shots song IDs are act-based** — `NH-S1nn` (Act I), `NH-S2nn` (Act II), `NH-S3nn` (Act III), where
`nn` is the number's global index 01–48. Opening = **NH-S101**; finale = **NH-S348**. (NH-S03 and NH-S05 belong
to other Ilyrium pieces and are untouched.)

| # | Sequence | Days | Scenes / numbers (v11-named only; the rest are slots) | Function |
|---|----------|------|------|----------|
| I | **Act One — "The Gathering"** | Mon–Wed | **NH-S101** *The First 90 Seconds*: Pengold reading; recitative "Who among them / can I afford to lose?"; chorus "Competing Anthems of Victimhood" streams in. Then: festival opens (land acknowledgments, workshops, galas); triangle forms; Dick awaits GRIFT; Summer negotiates + continues the affair; Dick's shakedown escalates (charming → insistent → threatening). "They, the People" (Pengold's aria) + Valencia's interlude — Act placement TBD. | Establish the machine, the triangle, the Framework, the mauve, and the modest stakes ($5M/$50M). |
| II | **Act Two — "The Crisis"** | Thu–Fri | The Betrayal (Summer overhears; sixty seconds; signs); "Everything we've built — it needs protection"; rationalization cascade; funding scandal breaks; the asymmetry scene (election-night memory); Dick oblivious. | Summer's silence becomes a choice. |
| III | **Act Three — "The Reckoning"** | Sat (Ersatzgiving) | The Feast keynote (celebration → denunciation); portrait rises; City AG + officers; the arrest; **NH-S348** *The Six Beats of the Finale* (Denunciation / Listening / Exit / Coronation / Valencia / Chord & Cut); news of Dick's death (inside Valencia's aria); eight seconds; house lights; the curtain-call problem. | One rises as the other falls; the question passes to the house. |

## First render targets (bookends)

| Song ID | Sequence | Cards | Storyboard | Status |
|---|---|---|---|---|
| **NH-S101** | The First 90 Seconds (opening) | `02_script/numbers/NH-S101_opening.scenes.json` | `04_preproduction/storyboards/NH-S101_OPENING_FIRST_90_SECONDS.md` | scene cards + shot specs generated 2026-08-15 |
| **NH-S348** | The Six Beats of the Finale | `02_script/numbers/NH-S348_finale.scenes.json` | `04_preproduction/storyboards/NH-S348_FINALE_SIX_BEATS.md` | scene cards + shot specs generated 2026-08-15 |

Everything between them is Screenwriter-stage work (`stage_ideate(project="new_harnomy_usa", stage="01_script", ...)`).
