#!/usr/bin/env python3
r"""Stage 3.5 RE-ANCHOR pass 2 - Summer's radiance, Pengold's softness.

WHY PASS 1 UNDER-DELIVERED (NH-USA-020)
---------------------------------------
Both misses were the same mistake: I named an INTERIOR quality ("beatific",
"soft and squishy") and the model answered with a SURFACE change (younger skin,
a beard). A diffusion model cannot render an inner state. It renders light,
tissue and geometry. So each abstraction is now decomposed into its physical
correlates and the abstraction itself is stated only once, at the end, as a
summary of what those correlates add up to.

  SUMMER   Beatific is a LIGHTING fact before it is an expression. In an
           altarpiece the saint is lit from a source the viewer cannot see, the
           brow is completely unfurrowed, the eyes are clear and open, and the
           mouth rests softly closed rather than pressed. Pressed lips read as
           control; that is what pass 1 gave us.
  PENGOLD  Squish is TISSUE. Rounded lower cheeks, a jaw angle softened and
           partly obscured, a little fullness under the chin at a level head,
           a well-fed colouring. Stated positively - NH-USA-006 - and fenced
           by what stays trim, so "not fat" survives as a shape rather than a
           negation the model will drop.

Cost: two images, ~$0.30.
"""
import os
import sys
import urllib.request

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "reanchor")
R = OUT

for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env",
            r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

FRAME = ("Head-and-shoulders portrait framed just below the collarbone, hands out of "
         "frame, straight-on to camera, plain unlit grey backdrop, natural skin tones, "
         "photographic realism, 85mm, sharp focus on the eyes.")

JOBS = [
 ("SUM-R03", os.path.join(R, "SUM-R01.png"),
  "Keep this exact woman completely: identical face, identical bone structure, "
  "identical age, identical ash-blonde chignon, identical dark blazer. Do not change "
  "her features. Change only the LIGHT on her and the set of her face. "
  "Light her as a saint is lit in a Renaissance altarpiece: a soft luminous key from "
  "just above and in front, the light wrapping gently around the cheekbones and brow "
  "so the skin seems lit from within, a faint glow along the forehead, the temples "
  "and the top of the cheeks, luminous near-translucent skin, and one bright clear "
  "catchlight in each eye. "
  "Set the face at complete peace: the brow entirely smooth and unfurrowed with the "
  "skin relaxed between the eyebrows, the eyes open, clear and untroubled and looking "
  "steadily out at the lens, the lips softly closed and resting together without any "
  "press or tension, the jaw loose, the neck long and the chin carried level. "
  "The whole reads as serene, radiant and already elevated - grace rather than "
  "satisfaction. " + FRAME),

 ("PEN-R03", os.path.join(R, "PEN-R01.png"),
  "Keep this exact man completely: identical eyes, identical nose, identical dark hair "
  "combed back, identical short well-manicured hipster beard, identical dark suit and "
  "crisp white shirt. Change only the flesh of his face and neck. "
  "Give him the soft well-fed body of a man who eats out constantly: full rounded "
  "lower cheeks with a comfortable padding over them, the angle of the jaw softened "
  "and partly hidden beneath that fullness so the jawline reads as a gentle curve "
  "rather than an edge, a small soft fullness under the chin where it meets the neck "
  "even with his head level, a fuller neck sitting comfortably against the shirt "
  "collar, and smooth pink well-fed colouring with no muscle definition anywhere in "
  "the face. "
  "His shoulders, chest and frame stay trim and the suit stays clean and well-fitted "
  "on him - the softness lives only in the face and neck. Smooth, unweathered, "
  "pampered and indoor: a comfortable man, plush rather than large. " + FRAME),
]


def preflight():
    key = os.getenv("FAL_KEY")
    if not key:
        sys.exit("[FAIL] FAL_KEY not set. Check .env.")
    r = httpx.post("https://rest.fal.ai/storage/auth/token?storage_type=fal-cdn-v3",
                   headers={"Authorization": "Key " + key}, timeout=30)
    if r.status_code == 403 and "balance" in r.text.lower():
        sys.exit("[FAIL] fal balance exhausted. Top up at fal.ai/dashboard/billing.")
    if r.status_code in (401, 403):
        sys.exit("[FAIL] fal auth rejected (%s): %s" % (r.status_code, r.text[:200]))
    print("[OK] fal auth and balance OK (probe %s)" % r.status_code, flush=True)


def main():
    preflight()
    import fal_client
    os.makedirs(OUT, exist_ok=True)
    for name, src, prompt in JOBS:
        if not os.path.exists(src):
            print("[SKIP] %s - source missing: %s" % (name, src), flush=True)
            continue
        print("-- %s" % name, flush=True)
        try:
            url = fal_client.upload_file(src)
            res = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={
                "prompt": prompt,
                "image_urls": [url],
                "aspect_ratio": "3:2",
                "resolution": "2K",
                "output_format": "png",
                "num_images": 1,
            })
            images = res.get("images") or []
            if not images:
                print("   [FAIL] no image: %s" % str(res)[:200], flush=True)
                continue
            dst = os.path.join(OUT, name + ".png")
            urllib.request.urlretrieve(images[0]["url"], dst)
            print("   [OK] %s (%d KB)" % (name, os.path.getsize(dst) // 1024), flush=True)
        except Exception as exc:
            print("   [FAIL] %s: %s" % (name, exc), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
