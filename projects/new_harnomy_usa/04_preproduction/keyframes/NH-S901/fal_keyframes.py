#!/usr/bin/env python3
r"""NH-S901 'The Scaffold' - eleven keyframes, one per shot spec.

METHOD, AND WHY NOT THE LoRA
----------------------------
Every keyframe is a reference-conditioned edit on fal nano-banana-pro, using the LOCKED
plates from 03_design/environments/city_hall/ as the environment reference, so the
building, the square and the office are provably the same object in every frame -
the same technique that held the facade across the dusk relight.

The one shot with a face (SH005) composes Pengold's locked anchor INTO the locked office
plate as a second reference. For a single still, multi-reference composition holds
identity better than the LoRA does (NH-USA-009); the LoRA's job is video and scale, and
it is named in the spec for the i2v stage.

SH001 is a black frame and is generated locally. SH002, SH010 and SH011 are the exterior
plates themselves - a plate that IS the shot is not regenerated.

Cost: seven generations, ~$1.05.
"""
import os
import sys
import urllib.request

import httpx
from dotenv import load_dotenv
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ENV = os.path.join(PROJ, "03_design", "environments", "city_hall")
ANCHOR = os.path.join(PROJ, "03_design", "characters", "casting", "finals", "PEN-FINAL.png")

for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env",
            r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

LOOK = ("prestige political drama, House of Cards season one color grade, Roger Deakins single-source "
        "lighting, anamorphic cinematography, Arri Alexa, slight 35mm film grain, color palette "
        "desaturated twelve percent, warm tungstens lifted, deep browns and charcoals in shadows, faint "
        "cool blue holding only in the deepest blacks, photographic realism, cinematic, no text")

EXT_FIRST = os.path.join(ENV, "plate_exterior_firstlight_v1.png")
EXT_DUSK = os.path.join(ENV, "plate_exterior_dusk_v3.png")
OFFICE = os.path.join(ENV, "plate_office_A_LOCKED.png")
POV = os.path.join(ENV, "plate_pov_square_v1.png")

COPY = {  # shot -> plate that IS the keyframe
    "NH-S901-SH002": EXT_FIRST,
    "NH-S901-SH010": EXT_DUSK,
}

JOBS = [
 # NH-USA-025 fix: reference the EMPTY-square POV and ADD the partial structure - never reference a
 # plate that already contains the crossbeam and try to subtract it (the reference outvotes the prompt).
 ("NH-S901-SH006", "16:9", [POV, EXT_FIRST],
  "Use the FIRST reference for the camera and the room edge: the same point of view from inside the "
  "Mayor's office looking down through the French window, the same two giant limestone columns close on "
  "either side rising out of frame, the same stone balustrade, the same faint reflection on the glass. Use "
  "the SECOND reference only for the far side of the square: low brick blocks, the steeple, bare trees, flat "
  "winter light. In the square below, centred between the columns and seen from above, build ONLY THIS: two "
  "tall fresh pine timber uprights standing vertical and braced with temporary diagonal props, WITH NO "
  "CROSSBEAM ON TOP OF THEM - the tops of the two posts are bare and separate against the paving - and in "
  "front of them a low rectangular timber platform frame of open joists with no decking laid yet, stacks of "
  "fresh lumber beside it, and four workmen in high-visibility vests moving around it, small, seen from "
  "above, no faces. " + LOOK),
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
    # SH001 black frame

    cache = {}
    for sid, ar, refs, prompt in JOBS:
        print("-- %s" % sid, flush=True)
        try:
            urls = []
            for rp in refs:
                if rp not in cache:
                    cache[rp] = fal_client.upload_file(rp)
                urls.append(cache[rp])
            if urls:
                res = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={
                    "prompt": prompt, "image_urls": urls, "aspect_ratio": ar,
                    "resolution": "2K", "output_format": "png", "num_images": 1})
            else:
                res = fal_client.subscribe("fal-ai/nano-banana-pro", arguments={
                    "prompt": prompt, "aspect_ratio": ar,
                    "resolution": "2K", "output_format": "png", "num_images": 1})
            imgs = res.get("images") or []
            if not imgs:
                print("   [FAIL] no image: %s" % str(res)[:200], flush=True); continue
            dst = os.path.join(HERE, sid + "_key.png")
            urllib.request.urlretrieve(imgs[0]["url"], dst)
            print("   [OK] %s (%d KB)" % (os.path.basename(dst), os.path.getsize(dst) // 1024), flush=True)
        except Exception as exc:
            print("   [FAIL] %s: %s" % (sid, exc), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
