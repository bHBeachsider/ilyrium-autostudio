# Broderick Character-Consistency LoRA — Spec

## The problem this solves
The `brdrck` Hand is a **STYLE** LoRA — it locks the *look* (scratchy grayscale ink, deadpan
staging, white void) but **not identity**. Across a multi-panel storyboard the recurring character
*drifts*: the protagonist's face/build/glasses change panel to panel. A **CHARACTER** LoRA binds a
unique trigger to one specific person so they render the same everywhere.

| | Style LoRA (`brdrck`) | Character LoRA (this spec) |
|---|---|---|
| Captures | the artistic idiom | one specific person's identity |
| Trigger | `brdrck` | `brdmc` (Broderick main character — must NOT collide) |
| Trained on | 173 varied panels | 20–40 images of *the same character* |
| At inference | always on | added when that character is in-panel |

## Scope — start with ONE character
The obvious first target is the **Broderick author-avatar**: the *heavyset bald man with a full
graying beard and thick black rectangular glasses* who recurs across the memoir strips
(`autobiography_707b` panels 2/5/6, and others). Ship a LoRA for him first; repeat the recipe for
any other frequently-recurring character later. One-off characters do NOT need a LoRA (use
IP-Adapter — see Alternatives).

## Dataset construction — the crux (character LoRAs live or die here)
A character LoRA needs **many views of the same identity**, reasonably isolated, varied in pose and
expression, all unmistakably the same person. The corpus has the character but *embedded in scenes*.
Pipeline:

1. **Pin the canonical description.** From the manifest captions, fix the avatar's invariant
   features (bald, full graying beard, thick black rectangular glasses, heavyset, gray work shirt).
   **Best seed: a `character bible` reference sheet** — front/¾/profile + a few expressions —
   ideally one Broderick draws or approves. His sign-off on "this is the canonical him" anchors
   everything (the recurring lever, again).
2. **Mine the corpus for instances.** Scan manifest captions (+ transcripts) for panels containing
   the avatar → candidate panels. A vision model (Qwen3-VL, already wired) can confirm presence and
   return a **bounding box**; crop the character region from each → real, authoritative identity
   crops. Expect maybe ~10–25 usable crops — likely *below* the comfortable floor.
3. **Expand to ~20–40 via reference-anchored generation.** Take the strongest 1–3 canonical crops
   as **IP-Adapter** references and generate varied poses/angles/expressions *in `brdrck` style*;
   **curate hard** — keep only generations whose identity matches the reference. (This is the
   bootstrap: the style LoRA can't hold identity, so you generate broadly and *select* the on-model
   ones.) GPU step.
4. **Caption + trigger.** Each image: `brdmc, <pose/expression/framing>` — e.g.
   `brdmc, shouting and pointing, medium close-up`. The trigger must be a rare token that does not
   appear in the style dataset's captions (avoid `brdrck`-prefix collisions).
5. **Integrity check.** Every image is the *same* identity (no near-misses), varied poses, clean-ish
   crops. A poisoned set (mixed identities) is worse than a small clean one — bias to clean.

## Training
- ai-toolkit Flux LoRA (same rig as the Hand), `is_flux: true`, FLUX.1-dev (text/face fidelity).
- Rank lower than the style LoRA — identity is narrower: `linear 8–16 / alpha = rank`.
- ~1500–2500 steps for 20–40 images, `save_every 250`, sample with the `brdmc` trigger.
- Resolution `[768, 1024]`; quantize true on 24GB / off on the 48GB L40S.
- Cost ≈ a Hand run (~$5–6 on the L40S).

## The key technical risk — stacking style + character
Two LoRAs on one base can fight or dilute. Three options, in order of preference:
1. **Stack at inference** (modular): load `brdrck` (style ~0.9) + `brdmc` (character ~0.8); **tune the
   two weights** on a test grid until identity holds without flattening the style. Most flexible.
2. **Style-inclusive character LoRA**: because the corpus crops are *already in `brdrck` style*, a
   character LoRA trained on them captures identity *and* style entangled — it renders the avatar
   in-style standalone. Simpler at inference, but not reusable for other characters and can muddy the
   pure style. Acceptable for the protagonist specifically.
3. **IP-Adapter only** (no character LoRA): a reference image at inference. Lightest; good enough for
   short storyboards or one-off characters; weaker for a constantly-recurring lead than a LoRA.

Decide empirically: train (1), and if stacking is unstable, fall back to (2).

## Evaluation gate
- **Cross-pose identity grid**: generate `brdmc` in ≥6 varied scenarios (seated, shouting, driving,
  small/large in frame). Identity (face, beard, glasses, build) must read as the same person.
- **Stacking test**: same prompts with `brdrck` + `brdmc` at the chosen weights — style intact AND
  identity held.
- **Drift-across-strip test**: render a 4-panel sequence; the lead must look consistent panel-to-panel.
- **HITL**: Broderick confirms "that's the guy" — identity is his call.

## Integration with the Brain + storyboard loop
- Extend the Brain's panel schema with `characters_present: [str]` per panel (operator extraction
  can already note recurring figures).
- Renderer injects the right triggers per panel: always `brdrck`; add `brdmc` when the protagonist
  is present (later, `brdXX` for other character LoRAs).
- Strip compositor lays the panels out; dialogue/balloons composited in post (PIL).
- Net: premise → Brain (breakdown + characters_present + prompts) → Hand (style + character LoRAs)
  → consistent multi-panel storyboard.

## Honest limits
- Diffusion character consistency is **hard**; a LoRA dramatically improves it but won't be perfect —
  extreme angles/expressions still drift. IP-Adapter or a reference per panel can backstop hard cases.
- The corpus likely yields too few clean crops alone → the IP-Adapter expansion + curation is
  mandatory, and curation quality caps the result.
- Needs a GPU box for steps 3 (expansion) and training.

## Sequencing
1. (No GPU) Mine the corpus for avatar crops via Qwen3-VL bounding boxes; get/approve a character
   bible from Broderick.
2. (GPU) IP-Adapter-expand + curate to a clean 20–40-image `brdmc` set.
3. (GPU) Train the character LoRA; run the eval grid + stacking test.
4. Wire `characters_present` into the Brain schema + renderer.
