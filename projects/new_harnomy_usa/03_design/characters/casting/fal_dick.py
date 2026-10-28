#!/usr/bin/env python3
r"""Dick Suede - hair modification on the cast face (DIC-K02), via fal nano-banana-pro.

Renders two frames from the approved caste portrait:
  DIC-K02-hair : dirty blond, loose to the collarbone, man-bun capable  (Acts I-II)
  DIC-K02-bun  : the same hair gathered into the bun                     (Act III)

The man-bun is not a hair note. Summer's initiative is THE MAN BUN COLLECTIVE, so
man-bun-capable hair puts the name of the organisation she is funding onto the body
of the man she is sleeping with, and no character ever remarks on it. See
01_development/bible/characters/dick/bible.md.

WHY nano-banana-pro AND NOT soul_cinematic: FINDINGS NH-USA-009 - soul_cinematic
accepts one reference and does not hold identity; steering a face through it returned
a different person three times out of four. nano_banana_pro held VAL-H01 first try.

Run with the project venv:
    venv\Scripts\python.exe projects\new_harnomy_usa\03_design\characters\casting\fal_dick.py

Cost: $0.15/image at 2K, pay-as-you-go, no subscription. Two images = ~$0.30.
"""
import os
import sys
import urllib.request

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "caste", "DIC-K02.png")
OUT = os.path.join(HERE, "dick_v2")

for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env",
            r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)


def preflight():
    """Fail fast and legibly on an empty balance.

    NH-USA-013: a render pipeline can be wired, tested and committed while the
    account behind it is dry. Never let that surface as a stack trace.
    """
    key = os.getenv("FAL_KEY")
    if not key:
        sys.exit("[FAIL] FAL_KEY not set. Check .env.")
    r = httpx.post("https://rest.fal.ai/storage/auth/token?storage_type=fal-cdn-v3",
                   headers={"Authorization": "Key " + key}, timeout=30)
    if r.status_code == 403 and "balance" in r.text.lower():
        sys.exit("[FAIL] fal balance exhausted. Top up at fal.ai/dashboard/billing "
                 "(pay-as-you-go, no subscription). Then re-run this script.")
    if r.status_code != 200:
        sys.exit("[FAIL] fal auth returned %s: %s" % (r.status_code, r.text[:200]))
    print("[OK] fal balance available")


# Everything that must NOT change. The edit is the hair and nothing else.
HOLD = ("Keep this exact man: same face, same bone structure, same tan and skin, "
        "same gym-built shoulders, same heritage workwear jacket over a plain fitted "
        "tee, same plain grey backdrop, same even neutral lighting. Photographic "
        "realism, 85mm, sharp focus on the eyes, mouth closed with the lips together, "
        "jaw relaxed, eyes steady on the lens, unbothered and certain.")

JOBS = [
    ("DIC-K02-hair",
     "Change ONLY the hair: make it dirty blond and slightly longer, worn loose and "
     "falling to the collarbone, thick enough to be gathered into a man-bun at a "
     "minute's notice - the carefully maintained 'I do not care' cut that takes an "
     "expensive barber to look effortless. " + HOLD),
    ("DIC-K02-bun",
     "Change ONLY the hair: dirty blond, gathered up into a neat man-bun at the crown "
     "with a few loose strands at the temples, the sides swept back cleanly. " + HOLD),
]


def main():
    preflight()
    import fal_client

    if not os.path.exists(SRC):
        sys.exit("[FAIL] source not found: %s" % SRC)
    os.makedirs(OUT, exist_ok=True)

    url = fal_client.upload_file(SRC)
    print("[OK] uploaded reference")

    for name, prompt in JOBS:
        print("-- %s" % name, flush=True)
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
            print("   [FAIL] no image returned: %s" % str(res)[:200])
            continue
        dst = os.path.join(OUT, name + ".png")
        urllib.request.urlretrieve(images[0]["url"], dst)
        print("   [OK] %s (%d KB)" % (dst, os.path.getsize(dst) // 1024))

    print("DONE")


if __name__ == "__main__":
    main()
