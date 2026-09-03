# CASTING SELECTIONS — NEW HARNOMY, U.S.A.

*Step 3.4 complete for all four principals. Brad's picks, 2026-09-02.*

| Character | Cast | File | Status |
|---|---|---|---|
| Valencia Strong | **VAL-H01** | `valencia_v3/VAL-H01.png` | LOCKED. Blend of C05 gravity + C06 ache. Screen-tested at finale Beat 5. |
| Summer Winters | **SUM-K02** | `caste/SUM-K02.png` | LOCKED. |
| Pengold Heavens | **PEN-K03** | `caste/PEN-K03.png` | LOCKED. *"Looks like a political consultant through and through."* |
| Dick Suede | **DIC-K02** | `caste/DIC-K02.png` | Face approved. **Hair modification pending render.** |

---

## Dick — the one outstanding render

**Change:** slightly longer, dirty-blond hair worn to the collarbone — long enough to be gathered into a
man-bun at a minute's notice. Everything else about DIC-K02 stays.

**Why it matters beyond hair:** Summer's initiative is *The Man Bun Collective*. Man-bun-capable hair puts
the name of the organisation she is funding on the body of the man she is sleeping with. No character ever
remarks on it. That is the Wildean law working as designed.

### Use nano_banana_pro, not soul_cinematic

FINDINGS NH-USA-009: `soul_cinematic` accepts one image reference and **does not hold identity** — steering a
face through it produced a different person three times out of four. `nano_banana_pro` held identity first
try on VAL-H01. Cost is **2.00 credits** against 0.12, and it is worth it; do not optimise this step on price.

**Ready to run the moment credits allow:**

```powershell
$D = "<casting>\caste\DIC-K02.png"
higgsfield generate create nano_banana_pro `
  --image-references $D `
  --aspect-ratio "3:2" --resolution 2k --wait --wait-timeout 8m --json `
  --prompt "This exact man, same face, same build, same clothes, same lighting. Change only the hair: slightly longer and dirty blond, worn loose to the collarbone, thick enough to be gathered into a man-bun at a minute's notice, the carefully maintained 'I don't care' cut that takes an expensive barber to look effortless. Head-and-shoulders portrait framed just below the collarbone, hands out of frame, straight-on to camera, plain unlit grey backdrop, mouth closed with the lips together, jaw relaxed, eyes steady on the lens, unbothered and certain. Even neutral daylight-balanced exposure, soft frontal key, natural skin tones, sharp focus on the eyes, photographic realism, 85mm."
```

Then render a second frame with the hair **gathered into the bun** — that is a wardrobe state, not a new
face, and Act III needs it.

---

## Also outstanding

- **All three caste picks are smiling or mid-speech** (NH-USA-011: "pleasant" beat "mouth closed"). Fine as
  character — a media-trained smile is the mask — but the anchor set needs them at rest. 3 stills, 0.36 cr on
  soul_cinematic once the descriptors above are used as text (no reference needed; the descriptors now
  describe the chosen faces).
- **Pengold's build flattened** in the caste pass. He should stay the heavy one against Dick's lean.
  Heaviness is character; the caste rule governs surface only.
- Credits: **0.48 remaining** of the free plan. The Dick modification alone needs 2.00.

## Next after the anchors

Step 3.5 silhouette test (all four at 40px, value only), then 3.7 descriptors are already written, then 3.8
training sets and 3.9 LoRAs. See `../LOOK_DEVELOPMENT_PLAN.md`.
