#!/usr/bin/env python3
r"""City Hall + Mayor's office plates, aligned. See SET_BIBLE.md for the geometry contract.

Brad's draft panels are 256px thumbnails, so they are used as COMPOSITION references only; the
pixels come from the prompt, which restates the set bible. Every plate fixes the same continuity
errors: American flag or none; no European capital, no Manhattan skyline; the mauve books present;
the office looks DOWN through the colonnade at the square, never at an opposite facade.

Five plates, ~$0.75.
"""
import os
import sys
import urllib.request

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "reference")

for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env",
            r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

LOOK = ("prestige political drama, House of Cards season one color grade, Roger Deakins single-source "
        "lighting, anamorphic cinematography, Arri Alexa, slight 35mm film grain, color palette "
        "desaturated twelve percent, warm tungstens lifted, deep browns and charcoals in shadows, faint "
        "cool blue holding only in the deepest blacks, photographic realism, cinematic, no people, no text")

BUILDING = ("New Harnomy City Hall, an American Beaux-Arts municipal building of about 1910 in pale grey "
            "limestone: a long flat two-storey facade over a rusticated base, and at its centre a projecting "
            "SEMICIRCULAR PORTICO of twelve giant-order columns two storeys tall on a curve, carrying an "
            "entablature with a drum and cupola above, a curved stone veranda with a balustrade running "
            "behind the columns at the upper level and tall French windows opening onto it")

SQUARE = ("a wide municipal square of grey granite setts in front of the building, ringed by low four- and "
          "five-storey American commercial blocks, a church steeple and bare winter trees, a mid-sized "
          "American city, nothing European, no skyline")

DAIS = ("a raw undecorated timber platform about nine metres wide and waist-high, with two tall timber "
        "uprights and a heavy crossbeam, and a short flight of wooden steps, standing on the building's "
        "axis about forty metres out with its back toward the portico")

OFFICE_DRESSING = ("a tungsten desk lamp still switched on, a half-empty coffee cup, a folded newspaper, THREE "
                   "worn dusty-mauve paperbacks stacked on the credenza and ONE pristine mauve paperback "
                   "squared on the desk (the brownish-purple of an aged 1970s university-press paperback, "
                   "never lavender), a single American flag on a floor stand")

JOBS = [
 ("plate_exterior_dusk_v3", "21:9", [os.path.join(HERE, "plate_exterior_firstlight_v1.png"),
                                     os.path.join(HERE, "plate_exterior_dusk_v2.png")],
  "Use the FIRST reference for the building, the square and the exact camera framing - keep every stone of "
  "it, crisp and solid, no transparency, no ghosting, no double exposure anywhere. Use the SECOND reference "
  "only for the time of day and the timber structure. Re-light the first reference as deep blue winter dusk: "
  "the sky a clean dark blue, every upper window and the ground-floor arcade glowing warm tungsten from "
  "inside, the stone cool and dim, frost on the granite setts. Remove the truck. Add in the square, on the "
  "building's axis about forty metres out, a LOW raw timber platform about nine metres wide and waist-high "
  "with a short flight of wooden steps at one end and two short timber uprights carrying a crossbeam that "
  "rises no higher than the tops of the ground-floor arches behind it, the whole structure solid, opaque, "
  "undressed, falling into silhouette against the lit facade. Nobody in frame. " + LOOK),
]


def preflight():
    key = os.getenv("FAL_KEY")
    if not key:
        sys.exit("[FAIL] FAL_KEY not set.")
    r = httpx.post("https://rest.fal.ai/storage/auth/token?storage_type=fal-cdn-v3",
                   headers={"Authorization": "Key " + key}, timeout=30)
    if r.status_code == 403 and "balance" in r.text.lower():
        sys.exit("[FAIL] fal balance exhausted.")
    if r.status_code in (401, 403):
        sys.exit("[FAIL] fal auth rejected (%s)" % r.status_code)
    print("[OK] fal auth OK (probe %s)" % r.status_code, flush=True)


def main():
    preflight()
    import fal_client
    cache = {}
    for name, ar, refs, prompt in JOBS:
        print("-- %s" % name, flush=True)
        try:
            urls = []
            for rp in refs:
                if rp not in cache:
                    cache[rp] = fal_client.upload_file(rp)
                urls.append(cache[rp])
            res = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={
                "prompt": prompt, "image_urls": urls, "aspect_ratio": ar,
                "resolution": "2K", "output_format": "png", "num_images": 1,
            })
            imgs = res.get("images") or []
            if not imgs:
                print("   [FAIL] no image: %s" % str(res)[:200], flush=True); continue
            dst = os.path.join(HERE, name + ".png")
            urllib.request.urlretrieve(imgs[0]["url"], dst)
            print("   [OK] %s (%d KB)" % (name, os.path.getsize(dst) // 1024), flush=True)
        except Exception as exc:
            print("   [FAIL] %s: %s" % (name, exc), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
