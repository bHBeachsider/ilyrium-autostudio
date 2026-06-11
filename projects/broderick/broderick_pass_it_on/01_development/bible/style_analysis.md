# Style Analysis — Pass It On

Seed analysis from source panels 01, 04, 07 (of 7). Date: 2026-06-11.

## Medium determination

**Hand-drawn digital, grayscale, loose-sketch register.** Evidence:

- Line is wobbly, gestural, and unpolished throughout (panel 01: window bars are quick scribbles, hands are approximate shapes). No AI-render tells — anatomy is consistently "wrong" in the same human way across panels.
- Flat gray washes laid under the sketch line with visible quick-fill edges; no tonal modeling, no gradients on faces.
- Lettering split is the giveaway of a human workflow: English lines are hand-lettered caps; Hindi (panel 04) is typeset Devanagari in a system font — the artist pasted real typeset text for foreign languages.
- Panel 07 carries leftover web-capture chrome (navigation arrows at frame edges) — source images are site screenshots, not clean exports.

## Line / color / shading / lettering

- **Line:** loose dark-gray sketch contour (~#2A2A2A), variable and scribbly; props drawn even fainter in pale gray. No closed/cleaned inking.
- **Color:** none — strictly grayscale.
- **Shading:** flat fills only. Two or three garment grays; skin rendered as gray value (notably darker for prisoner_african). No cast shadows, no light source.
- **Lettering:** hand caps for English dialogue floating at panel top (no balloons); typeset fonts for French/Russian/Hindi/Swahili/Chinese lines; floating "?" over each listener; bold hand-lettered "END" lower right of final panel.

## Palette table

| Name | Hex est. | Where used |
|---|---|---|
| paper_white | #FFFFFF | background, barracks walls |
| sketch_line_gray | #2A2A2A | contours, English lettering, question marks |
| garment_light_gray | #D6D6D6 | shirts, caps, light fills |
| trouser_mid_gray | #9E9E9E | trousers, tunics, guard uniform |
| ghost_prop_gray | #C9C9C9 | ACHTUNG posters, barred window, watchtower, locker |
| skin_value_gray | #7A7A7A | prisoner_african skin value; lighter grays for others |

## Composition and framing habits

- Rigid format gag: seven near-identical seated whisper two-shots, whisperer at left with cupped hand, listener at right with floating question mark, eye level, medium shot.
- Dialogue always across the top of the panel, image below.
- Background props rotate minimally per panel (window/tower → poster → locker) to imply different corners of the same camp.
- Final panel breaks pattern: standing two-shot, guard with rifle, "END" card — the only composition change in the strip, which is the punchline beat.

## Continuity risks

1. **Eight distinct characters, one panel each** — highest casting-drift risk of the series; each whisperer must match their listener appearance from the previous panel (hat swaps already occur in source: beret→white cap, star cap→flat cap — decide canon per character and lock it).
2. **Skin-value consistency** — gray skin values must stay stable per character or identities blur.
3. **Repeated composition** — generators will "improve" variety; the sameness IS the joke. Lock camera and pose.
4. **Foreign-language text** — must be typeset in post, never generated.
5. **Period setting** — POW camp iconography must stay generic-cartoon; never render real insignia (swastika excluded in negatives).
6. **Web chrome artifacts** — source panel 07 contains site navigation arrows; never reproduce.

## Keep vs Fix (for regeneration)

**Keep:**
- Loose wobbly sketch line and flat gray washes
- Identical whisper two-shot composition with rotating background props
- Floating question mark over every listener
- Hand caps for English / typeset for other languages
- Pattern-break standing finale with END card

**Fix:**
- Source hat inconsistencies (beret vs white cap, star cap vs flat cap) — pick one per character in the model sheet
- Strip web navigation arrows and capture chrome
- Panel 7's stray horizon/border line — standardize borderless white panels
