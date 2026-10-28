# Stage 3.8 — LoRA training sets

72 images, 18 per principal, generated on the EC2 box (g5.2xlarge, A10G) through
ComfyUI + FLUX.2-Klein, each frame carrying its principal's approved anchor as a
`ReferenceLatent`. Seeds are pinned (770000 + index), so **the raw PNGs are not
committed — `gen_trainset.py` plus the seed reproduces any frame exactly.**
Contact sheets ARE committed, because they are the review record.

Cost: EC2 hours only (~$0.98/hr), about 8 minutes of GPU for all 72.

## Why on the box and not through an API

NH-USA-014: every API edit re-draws the face a little. Eighteen independent edits
per character is eighteen slightly different faces, and a LoRA trained on that
averages them into a person who does not exist. Here the anchor is reference
conditioning on every frame and the seed is pinned, so a drifted frame is
reproducible and re-rollable rather than a one-off spend.

## The two-set rule

The CASTING set was lit flat to judge a face. The TRAINING set varies everything
EXCEPT the face — light, angle, distance, expression, wardrobe, background — or
the LoRA learns the key light instead of the person.

Wardrobe needed its own explicit list per character (`WARDROBE`): the reference
latent pins clothing hard, and without an override the LoRA would have baked the
anchor's jacket into the identity.

## Review — regenerated against the LOCKED anchors, 2026-09-03

The first pass of these sets was generated against the pre-revision anchors and is
superseded. After Brad's direction (Summer younger + beatific, Dick softer and
longer-haired, Pengold bearded and soft) all four anchors were re-cut and all 72
frames regenerated. About six minutes of GPU.

| Set | Verdict |
|---|---|
| pengold | **BEST OF THE FOUR.** The hard-won softness held across all 18 — full cheeks, softened jaw, the slicked hair and temple grey consistent, beard dark and neat. Wardrobe genuinely varies (suit, shirt and tie, polo, overcoat, black tie) and the expression range runs from laughing to sombre. |
| valencia | **GOOD, unchanged.** She was never re-anchored. |
| dick | **GOOD — recovered.** The gaunt forty-year-old of the first pass is gone. Long dirty-blond hair, soft features, lean tennis-player build, identity consistent. A few frames still read slightly narrower than the anchor; acceptable. |
| summer | **GOOD on wardrobe, one persistent caveat.** The wardrobe override worked this time — silk blouse, roll-neck, coat, white tee, sleeveless shift all present. Identity holds. She still reads a few years older than her canon thirty-eight in perhaps a third of the frames. |

### The beatific note is deliberately NOT in Summer's training set

Her radiance is a *lighting* fact (NH-USA-020) — a luminous key wrapping the
cheekbones, catchlights, an unfurrowed brow. The training set exists to vary lighting
so the LoRA learns her face rather than her key light, so the beatific quality cannot
and must not survive into it. **It is a per-shot decision at render time**, carried by
the shot spec, not by the LoRA. Baking it in would give us a woman who glows in a
basement.

## The Dick problem — RESOLVED

His first set came back gaunt, in his forties, without the gym build. Prompting could
not fix it: the anchor `DIC-K02-hair-v2` was itself narrower than the approved face and
Klein amplified that over 18 frames (NH-USA-016). Brad's 2026-09-03 direction then
reframed the character — softer, more feminine, a pro tennis player's build, longer
hair — and a new anchor was cut to that brief. Regenerating against it fixed the set.

The lesson generalised into the rule now recorded in `casting/SELECTIONS.md`:
**classify the change before choosing the method.** Surface changes survive an edit
against a reference; structural changes must be generated from text and re-cast.
