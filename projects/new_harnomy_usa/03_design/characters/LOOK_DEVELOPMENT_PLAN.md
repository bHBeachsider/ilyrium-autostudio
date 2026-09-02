# STAGE 3 — CHARACTER LOOK DEVELOPMENT & LoRA PLAN

*NEW HARNOMY, U.S.A. — 2026-09-02. How the four principals get a face, and how that face becomes a LoRA.
Scope decided 2026-09-01: LoRAs for Summer, Pengold, Dick, Valencia. Not Bildersatz (one portrait, rendered
once). Not Philip (offstage; revisit if the libretto gives him more than a handful of shots).*

---

## 0. The method: cast first, describe second

The usual AI workflow is *write a description, then generate*. That is backwards for a feature, and it is why
the bibles currently carry PHYSICAL sections marked "(proposed, not in v11; refine at Stage 3)" and descriptors
that say "fill hair/eye specifics at Stage 3 anchor lock." Nobody can describe a face they have not seen.

So we run a **casting session**, the way a real production would:

1. Generate a slate of candidates per character, varying only what canon leaves open.
2. Brad picks one face.
3. **Then** the LOCKED VISUAL DESCRIPTOR is rewritten to describe the face that was chosen.

The descriptor becomes a record of a decision instead of a guess. Everything downstream — keyframes, shot
prompts, the LoRA — inherits a face that was selected, not stumbled into.

### The two image sets people conflate

This is the distinction that matters most, and the current `ANCHOR_MANIFEST.json` does not yet make it:

| Set | Purpose | Lighting | Count | Judged by |
|---|---|---|---|---|
| **Casting set** | Choose the face | Hero look, consistent — so candidates differ by face, not by lighting | 6 per character | Brad |
| **Training set** | Teach the LoRA | **Deliberately varied** — lighting, angle, expression, wardrobe | ~18 per character | Automated + spot check |

Training on a single lighting setup bakes that lighting into the identity. Varying it makes the LoRA learn the
*face* rather than one Deakins tungsten key — which is also what makes the LoRA survive the Gate 0 frame
decision. Bone structure does not change if the film becomes a recording of a stage premiere; grade and key
light do. Vary them in training and identity stops being frame-dependent.

**Corollary — train the face, not the wardrobe.** Dick's $1,500 outfit is the most specified thing in v11 and
must NOT be fused into his LoRA. Wardrobe varies across the training set; it is locked separately on a wardrobe
board. Brad's own Stripe LoRA notes record this failure mode ("the char LoRA over-fits front").

---

## 1. What the slate varies, and what it must hold

Canon fixes age band, casting look, build register, wardrobe register and affect. The slate varies only the rest.
Per character, the creative brief for the casting session:

### VALENCIA — do her first
*Mezzo. The Greek chorus. The only character who tells the truth.*

- **Hold:** late 40s; European Mediterranean-rim or Eastern; unglamorous; real clothes worn more than once this
  week; working hands; no makeup performance; flat honest documentary light.
- **Vary:** hair (cropped practical / tied back / greying); build (solid / wiry); face (broad / angular).
- **The trap:** every image model drifts toward attractive. v11 is explicit that her costume is "the exception
  that proves the rule — real clothes, practical clothes." If Valencia reads as an actress *playing*
  working-class, the Wildean device collapses and the opera loses its one honest voice.
- **The test question:** does she read as staff, or as cast?
- **Why first:** simplest look, no style complications. She is the pipeline control. If we cannot hold Valencia,
  we cannot hold anyone.

### SUMMER — do her second
*Soprano. The moral center. The hardest identity problem in the film.*

- **Hold:** early 40s; patrician bearing; slim, upright, still; professional-class activist tailoring, expensive
  and muted; composure that hides cost.
- **Vary:** hair colour and how it is worn; face width; warmth vs. coolness of affect.
- **The trap:** her face has to do two incompatible things. The Act III portrait shows her "heroic, idealized,
  bathed in golden light — a mother of the movement despite her barrenness." Beneath it, her real face is
  "recognition, horror, the knowledge that she chose this." A face too cold cannot be idealized; a face too warm
  cannot freeze.
- **Why second, not last:** if the portrait problem is unsolvable it changes the finale design, and we want that
  news early.

### PENGOLD — third
*Baritone. The machine. Carries two of the three load-bearing silences.*

- **Hold:** American, Northeast working-class origin; mayoral gravitas; controlled.
- **Vary:** heaviness; hairline; how easily the acquired polish sits.
- **The trap:** casting him smooth. His whole character is origin showing through acquired polish — a man
  wearing a class he learned. v11: "he cannot find the person who existed before the construction began." The
  face should show construction. Something slightly effortful.
- **The test question:** is the face **readable at rest**? He opens the opera with a twenty-two-second silent
  read and closes it with the smallest possible smile, held. He does more acting with less than anyone.

### DICK — fourth
*Tenor. The sacrifice. His fall must land as pathos.*

- **Hold:** cast European (Berlin-via-Antwerp gallerist's-son face), plays an American trust-fund heir;
  grown-out product-free hair, expensively maintained; softness.
- **Vary:** age read (late 20s / mid 30s); hair length; wire-frame glasses on or off.
- **The trap:** making him punchable. "Little Dickie" — the family called him soft, and he must look like
  someone who has never had to be hard. If the slate produces a face the audience wants to see arrested, the
  ending does not work.
- **Wardrobe is a separate lock.** Build his wardrobe board from v11's list (selvedge denim, Common Projects,
  vintage band tees, Engineered Garments/RRL/Kapital workwear, keffiyeh scarf, canvas tote) as its own
  approved asset — and keep it *out* of the LoRA.

### The silhouette test — all four together
Before any face is locked, render the four chosen candidates side by side at **40 pixels tall, in value only**
(desaturated, no colour). In a film with a chorus, crowds, festival wides and a full stage picture, an audience
that cannot tell four principals apart at a glance loses the plot. If two silhouettes collide, change one —
height, build, hair mass or hairline — before locking. This is cheap now and impossible later.

---

## 2. The likeness screen — non-negotiable

Every character is specified by age, origin, build, wardrobe and affect only, **never by likeness to a real
person**. That is the kernel's `legal_rule` and the A4 release gate checks it at the end.

Two Stage-3 rules that keep it clean:

1. **Source images are generated from text, not photographs of real people.** The `loras/README.md` scaffold
   suggests `source/` holds "public-domain portraits, engravings, photos" — that workflow came from Broderick
   (an author-avatar) and Stripe (an original cartoon). It does **not** apply here. New Harnomy's faces are
   generated, and the training set is derived from the approved generated anchor.
2. **Screen the slate before selection.** Reverse-image-check each candidate and reject anything that reads as a
   recognisable public figure. Catching it now costs one regeneration; catching it at A4 costs an act.

---

## 3. Use the proven training path, not the scaffold's

The NH scaffold points at Tensor.art with `"base_model": "TENSORART_BASE_MODEL_ID_TBD"` — an open question from
May 2026 that was never resolved. Meanwhile three LoRAs were trained successfully on **FLUX.1-dev**, with
artifacts sitting in `s3://ilyrium-slm-foundry/models/`. Use what works.

| Decision | Value | Grounded in |
|---|---|---|
| Base model | `black-forest-labs/FLUX.1-dev` | broderick_char, broderick_flux_v2, stripe_char_v2 all trained on it |
| Training set size | **17-20 images** | Broderick 17, Stripe v2 19 — the house number that produced usable LoRAs |
| Network | dim 16 / alpha 8 | `lora_train_config.example.json`: "larger is not better" |
| Resolution | 768 | same config |
| Strength at render | 0.85-0.9 | the strengths recorded for the working LoRAs |
| Checkpoints | save every N epochs, **pick by preview** | S3 shows saved intermediates (`_000001000`, `_000001250`, `_000001500`, `_000001750`) and a chosen one |
| **Never** | Astria API tunes | `stripe_young` has been `status: pending` since July 2026 — Astria tunes have no downloadable checkpoint |

### The trigger-word lesson — read this before writing shot prompts

Brad's library records it twice, validated: **on Flux a rare trigger token does not bind the way it does on
SDXL.** `brdmc` alone yielded "inconsistent photoreal people, no ink." `brdrck` alone yielded "generic cartoon."
Both work only when the prompt *also* describes the subject.

So for New Harnomy: **the LoRA does not replace the LOCKED VISUAL DESCRIPTOR — it reinforces it.** Every shot
prompt keeps the full descriptor and adds the trigger. The descriptor stays load-bearing forever. This is
already how `build_anchor_manifest.py` assembles prompts, and it must stay that way after the LoRAs exist.

---

## 4. The plan, in order

| # | Step | Output | Owner | Gate |
|---|---|---|---|---|
| 3.1 | Split `build_anchor_manifest.py` into two generators: casting slate (6 candidates x 4 principals, hero look) and training set (varied lighting/angle/expression/wardrobe) | two manifests | me | prompts hold canon, vary only the open axes |
| 3.2 | Render the casting slate — 24 stills | contact sheet per character | me | cloud path; no GPU box needed |
| 3.3 | **Likeness screen** the 24 | pass/fail per candidate | me | nothing resembling a real person survives |
| 3.4 | **Brad picks one face per principal** | 4 selections | **Brad** | the irreducible human step |
| 3.5 | **Silhouette test** — four at 40px, value only | one sheet | me -> Brad | four distinguishable silhouettes, or revise one |
| 3.6 | **Portrait test (Summer)** — her chosen face rendered as a Socialist-Realist painted portrait at poster, background, half-height and apex scales | 4 renders | me -> Brad | reads as the same woman across the style gap |
| 3.7 | Rewrite each LOCKED VISUAL DESCRIPTOR to describe the chosen face; bump the kernel | 4 bible edits | me | descriptor matches the anchor, not the guess |
| 3.8 | Generate the training set — ~18 per principal, img2img from the approved anchor, denoise 0.60-0.70, varied | 72 images | me | same face throughout; wardrobe and light vary |
| 3.9 | Launch the box from `ami-04ef6582604f56a4a`; train four LoRAs **serially** (8-vCPU quota = one box) | 4 `.safetensors` | me | per-epoch previews reviewed, best checkpoint picked |
| 3.10 | Verification stills — 6 per LoRA against the anchor | 24 stills | me -> Brad | same face; register held; no wardrobe fusion |
| 3.11 | Push to `s3://ilyrium-slm-foundry/models/new_harnomy/`, register in `lora_library.json` with sha256 + trained_at + `status: trained`, pin in `models.lock.json` | registry entries | me | render engine resolves `keyframe.ref_lora` |
| 3.12 | **STOP the box** | — | me | billing off |

### Definition of done, per character
- An approved anchor set (3 angles x 2 aspects) in `anchors/`.
- A LOCKED VISUAL DESCRIPTOR that describes the approved face.
- A trained `.safetensors` in S3, registered with `sha256`, `trained_at`, `status: trained`.
- Six verification stills that read as the same person as the anchor.

---

## 5. Cost, time, and what actually paces it

| Line | Estimate |
|---|---|
| Casting slate, 24 stills | ~3 Higgsfield credits (of 10 on the free plan) or ~$4 on fal |
| Training sets, 72 images | box time, or ~$10 cloud |
| LoRA training, 4 serial | ~3-4 box-hours ≈ **$5** |
| Verification, 24 stills | ~$3 |
| **Generation total** | **~$25** |

Elapsed: **about a week**, and almost all of it is Brad looking at faces. The generation is hours; the judgment
is the schedule. Steps 3.4, 3.5, 3.6 and 3.10 are the only ones that cannot be delegated, and 3.4 is the one
that unblocks everything.

**Only step 3.9 needs a GPU box.** Everything before it runs on the cloud path, so the casting session can start
before the terminated box is relaunched.

---

## 6. Relationship to the other gates

- **Gate 0 (frame decision)** does not block the casting session. Identity is frame-independent once the
  training set varies its lighting (see §0). What Gate 0 *does* change is the style kernel's grade and key —
  which affects shot rendering, not who these people are.
- **Gate 2 (the finale vertical slice)** needs all four principals in close-up, so there is no cheaper subset to
  prove the pipeline on. Stage 3 is Gate 2's input.
- **Open question worth settling at 3.10:** whether the LoRAs are needed at all. Render two of the finale's
  close-ups both ways — anchors plus multi-reference vs. anchors plus LoRA — and keep the evidence. Costs
  almost nothing on top of work already scheduled, and it answers the question with pictures instead of
  assumption.

*Companion docs:* `00_admin/CCO_ASSESSMENT.md` (capacity verdict and gates) · `loras/README.md` (authoring home
— note its Tensor.art recipe is superseded by §3 above) · `SOUL_ID_PLAN.md` · `CASTING_CANON.md`.
