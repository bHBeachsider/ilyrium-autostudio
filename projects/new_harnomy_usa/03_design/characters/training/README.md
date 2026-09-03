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

## Review, 2026-09-03

| Set | Verdict |
|---|---|
| valencia | **GOOD.** Identity holds across all 18. Light, wardrobe, expression and background all vary. Reads a few years older than her canon late twenties. |
| pengold | **GOOD — the best of the four.** Heavy through the face and shoulders as canon requires; expression range from laughing to sombre. |
| summer | **ACCEPTABLE, one caveat.** Identity holds, but she reads mid-to-late forties rather than "early forties *maintained to read younger*" — and the maintenance is the character point. The blazer also survived the wardrobe override in most frames. |
| dick | **NOT APPROVED.** See below. |

## The Dick problem — open decision

His set came back gaunt, in his forties, without the gym build, and with the hair
drifted into a slicked-back mullet rather than the approved cut. A second pass
with every preserved quality given its own positive clause (NH-USA-016) moved it
perhaps a fifth of the way and no further.

Root cause is upstream of this step: `DIC-K02-hair-v2` is itself slightly narrower
than the DIC-K02 face Brad approved (recorded at NH-USA-014), and Klein amplifies
that drift over 18 frames. Prompting cannot outvote the reference.

**The recommendation is to re-anchor him on the original `caste/DIC-K02.png`** and
let the training set carry that face with its original hair. A character LoRA's
job is bone structure; hair is a per-shot variable — and Dick needs TWO hair states
(down for Acts I–II, gathered for Act III) regardless, so baking either one into
the LoRA is wrong on its own terms.
