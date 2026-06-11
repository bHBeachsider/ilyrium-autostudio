# Style Analysis — Follow Instructions (SEED v0, 2026-06-11)

Panels examined: 01 (whistling entrance), 03 (assembly), 05 (DUNCE pictogram, dialogue-heaviest), 06 (decapitation + END badge). 6 panels total in `panels/`.

## Medium determination

**Hand-drawn digital (iPad/Procreate) minimal line art — an IKEA-instruction-manual parody. NOT clip-art collage, NOT AI render.**

Evidence:
- Source filenames are `untitled_artwork-N` — Procreate's default export name; original drawn art.
- Line is a single thin stroke with visible hand wobble, inconsistent closures, and slight pressure variation — characteristic of stylus drawing, not vector tooling or model output.
- Figures are deliberate IKEA-manual humanoids: bald, featureless, dot eye, simple mouth — the parody is the premise.
- The END badge in panel 06 directly parodies the IKEA logo (blue rectangle, yellow oval, bold blue caps).

## Line / color / shading / lettering

- **Line:** thin, near-uniform weight, gently wobbly; contour-only, no interior detail beyond a dot eye, mouth line, and the occasional belly crease.
- **Color:** none in the body of the strip — black on white only. Blue/yellow appears solely in the END badge.
- **Shading:** none. Two tiny solid-black fills exist (the musical note, the inside of the dunce cap's brim) and read as pictogram emphasis, not shading.
- **Lettering:** almost wordless. "DUNCE" is small wobbly hand-lettered caps inside the pictogram; "END" is bold logo-style type. One classic oval speech balloon with tail (panel 5 / question-mark panel) — pictograms in balloons rather than words.

## Palette table

| Name | Hex (est.) | Where used |
|---|---|---|
| void_white | #FFFFFF | the entire field, every panel |
| manual_ink | #1F1F1F | all linework |
| solid_fill_accent | #111111 | musical note, dunce-cap brim interior |
| flatpack_blue | #0051BA | END badge rectangle + lettering (panel 6 only) |
| flatpack_yellow | #FFDB00 | END badge oval (panel 6 only) |

## Composition & framing habits

- Landscape ~850x550 panels, borderless on white.
- Figures occupy the lower half / lower third; the upper half is empty void (balloons and flying objects enter that space when needed).
- Strict two-figure staging: passerby left, manual_reader right, box between them at ground level — held across nearly every panel like a fixed theater set.
- Action conveyed by pose change and simple motion arcs (curved lines tracing the flying head and booklet in panel 6).
- Eye-level, flat, wide. No camera moves implied; it is a diagram that misbehaves.

## Continuity risks

1. The two figures are near-identical; the only distinguishers are height, belly shape, and the booklet prop. The manual_reader must always hold the booklet (until he throws it) or the characters become unreadable.
2. Line weight must stay thin and uniform; any bold-brush regeneration breaks the instruction-manual register.
3. The blue/yellow END badge is the only color in the strip — if color leaks into earlier panels the punchline-by-contrast dies.
4. Box state progression (open → lid being fitted → closed) is the silent plot clock; panels must respect it.
5. Generators will want to add faces, hair, clothes, shadows, and a ground line. All must be suppressed explicitly.

## Keep vs Fix for regeneration

**Keep:**
- Single thin wobbly contour line, featureless IKEA-manual humanoids
- Pure white void, no ground line, no shadows
- Pictogram-only communication (note, ?, dunce cap) in classic oval balloons
- Fixed left/right staging with box at center, huge top negative space
- END badge as IKEA-logo parody and sole color event

**Fix:**
- Normalize panel margins (figures drift in vertical placement between source panels)
- Standardize the dot-eye and mouth marks (panel-to-panel jitter in placement)
- Ensure the booklet prop is drawn identically across panels (fold count varies in source)
- Keep "DUNCE" hand-lettering legible at output resolution or replace with a cleaner lettering pass
