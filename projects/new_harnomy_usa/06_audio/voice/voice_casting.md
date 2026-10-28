# Voice casting — NEW HARNOMY, U.S.A.

> Stage 7 template: NAME: provider, voice_id, stability, similarity, style, accent/age, baseline delivery.
> Lines: SPEAKER | line | delivery — spoken words only. **Voice IDs are NOT locked yet** — this sheet
> records the fach + register from v11 so the Voice Director can audition against it. Sung lines are score
> work (see `../music/score_brief.md`); this sheet governs recitative/spoken scratch tracks and any
> narrated animatic.

| Character | Fach (v11) | Register / delivery baseline | Accent/age note (see CANON_RECONCILIATION) | Provider / voice_id | stability / similarity / style |
|---|---|---|---|---|---|
| **summer** | Soprano | soaring idealism; composed; Framework-fluent grant-application cadence; never winks | early 40s; American New England (v11) — or European patrician if reading A is applied to voice as well | ElevenLabs — **TBD** | TBD |
| **pengold** | Baritone | measured authority; municipal cadence; "they" never "we"; the recitative "Who among them / can I afford to lose?" is addressed to the middle distance, low, unhurried | late 40s; American Northeast (kernel) | ElevenLabs — **TBD** | TBD |
| **dick** | Tenor | revolutionary fervor; charming, earnest, present; the finale line is **unamplified, clear, human**: "Pengold — you know me. You know the work. Tell them." | early 30s; American (v11) / Berlin-Antwerp (kernel) — decide with reading A/B/C | ElevenLabs — **TBD** | TBD |
| **valencia** | Mezzo-soprano | direct, economically precise; quiet; not accusatory; the last line is "a question, offered to the house" | late 40s; Mediterranean-rim or European-East (kernel) | ElevenLabs — **TBD** (prefer a less "produced" voice) | TBD |
| philip | speaking (if staged) | measured scholarship; Thucydidean; cold gentle questions | ~50; European (kernel) | deferred | — |
| chorus | ensemble | "Competing Anthems of Victimhood" — many anthems at once; finale: frozen mid-gesture | — | score | — |
| house manager (pre-show) | speaking | "Please silence your phones in solidarity with our most vulnerable." | — | TBD | — |
| City AG / TWEEEDS operative | speaking/recitative | flat, procedural: "Suede's organization is a disaster. Misappropriation, missing funds, grant violations. We document it, hand it over, investigation stops there." / "When do we move?" / "Paperwork's ready. Five million, contingent on…" | — | TBD | — |

## Line specs for the two bookends (spoken words only)

**NH-S101 (opening)**
- pengold | Who among them / can I afford to lose? | recitative over a single held bass note; to the middle distance; low; unhurried; no address to the house

**NH-S348 (finale)**
- dick | Pengold — you know me. You know the work. Tell them. | unamplified, clear, human; over a single clarinet; not drowned out — ignored
- pengold | LYSTERIA's allocation is confirmed. The federal application can proceed. Your work will continue. | after the hand on the shoulder; first words are about her funding, not about Dick; quiet; settled
- valencia | What won't you do? | one line; not accusatory; quiet; a question offered to the house

## Higgsfield note
`text2speech_v2` exposes ElevenLabs/MiniMax/Seed-Speech/Vibe/Cozy voices behind one CLI (`--variant`,
`--voice_id`, `--voice_type preset|element`); `seed_audio` can do voice-style audio + SFX. Use only for
scratch/animatic; the studio's locked voice remains ElevenLabs via `render_voiceover` until decided otherwise.
