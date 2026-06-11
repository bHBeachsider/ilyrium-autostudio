# Style Analysis — Into The Rubber Chamber Area That Leads To The Toilet

Seed analysis from source panels 01, 03, 04, 07 (of 7). Date: 2026-06-11.

## Medium determination

**Hand-drawn digital, grayscale, mixed rendering fidelity.** Evidence:

- Yabo's head is rendered with near-photographic caricature realism — smooth, continuous gray tonal modeling on the scalp stubble, jowls, ears, and nose (panels 01, 03, 07). This reads as drawn over photo reference or heavily worked digital painting, not AI render (consistent anatomy across panels, no AI artifacts, deliberate caricature exaggeration of ears/jowls).
- Bodies and hands drop to a much looser, sketchier ink line (panel 04: the throw — knuckles are gestural scribbles, the victim's hand is a five-stroke splay). The fidelity gap between head and body is a signature, not a flaw.
- Lettering is genuinely hand-made (irregular baselines, marker-weight strokes), ruling out typeset comic fonts.

## Line / color / shading / lettering

- **Line:** confident but unfussy ink contour; weight varies from bold figure outlines to barely-there light-gray door lines (~#D9D9D9). Speed lines are three quick horizontal dashes.
- **Color:** none. Strictly grayscale — white paper, black ink, two or three gray values.
- **Shading:** soft continuous tonal modeling on heads and arms only; flat mid-gray fill on the t-shirt; hatched ribbing on the collar; everything else unshaded white.
- **Lettering:** bold black italic hand-lettered caps for title and shouted dialogue, floating free with NO balloon; oval balloons with long curved tails reserved for unseen voices behind the door; "KNOCK KNOCK KNOCK" stacked with stroke marks; microtype mock-legalese copyright band across the bottom of every panel (a recurring gag — keep it).

## Palette table

| Name | Hex est. | Where used |
|---|---|---|
| paper_white | #FFFFFF | background void, every panel |
| ink_black | #141414 | lettering, contours, track pants, knock strokes |
| shirt_mid_gray | #8A8A8A | t-shirt flat fill, TO BE CONTINUED placard |
| flesh_shade_gray | #C4C4C4 | tonal modeling on scalp, face, ears, arms |
| ghost_line_gray | #D9D9D9 | faint door contour, light furniture lines |
| microtype_strip | #EFEFEF | bottom legalese band background |

## Composition and framing habits

- Landscape single panels, no panel borders — the image edge is the frame.
- Figure anchored frame RIGHT, text filling frame LEFT (panels 01, 03, 04, 07). The door, when present, dominates frame left.
- Eye-level medium/medium-full shots; slight low angle on the title panel.
- Panel 7 deliberately mirrors panel 3 (same door composition) for the repeat-cycle gag.
- Motion via horizontal speed lines and bodies exiting frame; "TO BE CONTINUED" on a slanted gray placard cutting across the lower frame.

## Continuity risks

1. **Head fidelity drift** — generators will either photoreal-ify the whole figure or flatten the head. The head-realistic/body-sketchy split is the hardest thing to reproduce; lock with a model sheet.
2. **Color creep** — any color breaks the look; enforce grayscale in every prompt.
3. **Lettering** — hand-lettered floating caps will garble; generate art textless, letter in post.
4. **Microtype band** — easily lost; composite it in post from a fixed asset.
5. **Door consistency** — the faint-gray paneled door must match between panels 3 and 7 (mirror gag depends on it).

## Keep vs Fix (for regeneration)

**Keep:**
- White void staging, no backgrounds
- Head-realistic / body-sketchy fidelity split
- Free-floating shout lettering vs. ballooned door voices
- Frame-right figure / frame-left text layout
- Bottom microtype legalese band
- Strict grayscale

**Fix:**
- Inconsistent hand anatomy in action panels (panel 04 knuckles) — acceptable in source, but regenerated versions should be deliberately gestural, not broken
- Slight head-angle inconsistency between panels 01 and 03 — lock a model sheet
- Bake lettering as a post pass, never in-generation
