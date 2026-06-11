# Style Analysis — New York, New York (SEED v0, 2026-06-11)

Panels examined: 01 (title card), 04 (ATM blast — scream panel), 07 (NYPD booth — dialogue/caption-heavy), 08 (closing patriotic card). 4 of 8 panels.

## Medium Determination
**Hand-drawn digital illustration, grayscale, dual-register rendering.** Evidence:
- Landmarks (Statue of Liberty, Empire State Building) are wobbly contour-only line drawings with human stroke hesitation — no AI tool leaves architecture this unrendered while heavily modeling adjacent faces.
- Faces show deliberate soft-brush tonal modeling (digital airbrush/soft round) layered under ink — shouting_man's scribbled hair mass is built from looping pen strokes, not diffusion texture.
- Caricature is grotesque and consistent: gap teeth, pitted cheeks, bulging eyes recur across panels with the same drawing logic.
- Title card serif type ("NEW YORK, NEW YORK") is set type composited over the drawing — typography in post, not drawn.

## Line / Color / Shading / Lettering
- **Line:** Two weights of intent: light wandering contour for landmarks/environment; denser, more worked ink for figures (hair scribble, mustaches, knuckles).
- **Color:** None. Grayscale only.
- **Shading:** Heavier than the other Broderick strips — soft gray tonal modeling on every face and hand, flat gray washes on station ceilings/counters, plus a ghosted ~10%-gray patriotic layer (flag, eagle, fife-and-drum trio) in panel 08. Solid black for silhouettes and garments.
- **Lettering:** Three systems: (1) bordered rectangular caption boxes for narration (panel 07); (2) free-floating all-caps hand lettering for dialogue; (3) giant black italic display caps for the bellow ("MMMAAOUUUB!!"); plus typeset Didone serif + script on title card only.

## Palette Table
| Name | Hex est. | Where used |
|---|---|---|
| ink_black | #1A1A1A | contour line, scream type, cap, jersey stripes |
| silhouette_black | #0D0D0D | bystander silhouette, shirt masses, exclamation mark |
| face_model_gray | #AFAFAF | tonal modeling on faces/hands, pizza slice |
| environment_gray | #D6D6D6 | ceiling panels, NYPD counter, ghost flag/eagle layer |
| paper_white | #FFFFFF | unfilled landmark line art, caption boxes, negative space |

## Composition & Framing
- Bookend cards: centered mascot flanked symmetrically by landmarks; closing card adds the ghosted patriotic layer behind.
- Story panels: tight claustrophobic two-shots at eye level; perspective lines of fluorescent ceiling panels converge to sell the underground concourse.
- Scream panels put the display lettering across the top third, art compressed below; shock lines radiate off the victim.
- Solid-black foreground silhouette used for over-the-shoulder framing (panel 07) — cheap, effective depth trick.

## Continuity Risks
1. The dual register (unfilled landmarks vs heavily modeled faces) is the signature — a generator will want to render everything evenly. Must be prompted explicitly per layer.
2. shouting_man's hair is a scribble mass, not styled hair; renders drift toward "anime spiky" fast.
3. Grotesque faces must stay ugly; beautification is the most likely model failure (see failure_fixes.drifts_pretty).
4. Caption boxes are bordered here, unlike other Broderick strips — keep per-strip lettering rules separate.
5. NY iconography (NY cap logo, NYPD insignia) is trademark-adjacent — generic-ize marks on regeneration.

## Keep vs Fix (for regeneration)
**Keep:** grayscale dual-register rendering; grotesque tonal-modeled caricature; contour-only landmarks; black silhouette device; ceiling-perspective concourse staging; three-tier lettering system; bookend mascot with pizza + thumbs-up.
**Fix:** trademark-adjacent logos (NY cap monogram, NYPD lettering) — replace with generic equivalents or hand-altered marks; tonal level on faces varies between panels (04 heavier than 01) — pick one modeling depth; serif title must be set in post, never generated; ghost layer in 08 should stay below ~12% gray or it crowds the figures.
