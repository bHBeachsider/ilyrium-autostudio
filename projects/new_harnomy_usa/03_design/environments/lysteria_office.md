# LYSTERIA — Summer's office

Set: `LysteriaInterior` (backlot asset). Upper floor of `shop_e1`, the north row's east end; three windows onto the
square, door at the north-west corner. Room 9 × 14 m, ceiling 3.2 m, floor at z = 4.2.
Design brief, Brad, 2026-09-09: *"in the style of a feminist NGO like Code Pink."*

## The thesis

The reference is the **genre**, not any real organisation — every mark in this room is LYSTERIA's own.

And the room is not scrappy. LYSTERIA is ten years old, well funded and respected (`world/factions.md`), and Summer
was raised in elite rooms. Playing the office as grassroots protest craft would be the easy joke and the wrong one.
The satire is that the room **performs the movement it has outgrown**: protest craft, bought.

Four decisions carry it.

**The craft is behind glass.** Three handmade banners hang framed on the west wall, lit like art. A banner in a frame
has stopped being a banner. This is the room's thesis in one prop, and it is the first thing a visitor sees on the
way to a chair.

**The plaques are what the room is actually proud of.** Twelve grant and award plaques in a tight grid on the east
wall, beside Summer's desk where she sees them and a funder sees them being seen. The banners get the long wall; the
plaques get the money wall.

**The rose is drained.** LYSTERIA's brand colour sits a half-step from the mauve of the paperbacks — the same family,
one lifted and one aged. The visual signature allows only two saturated events (the portrait's Socialist-Realist gold
and, deliberately un-saturated, the mauve), and this is not one of them. The pink is present and dead. Material
`rose = (0.64, 0.44, 0.48)`; the books stay on `banner`.

**The launch outnumbers the services.** The Man Bun Collective is six months old with zero services delivered. In the
`launch` state that is literal: two presentation boards on easels at the presenting end, tote bags out on the
conference table, and four cartons by the door **still shrink-wrapped**. Nothing in the room does anything; all of it
announces.

## Blocking

Summer sits with the square behind her, so a visitor faces the window and she reads the visitor's face against the
light. Her desk is at the south end; the conference table — the donor-and-press half of the room — is in the middle,
six chairs addressing it; the tea and natural-wine credenza is by the door where arrivals meet it.

Marks (`LYST_CONTROL`, composed into the stage as ControlPoints): `desk_chair` (seated, facing into the room),
`table_head` (standing at the head of the conference table), `window_centre` (standing at the windows, facing back
into the room), `door`.

## States

| state | what changes |
|---|---|
| `working` *(default)* | Ordinary morning: document boxes open on the conference table, papers, desk lamp on. |
| `launch` | The Festival rollout staged: boards on easels, totes on the table, cartons stacked by the door, the sash on its stand. |

Driven by the `lysteria` variantSet on `/World`. Render with
`python3 -m backlot.usd.render_clay LYST_DESK --variants lysteria=launch`.

## Text planes

`lyst_mission` — east wall, lettered by the gate rather than by the diffusion (the kernel forbids on-screen text
generated into the image, and OCR-gating requires we own the letters):

> LYSTERIA COALITION FOR REPRODUCTIVE JUSTICE
> EVERY BODY. EVERY CHOICE. EVERY TIME.

The strapline is placeholder — it is written to sound like the genre and to be replaced by the writer. The
organisation's name is canon; the line under it is not.

## Cameras

`LYST_DESK` (24 mm, 2.39:1) — the visitor's view: in at the door, down the room past the table to Summer against the
windows. `LYST_IN` and `LYST_IN_BACK` are the two survey ends.

## One proposal, flagged not assumed

`lyst_ghost_frame` — an unfaded rectangle on the east wall where a frame used to hang. Philip is two years gone and
the wall has not been repainted; the casting bible already carries *"bare ring finger, no mark — the skin has
forgotten, the same erasure she performs on Philip."* This is that note, in the set. It costs two lines and reads at
any focal length. **Delete it if the writer would rather she never hung him at all** — which is a different and also
true version of her.

## Still open

- The chairs are folding chairs, correct for the PILF storefront and too cheap for this room; Summer's office wants
  proper seating once the set goes past blockout.
- No lighting state registered yet in `world/nh/lighting.yaml` — the room needs one (`lysteria_day`: thin cool window
  light from the south, one warm desk lamp, per the world's single-source rule).
- No scene cards name this room yet, so no shot cameras beyond the survey three and no prompt book.
