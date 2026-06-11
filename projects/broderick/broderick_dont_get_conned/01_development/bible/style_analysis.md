# Style Analysis — Don't Get Conned / Fonzi Scheme (SEED v0, 2026-06-11)

Panels examined: the single panel in `panels/` (the complete strip), landscape ~3:2.

## Medium determination
**Hand-drawn digital, grayscale, single-panel gag cartoon.** Evidence: freehand contour with visible wobble (the mark's belly and trouser line), hatch strokes on the leather jacket and knit ribbing, flat hard-edged gray fills, hand-styled underlined title. The two figures are drawn at deliberately different skill registers — the con man with confident modeling and a polished toothy grin, the mark lumpy and crude — an intentional caricature asymmetry, not inconsistency. No photographic or AI-render artifacts; no color anywhere.

## Line / color / shading / lettering
- **Line:** single-weight freehand; refined and assured on the con man, deliberately schlubbier on the mark. Knit collar/cuffs indicated with short rib ticks.
- **Color:** none. White void, black ink, three flat grays.
- **Shading:** flat fills only — charcoal jacket, pale denim, dark trousers — plus light hatch on the jacket for leather sheen. No gradients or washes.
- **Lettering:** typeset all-caps comic font, balloon-less, blocks floating beside each speaker; underline used for emphasis ("RISK-FREE?"). Title "FONZI SCHEME" top-left: large bold underlined capitals acting as an in-panel title card.

## Palette table
| Name | Hex est. | Where used |
|---|---|---|
| paper_white | #FFFFFF | background void, mark's t-shirt |
| ink_black | #1B1B1B | linework, lettering, title, pompadour, hair fringe |
| jacket_charcoal | #3A3A3A | leather jacket body |
| trouser_gray | #5A5A5A | mark's trousers |
| denim_gray | #C4C4C4 | faded jeans, light shirt |

## Composition and framing habits
- Pure white void stage — zero environment, zero props; the figures and text carry everything.
- Status geometry: the con man stands larger and closer (right half, head near the top edge, cropped at the knees); the mark is smaller, hunched, and pushed left and lower. Size = power.
- Title top-left, dialogue blocks in the white gap between the figures; reading path is title → mark's question → con man's one-word answer at his eye level.
- Double thumbs-up is the punchline pose — both thumbs must read clearly.

## Continuity risks
1. Legal/IP: the premise puns on a famous 1950s-TV greaser archetype — generated art must stay a generic pompadour/leather-jacket archetype, never a recognizable actor likeness (legal_rule applies hard here).
2. The polish gap between the two figures is the visual joke; a generator will try to equalize them.
3. Thumbs are an "extra fingers" hazard at the exact focal point of the panel.
4. White tee against white void depends on the contour line holding; fill bleed kills the mark's silhouette.
5. Underline emphasis and underlined title must survive the lettering pass.

## Keep vs fix for regeneration
**Keep:** white-void single panel; grayscale flats; size/polish asymmetry; double thumbs-up pose; underlined in-panel title; balloon-less comic-font dialogue with underline emphasis; knit collar/cuff detail on the jacket.
**Fix:** mark's facial features are mushy at small sizes (sharpen the heavy-lidded eyes); jacket hatch direction inconsistent between sleeve and body; dialogue block crowds the mark's head; consider one cast shadow per figure to seat them on the void (optional, test against deadpan flatness).
