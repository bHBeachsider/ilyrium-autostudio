# Style Analysis — Cool Daddy Smooth

Seed analysis date: 2026-06-11. **Evidence caveat:** only panel 07 of 7 ("Flipping Burghers," the standalone gag panel, 2048x1535) exists in `01_development/bible/panels/`. Panels 1-6 (the main Cool Daddy Smooth narrative) were unavailable; their look is extrapolated from this panel plus scenes.json descriptions. Re-verify against the full strip before locking.

## Medium determination

**Full-color hand-drawn digital, polished register.** Evidence (panel 07):

- Clean, confident, closed ink contours at consistent medium weight — far tidier than the scribble register of other Broderick strips. Reads as deliberate digital inking (iPad/desktop), not AI render: hands, staff grip, and robe folds show human cartoon logic with consistent stylization, and the hand-drawn wobble survives in the panel border and checklist box.
- Flat color fills with restrained tonal folds on the red robe; soft gray cast shadows pooling beneath both figures — a lighting model, but a minimal cartoon one.
- Hand-lettered caps for the title and the reader-poll checklist.

## Line / color / shading / lettering

- **Line:** medium-weight closed black contour, even and confident; hand-drawn panel border with slightly rounded corners frames the image.
- **Color:** full color, muted-support / single-accent strategy — one big saturated red shape (the robe), small red echo (sneakers), everything else khaki/gray/flesh neutrals on white.
- **Shading:** flat fills; soft tonal folds inside the robe; soft gray ground shadows under figures. No light direction beyond the shadow pool.
- **Lettering:** hand caps in black ink; title top-left; checklist in a wobbly rounded-rect box lower right (fourth-wall poll gag). No balloons in this panel; scenes.json implies floating caps elsewhere.

## Palette table

| Name | Hex est. | Where used |
|---|---|---|
| paper_white | #FFFFFF | void background inside panel border |
| ink_black | #1A1A1A | contours, border, lettering, checklist |
| robe_red | #B5453A | burgher's robe — dominant accent shape |
| sneaker_red | #D6342C | sneakers; accent echo |
| khaki_drab | #ACA08E | cargo shorts, muted garments |
| shadow_gray | #BFBFBF | soft cast shadows on ground |
| flesh_warm | #E8B9A0 | skin tones, flat |

## Composition and framing habits

- Bordered landscape panel; white void stage with no environment except shadow pools.
- Strong diagonal between thrower (lower left) and airborne figure (upper right); motion conveyed by pose and placement, not speed lines.
- Title top-left, gag furniture (checklist) lower-right — corners do the talking.
- scenes.json indicates the main strip uses two-shots at eye level, sketched minimal props (desk, banner, alley trash basket), caption boxes upper-left, and an END card.

## Continuity risks

1. **Single-panel evidence** — the main strip's six narrative panels are unverified; the polish level of panel 7 may not match panels 1-6. Re-extract when those panels are recovered. HIGH priority.
2. **Costume volume** — Cool Daddy Smooth has two outfits (leather-jacket street look, FLAPPY clown suit) plus permanent hat/shades; the never-removed cone hat and white-framed sunglasses are identity anchors in both.
3. **Accent-color discipline** — one saturated accent per panel; generators will over-color.
4. **FLAPPY collar lettering** — tiny in-art text will garble; composite in post.
5. **Six-character cast + 2 gag-panel extras** — model sheets needed for all before batch generation.

## Keep vs Fix (for regeneration)

**Keep:**
- Clean closed ink contour + flat color + soft ground shadow
- White void staging inside a hand-drawn panel border
- Muted-support/single-red-accent palette strategy
- Hand-lettered caps and corner-anchored gag furniture
- Diagonal action staging without speed lines

**Fix:**
- Confirm main-strip (panels 1-6) polish level matches panel 7 before locking the kernel
- In-art micro-lettering (FLAPPY collar, checklist) must be a post pass
- Keep skin tones flat — resist tonal modeling creep

---
CORRECTION (2026-06-11, verifier pass): panels 1-6 ARE readable and are grayscale scratchy gag-cartoon (verified against panel 3, 'AT THE PAR-TAY'). The original extrapolation saw only panel 7 (Flipping Burghers, full color) and generalized wrongly. Kernel corrected: main strip grayscale; panel 7 is the color outlier. Medium confidence now NORMAL, not low.
