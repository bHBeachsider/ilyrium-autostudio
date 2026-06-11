# Style Analysis — The Bio-Dome Brigade (SEED v0, 2026-06-11)

Panels sampled: 01 (title card), 02 (control-center confrontation, dialogue-heavy), 09 (bowl-throw slapstick), 17 (boardroom punchline/END).

## Medium Determination
**Hand-drawn digital, strict grayscale.** Evidence:
- Variable-weight organic ink outlines with visible hand wobble (mustache strokes, flyaway hairs, mountain ridges) — not vector-clean, not AI-render smooth.
- Flat fills with no gradient banding; sparse loose hatching on mountains/fabric only. No photographic texture, no CGI lighting.
- Lettering is hand-styled bold all-caps with slight baseline drift — drawn or hand-fonted, not typeset body text.
- Zero color in any sampled panel. The strip is black/white/gray by design, not by scan loss (gray washes are deliberate and tonal-ranged).

## Line / Color / Shading / Lettering
- **Line:** Bold, confident, medium-to-heavy contour; thicker on silhouettes and figure outlines, thinner on background lattice and mountain detail. Motion arcs, speed lines, flying sweat/tear droplets used liberally for slapstick beats.
- **Color:** None. Three-value system: paper white, mid gray (~#ABABAB), near black (~#0A0A0A), plus a light wash (~#D9D9D9) for glass/ground.
- **Shading:** Flat tonal fills; minimal hatching; occasional soft drop shadow under figures. No rendered form shadow on faces.
- **Lettering:** Bold all-caps, mixed free-floating dialogue blocks (no balloon outlines in panel 02 — text sits in white space above each speaker) and solid black banner caption boxes with white text ("AT THE BIODOME CONTROL CENTER ..."). Underlining used for emphasis (INTENTIONALLY). Footnote asides at panel bottom in smaller caps.

## Palette Table
| Name | Hex est. | Where used |
|---|---|---|
| paper_white | #FFFFFF | Corridors, sky, boardroom, dome interior — dominant negative space |
| silhouette_black | #0A0A0A | Silhouette man's body, caption banners, ties, heavy outlines |
| suit_gray | #ABABAB | Dr. Spanker's suit, counters, table edges, mountain mid-tones |
| wash_gray_light | #D9D9D9 | Dome glass panels, ground planes, soft drop shadows |
| lattice_line | #C7C7C7 | Faint triangular geodesic lattice on interior dome walls (location signature) |

## Composition & Framing Habits
- Single widescreen panels (~3:2 landscape), one beat per panel.
- Eye-level two-shots dominate; speakers placed left/right with dialogue stacked above each.
- Huge empty white negative space — backgrounds reduced to one or two cues (doorway, lattice, counter).
- Recurring over-the-shoulder boardroom setup held static across three consecutive panels for comic timing (silent-beat repetition).
- The silhouette man always reads in profile; his black mass anchors frame right or foreground.
- "END" printed directly on the silhouette's back — diegetic text gags are in-style.

## Continuity Risks
1. The dome exterior is latticed-hemispherical, NOT geodesic (the author footnotes this joke) — keep the established non-geodesic dome; don't "correct" it.
2. Silhouette man must never gain facial features, eyes, or interior detail — solid black with hooked-nose profile only.
3. Dr. Spanker's walrus mustache scale (covers mouth entirely) and balding pattern must stay locked.
4. Interior dome lattice is faint light-gray triangles — easy for a generator to over-render into hard geometry.
5. Grayscale discipline: any model drift into color breaks the entire look.
6. Lettering style mixes free-floating text and black banners — a uniform balloon treatment would be off-model.

## Keep vs Fix (for regeneration)
**Keep:**
- Strict 3-value grayscale; flat fills; sparse hatching.
- Big-nose caricature proportions, mugging expressions, lolling tongues, flying sweat.
- White-dominant compositions; static repeated framings for timing.
- Black banner captions with white text; all-caps lettering; underline emphasis.
- Solid-black silhouette antagonist convention.

**Fix:**
- Slight line-weight inconsistency between panels (title card heavier than interiors) — normalize per-scene.
- Background lattice opacity varies panel to panel — lock to a single light-gray value.
- Free-floating dialogue can collide with art at render; generate art textless, letter in post.
- Counter/table grays drift between #999 and #BBB across panels — pick one suit_gray anchor.
