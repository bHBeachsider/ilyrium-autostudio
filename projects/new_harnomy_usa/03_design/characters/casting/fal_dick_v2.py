#!/usr/bin/env python3
r"""Stage 3.5 CORRECTION - Dick, second hair pass.

Two problems with DIC-K02-hair / DIC-K02-bun (first pass):

  1. IDENTITY DRIFT. "slightly longer, worn loose and falling to the collarbone"
     was a large enough edit that nano-banana-pro re-drew the face along with the
     hair - it came back leaner, more chiselled and more male-model than the
     approved DIC-K02. The face is the thing under selection; it must not move.

  2. SILHOUETTE FAILURE (step 3.5). At 40px, value only, hair to the collarbone
     reads as a woman's long hair, and its outline collides with Valencia -
     same mid-grey field, same dark mass framing a narrow face. Dick and
     Valencia must be separable in a wide shot.

The fix is the same one in both cases: less hair, and lock the face explicitly.
The length that actually makes a man-bun lives at the crown and the back, not at
the sides - cutting the temples close restores the skull shape, reads male at
40px, and still gathers.

Cost: $0.15/image at 2K. Two images = ~$0.30.
"""
import os
import sys
import urllib.request

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "finals")
SRC = os.path.join(HERE, "caste", "DIC-K02.png")

for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env",
            r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

FRAME = ("Head-and-shoulders portrait framed just below the collarbone, hands out of "
         "frame, straight-on to camera, plain unlit grey backdrop, even neutral "
         "daylight-balanced exposure, soft frontal key, shadows open and detailed, "
         "natural skin tones, photographic realism, 85mm, sharp focus on the eyes.")

REST = ("Mouth closed with the lips together, jaw relaxed, eyes steady on the lens, "
        "the expression completely neutral and still, unbothered and certain.")

# The face lock. Stated positively and specifically - NH-USA-006.
FACE = ("Keep this exact man. Hold his face identical to the source: same bone "
        "structure, same width across the cheekbones and jaw, same weight in the "
        "cheeks, same nose, same eyes, same brow, same tan and skin texture, same "
        "gym-built shoulders, same heritage workwear jacket over a plain fitted tee. "
        "Keep the face exactly as ordinary and as solid as it is in the source. ")

JOBS = [
    ("DIC-K02-hair-v2", FACE +
     "Change ONLY the hair. Dirty blond. Cut close at the temples and above the ears "
     "so the shape of the skull reads clearly at the sides, with the length kept on "
     "top and at the back, the longest strands reaching the jawline and no further, "
     "swept back off the forehead and sitting close to the head. A grown-out men's "
     "cut, thick on top, long enough to gather at the crown - the carefully "
     "maintained 'I do not care' cut that takes an expensive barber to look "
     "effortless. " + REST + " " + FRAME),

    ("DIC-K02-bun-v2", FACE +
     "Change ONLY the hair. Dirty blond, cut close at the temples and above the ears, "
     "the length on top and at the back gathered up into a small tight bun high at the "
     "back of the crown, the sides swept back cleanly and flat to the head, a few "
     "short strands loose at the temples. " + REST + " " + FRAME),
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
    if not os.path.exists(SRC):
        sys.exit("[FAIL] source missing: %s" % SRC)

    url = fal_client.upload_file(SRC)
    for name, prompt in JOBS:
        print("-- %s" % name, flush=True)
        try:
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
