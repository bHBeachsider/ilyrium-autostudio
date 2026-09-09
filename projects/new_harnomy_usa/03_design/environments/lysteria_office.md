# LYSTERIA — Summer's office

Set: `LysteriaInterior` (backlot asset). The upper floor of `shop_e1`, the north row's east end, re-fronted in glass.
Room 9 × 14 m, ceiling 3.2 m, floor at z = 4.2. Brief, Brad, 2026-09-09; evaluated against the bible before building
(the evaluation is summarised under *Canon* below), then built.

## The room

All white — walls and floor — with the brand rose as the only accent. The aesthetic of a high-end London PR company:
white, pale oak, brushed steel, one colour, nothing loud. "Impeccable, expensive, never flashy" (wardrobe bible), as a
room.

**A glass wall divides it.** North of the glass, the door end, is the floor: reception against the east wall with
LYSTERIA on the wall behind it in the rose; two white benches with a low rose screen down the middle, two staff each,
linear pendants over them; the gallery wall along the west side; a low white shelf of the mauve paperbacks under it.
South of the glass is Summer's own office, backed by the glazed band onto the square: her desk facing the floor, two
visitor chairs, a white sofa with a low oak table for the chat, the plaque grid on her east wall, the second framed
campaign banner over the sofa.

**She sits with the square behind her.** A visitor takes the chair with the light in their face; she is a shape
against the band until she leans in. Through the band: City Hall's colonnade and the rally stage. She watches the
scaffold go up from her desk. That is the POV contract with the square, and it came free from the geometry.

**The glass wall is status and surveillance in one plane.** She sees the floor; the floor sees her. It rhymes with her
sixty-second wait outside Pengold's ajar door — here she runs the room where the glass makes her the one watched.

**Larger windows.** LYSTERIA re-fronted the shop's upper floor as a single glazed band when it moved in (7.6 m of a
10 m frontage, sill 0.7, head 3.0). The exterior changed with it: the one shop on the row with a modern glass first
floor is the one with money. `NorthRow` carries the band; the interior cut is the same opening.

## The satire, and the law that governs it

The causes are instruments of her aspiration. Campaign banners framed in white; photographs hung museum-spaced, her in
every one; the plaques — twelve grants and awards — in a tight grid beside her desk, where she sees them and a funder
sees them being seen. The bible says instrumental is canon ("want: $5M → $50M, to remain in the game"; "radicalism
that is socially costless").

**But the set never states the reading.** THE_CASTE: "the contempt lives in what they DO, never on the face" — and a
set is a face. The bible has her as *genuine believer → collaborator*. So the photographs are hung the way someone
proud of the work hangs them: beautiful, uniform, exact. The audience notices she is in every one. Nothing in the room
knows it is a joke. This is the rule that keeps it from being the easy version, and every prop was checked against it.

## The void where Philip was — twice

Not an unfaded rectangle: there is no aged paint in a white room. Two devices, neither of which announces itself.

**Her nameplate on the glass door reads SUMMER WINTERS.** Winters is his name. She kept it; the bible's own pun
("abundance turned to barrenness") depends on it. His absence is spelled on her door and she walks past it daily.

**One gap in the gallery grid.** Two rows of five, museum-spaced — and one frame missing, the hook still in the wall.
In a room curated to the millimetre, one empty hook is loud, and a visitor cannot tell whether a photograph is being
reframed or a person removed. Which is the point.

## The staff — props for now

Handmaidens for the Queen of New Harnomy. Casting guide (Brad, 2026-09-09 — *guides, not instructions*): revolutionary
chic; rings, some tattoos, earrings, hair expensive but hipster; all very attractive and younger than Summer. A couple
of men in glasses, different body types and clothing — t-shirts, keffiyehs. They render under THE_CASTE's block
(elite schools and a good gym, no visible wear) — the same caste, one generation down, curated. Played serene and
certain, never mean: a sorority queen bee's court, not a mean-girls scene.

In the stage: `Mannequins` state `lysteria` — Summer at `desk_chair`, one at `reception`, four on the benches, heights
1.62–1.80. No LYSTERIA staff exist in the libretto; adding them as characters is a writing decision.

## Canon — the evaluation

| Brief | Verdict |
|---|---|
| White, pink accents, London PR | In keeping; better than the Code-Pink-genre read it replaced. |
| LYSTERIA on the wall in rose | In keeping as a **wordmark in type**, lettered by the gate (text plane). No symbol, no logo mark — kernel negative. |
| Her own office behind glass | In keeping — strong. |
| Larger windows, sun streaming in | **Conflicts with `visual_signature.md`** ("winter daylight stays out of the principals' faces"); resolved as the opera's one deliberate exception, written into the signature. Cold-white, never golden. |
| Causes as instruments, trophies | In keeping — governed by THE_CASTE: the set must not wink. |
| The void where Philip was | In keeping; the aged-paint device is dead in a white room — replaced by the nameplate and the gap. |
| Curated staff | Plausible, not canon; props for now. |

## States, marks, text, cameras

| | |
|---|---|
| `lysteria` variantSet | `working` (default): papers on the benches, one archive box on reception. `launch`: the Man Bun Collective rollout — boards on easels west of the benches (out of her sightline), totes on the benches, four cartons by reception **still shrink-wrapped**, the sash on its stand. |
| `people` | `lysteria` — Summer and the staff. |
| marks | `desk_chair`, `visitor_chair`, `sofa`, `glass_door`, `reception`, `floor_centre`, `window_centre`, `door` |
| text planes | `lyst_wordmark` — LYSTERIA, rose ink. `lyst_nameplate` — SUMMER WINTERS, on the glass door. |
| lighting | `lysteria_morning` (the sun exception), `lysteria_launch` |
| cameras | `LYST_DESK` (32 mm, 2.39:1 — the visitor's view down the aisle, through the glass, to her); `LYST_RECEPTION` (arriving); `LYST_POV` (hers, over the floor); `LYST_IN`, `LYST_IN_BACK` (survey). |

Render: `python3 -m backlot.usd.render_clay LYST_DESK --variants lysteria=launch,people=lysteria`.
Agent: `BLOCKING` puts Summer on `desk_chair`, Dick on `visitor_chair`, Pengold on the `sofa`, Valencia at the
`glass_door`; a card naming the room resolves with zero build items (a card naming a *conference table* is flagged —
there isn't one; the chat happens on the sofa).

## Still open

- Glass in the passes: clay and lineart see through it; seg, depth and normal now hide it. Not yet measured on the box.
- The chairs are the folding-chair primitive in white; a PR office wants better seating past blockout.
- The wordmark ink colour: the gate letters it in the rose; `letter_text_plane.py --ink` takes the value.
- No number puts a camera in this room yet. Every prop here is a proposal until one does.
