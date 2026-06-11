# Style Analysis — Holy F* It's Cody (SEED v0, 2026-06-11)

Panels examined: 01 (setup two-shot), 04 (three-shot dialogue), 07 (tirade), 12 (mail-order coda). 12 panels total in `panels/`.

## Medium determination
**Hand-drawn digital, monochrome.** Evidence: wobbly single-pass contours with visible direction changes and overshoots (windshield frame, headlight circles); scribbled crosshatch fill inside headlights and grille that no AI renderer produces this crudely; identical car drawing reused panel-to-panel (copy-paste base layer with redrawn heads); flat digital gray fills with hard edges; stray pen marks in the sky of panel 01. No photoreal artifacts, no gradient rendering, no AI texture noise. Lettering is a typeset bold all-caps comic font (uniform letterforms), not hand-lettered — except the coda's coupon fields, which are hand-scrawled ("NAIM", "ADRESS").

## Line / color / shading / lettering
- **Line:** loose, scratchy, single weight, confident but uncorrected; deliberately crude. Hair drawn as solid black scribble masses.
- **Color:** none. Strict grayscale — black ink, two or three flat grays, white paper.
- **Shading:** flat fills only. The cabin smoke is a soft light-gray haze that visibly thickens across the strip — the haze IS the plot's visual escalation device.
- **Lettering:** bold all-caps comic font floating balloon-less in white negative space above the car; speaker attribution by horizontal position only (left text = left character). No balloon outlines or tails anywhere.

## Palette table
| Name | Hex est. | Where used |
|---|---|---|
| paper_white | #FFFFFF | background sky, dialogue field, coda page |
| ink_black | #1A1A1A | linework, lettering, hair, sunglasses lenses, suit |
| car_body_gray | #B5B5B5 | sedan hood, frame, headrests |
| cabin_smoke_gray | #D8D8D8 | interior haze, escalating density |
| glass_gray | #C8C8C8 | windshield/rear-window tint |

## Composition and framing habits
- One locked camera: head-on through the windshield, eye level, symmetrical. 11 of 12 panels are this exact shot — the static frame is the comedic engine.
- Characters rendered bust-level behind the dash line; hood and grille occupy the lower 40% as dead space.
- "uber" placard (white box, lowercase scrawl) lower-left of windshield in every car panel.
- Panel 12 breaks format entirely: flat white advertisement page with starburst mascot head, dashed coupon, and two crude blob doodles — intentionally even cruder than the strip.

## Continuity risks
1. Cody's drool line and slack jaw must persist in every panel after scene 3 — easy for a generator to "fix."
2. Smoke density must be monotonically increasing; resets break the gag.
3. The reused car drawing must be pixel-identical across panels; any redraw of the hood/grille will read as a continuity error.
4. Driver's heavy-lidded eyes drift toward "alert" in regeneration; lock the half-closed lids.
5. Color creep — any colorization destroys the look.

## Keep vs fix for regeneration
**Keep:** locked head-on windshield frame; strict grayscale; scratchy crude line; balloon-less floating dialogue; escalating smoke haze; uber placard; crosshatched headlights; format-breaking crude coda page.
**Fix:** stray pen marks in sky (panel 01); inconsistent gray values between panels; text occasionally crowding the windshield top edge; coupon-page blob doodles can be regenerated freely (intentionally throwaway).
