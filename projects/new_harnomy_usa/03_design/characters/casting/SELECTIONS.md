# CASTING SELECTIONS — NEW HARNOMY, U.S.A.

*Steps 3.4 and 3.5 complete for all four principals. Brad's picks 2026-09-02; final
anchors rendered and silhouette-tested 2026-09-03.*

## The four anchors — LOCKED

| Character | Cast | Anchor file | Notes |
|---|---|---|---|
| Valencia Strong | **VAL-H01** | `finals/VAL-H01-rest.png` | Blend of C05 gravity + C06 ache. Deliberately ethnically ambiguous (NH-USA-008). Screen-tested at finale Beat 5. Re-lit only — face unmoved. |
| Summer Winters | **SUM-K02** | `finals/SUM-K02-rest.png` | At rest. Attractive by design: v11 §III — *"She's beautiful (he's shallow, she's genuinely attractive)."* |
| Pengold Heavens | **PEN-K03** | `finals/PEN-K03-rest.png` | At rest, build restored. *"Looks like a political consultant through and through."* |
| Dick Suede | **DIC-K02** | `finals/DIC-K02-hair-v2.png` | At rest, dirty blond, hair down (Acts I–II). |
| Dick Suede — Act III | **DIC-K02** | `finals/DIC-K02-bun-v2.png` | Same face, hair gathered. Wardrobe state, not a second casting. |

Superseded, kept for the record: `finals/DIC-K02-hair.png` and `finals/DIC-K02-bun.png`
(first pass — see NH-USA-014, NH-USA-015).

**Why Dick's hair matters beyond hair:** Summer's initiative is *The Man Bun Collective*.
Man-bun-capable hair puts the name of the organisation she is funding on the body of the
man she is sleeping with. No character ever remarks on it. That is the Wildean law working
as designed.

---

## Step 3.5 — silhouette test: PASS (with one caveat)

All four rendered under identical neutral light, reduced to 40px tall, value only
(`/tmp/cast/silhouette_v2.png`, script inline in this directory's history).

| | mean | sd | reads as |
|---|---|---|---|
| Valencia | 127.9 | 46.5 | wide dark hair mass flaring past the jaw, light collar |
| Summer | 75.8 | 36.8 | dark block, light face, light hair — the outlier |
| Pengold | 120.6 | 50.5 | broadest head and neck, light shirt V |
| Dick | 121.0 | 42.2 | narrowest head, hair close to the skull, long neck |

**Caveat, stated plainly:** value alone does NOT separate Valencia, Pengold and Dick — they
sit within 8 points of each other. The separation is carried entirely by *outline*: Pengold's
mass, Valencia's hair flare, Dick's narrow head and long neck. That is legible, but it is a
thinner margin than the plan assumed. If a wide shot ever needs more, the lever is wardrobe
value, not face.

The first Dick pass FAILED this test — hair to the collarbone read as a woman's long hair and
collided with Valencia's outline. Fixed in v2 by cutting the sides close so the skull reads.

---

## Next

3.8 training sets (~18 images per principal, varied light — the casting set judges the face,
the training set teaches it), 3.9 four LoRAs serial on the g6e box from `ami-04ef6582604f56a4a`,
3.10 verification, 3.11 register in `lora_library.json`, 3.12 stop the box.
See `../LOOK_DEVELOPMENT_PLAN.md`.
