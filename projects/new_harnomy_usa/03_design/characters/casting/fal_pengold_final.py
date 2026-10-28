#!/usr/bin/env python3
r"""Stage 3.5 - PENGOLD final anchor. Brad picked PEN-T01, 2026-09-03.

CORRECTION: an earlier run of this script targeted T02. Brad corrected the pick to
T01, the leanest of the four text candidates. T01 carries less of the well-fed
softness than T02 or T03, but it is also the coldest, which is consistent with him
rejecting T03 as "too likeable".

Two changes, both to the hair:
  - slicked back, wet-combed and held rather than dry and softly combed
  - a hint of grey

Both are SURFACE changes, so an edit against T02 as reference is the right
method (NH-USA-021: surface survives an edit, structure does not). The body,
which was the hard-won part, is carried by the reference and must not move.

The grey goes in the HAIR ONLY, at the temples. PEN-R02 put grey in the beard
and it read as an older, harder man - the wrong direction entirely. The beard
stays dark.

T03 was rejected as "too likeable", so T01's coolness is the target: hold the
expression exactly where it is and do not warm him.

Two variants on how much grey. Cost: two images, ~$0.30.
"""
import os
import sys
import urllib.request

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "pengold_text", "PEN-T01.png")
OUT = os.path.join(HERE, "pengold_text")

for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env",
            r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

HOLD = ("Keep this exact man completely unchanged: identical face, identical bone "
        "structure, identical soft full cheeks and softened jawline, identical fullness "
        "under the chin and at the neck, identical dark hipster beard with no grey in "
        "it, identical navy suiting and open white collar, identical expression and "
        "identical lighting. Do not slim his face. Do not change his age or his "
        "expression. Change ONLY the hair on his head. ")

FRAME = ("Head-and-shoulders portrait, plain grey backdrop, even neutral daylight, "
         "natural skin tones, photographic realism, 85mm.")

JOBS = [
 ("PEN-F03", HOLD +
  "Slick his hair back tight to the skull, wet-combed and held in place with product, "
  "the comb lines visible, a clean high forehead and nothing falling loose. Put a hint "
  "of grey in it: a light silvering at the temples and just above the ears, the rest "
  "still dark. " + FRAME),
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
                print("   [FAIL] no image: %s" % str(res)[:250], flush=True)
                continue
            dst = os.path.join(OUT, name + ".png")
            urllib.request.urlretrieve(images[0]["url"], dst)
            print("   [OK] %s (%d KB)" % (name, os.path.getsize(dst) // 1024), flush=True)
        except Exception as exc:
            print("   [FAIL] %s: %s" % (name, exc), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
