#!/usr/bin/env python3
r"""Stage 3 FINAL ANCHORS - all four principals, via fal nano-banana-pro/edit.

Fixes every outstanding item from the casting pass in one run:

  SUM-K02  at rest        NH-USA-011: "pleasant" beat "mouth closed" - she is smiling
  PEN-K03  at rest + bulk NH-USA-011, plus the caste pass flattened his build. He is
                          the heavy one against Dick's lean; the caste rule governs
                          SURFACE, not build.
  DIC-K02  hair loose     Cast face + the man-bun-capable dirty blond (Acts I-II)
  DIC-K02  bun gathered   The same hair up (Act III)
  VAL-H01  relight only   Already at rest and LOCKED. Re-lit ONLY to match the other
                          three so the silhouette test compares like with like.
                          Her face must not move.

WHY nano-banana-pro: NH-USA-009 - soul_cinematic accepts one reference and does not
hold identity; steering a face through it returned a different person three times out
of four. nano_banana_pro held VAL-H01 first try.

Run:  venv\Scripts\python.exe projects\new_harnomy_usa\03_design\characters\casting\fal_cast_finals.py

Cost: $0.15/image at 2K. Five images = ~$0.75. Pay-as-you-go, no subscription.
"""
import os
import sys
import urllib.request

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "finals")

for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env",
            r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

# Held constant so the four anchors are directly comparable at the silhouette test.
FRAME = ("Head-and-shoulders portrait framed just below the collarbone, hands out of "
         "frame, straight-on to camera, plain unlit grey backdrop, even neutral "
         "daylight-balanced exposure, soft frontal key, shadows open and detailed, "
         "natural skin tones, photographic realism, 85mm, sharp focus on the eyes.")

# Positive phrasing only - NH-USA-006: negations do not hold.
REST = ("Mouth closed with the lips together, jaw relaxed, eyes steady on the lens, "
        "the expression completely neutral and still, unbothered and certain.")

JOBS = [
    ("SUM-K02-rest", os.path.join(HERE, "caste", "SUM-K02.png"),
     "Keep this exact woman: same face, same ash-blonde hair in a low chignon, same "
     "narrow face and lightly tanned flawless skin, same dark blazer over a fine plain "
     "knit. Change ONLY the expression: close the mouth and settle the face completely "
     "at rest. " + REST + " " + FRAME),

    ("PEN-K03-rest", os.path.join(HERE, "caste", "PEN-K03.png"),
     "Keep this exact man: same face, same dark hair combed back, same strong brow, "
     "clean-shaven, same immaculate dark suiting and crisp white shirt. Change TWO "
     "things: close the mouth and settle the face completely at rest; and make him "
     "heavier and broader through the shoulders, neck and jaw - a big man who lifts, "
     "substantial in the suit. " + REST + " " + FRAME),

    ("DIC-K02-hair", os.path.join(HERE, "caste", "DIC-K02.png"),
     "Keep this exact man: same face, same bone structure, same tan and skin, same "
     "gym-built shoulders, same heritage workwear jacket over a plain fitted tee. "
     "Change ONLY the hair: dirty blond and slightly longer, worn loose and falling to "
     "the collarbone, thick enough to be gathered into a man-bun at a minute's notice "
     "- the carefully maintained 'I do not care' cut that takes an expensive barber to "
     "look effortless. " + REST + " " + FRAME),

    ("DIC-K02-bun", os.path.join(HERE, "caste", "DIC-K02.png"),
     "Keep this exact man: same face, same bone structure, same tan and skin, same "
     "gym-built shoulders, same heritage workwear jacket over a plain fitted tee. "
     "Change ONLY the hair: dirty blond, gathered up into a neat man-bun at the crown "
     "with a few loose strands at the temples, the sides swept back cleanly. "
     + REST + " " + FRAME),

    ("VAL-H01-rest", os.path.join(HERE, "valencia_v3", "VAL-H01.png"),
     "Keep this exact woman completely unchanged: identical face, identical bone "
     "structure, identical heavy dark brows and strong nose, identical dark hair, "
     "identical secondhand cardigan over a plain tee. Do not alter her features, her "
     "age or her expression in any way. Change ONLY the lighting and backdrop to "
     "match a neutral studio casting portrait. " + FRAME),
]


def preflight():
    key = os.getenv("FAL_KEY")
    if not key:
        sys.exit("[FAIL] FAL_KEY not set. Check .env.")
    r = httpx.post("https://rest.fal.ai/storage/auth/token?storage_type=fal-cdn-v3",
                   headers={"Authorization": "Key " + key}, timeout=30)
    # The account lock surfaces ONLY as 403 + "balance" - that is the one thing worth
    # blocking on. A 422 here just means this probe endpoint wanted a body; auth and
    # balance were fine, which is all the pre-flight needs to know.
    if r.status_code == 403 and "balance" in r.text.lower():
        sys.exit("[FAIL] fal balance exhausted. Top up at fal.ai/dashboard/billing "
                 "(pay-as-you-go, no subscription). Then re-run this script.")
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
