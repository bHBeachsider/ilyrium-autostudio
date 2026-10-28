#!/usr/bin/env python3
r"""fal_v9_cleanup.py - NH-S901 v9: take the second timber platform out of the square.

Brad, 2026-09-05: remove the pumpkin platform at the foot of the City Hall steps. The v4 harvest dressing built a low
timber dais there, banked with hay bales - a second stage in the same square, which muddies the one structure the
teaser is about. The harvest dressing stays (sheaves at the columns, pumpkins and gourds on the granite steps and at
the column bases); only the timber platform and its hay-bale banks go, leaving open wet granite in front of the steps.

Plates first, then the shots that see the building, each as a SINGLE-reference edit so the camera cannot drift
(NH-USA-043/046). Banner text is re-lettered in pixels afterwards (set_banner_text.py).
usage: fal_v9_cleanup.py JOB [JOB ...]   jobs: plate_first plate_dusk SH007 SH009
"""
import os
import sys
import urllib.request

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
KEYS = os.path.join(PROJ, "04_preproduction", "keyframes", "NH-S901")
OUT = os.path.join(HERE, "_v9")
for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env", r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

# take 2 (NH-USA-041 again): "remove the platform" made the model remove the RALLY STAGE in two of four jobs. The
# target is now identified by position and by what it is NOT, and the rally stage is named as untouchable first.
KEEP_STAGE = ("The long low timber RALLY STAGE standing out in the open square - the wide one with the tall pine "
              "uprights and crossbeam over it - is the subject of this picture and must remain COMPLETELY UNTOUCHED: "
              "every board, its steps, its chairs, its podium, its truss and its garlands stay exactly as they are. "
              "Do not remove it, do not move it, do not shrink it. ")
STRIP2 = (KEEP_STAGE + "A DIFFERENT and much smaller timber platform stands right up against the building, at the "
          "bottom of City Hall's granite entrance steps, banked with straw bales and heaped pumpkins. Remove THAT one "
          "completely - its deck, its front edge, the straw bales and the pumpkins piled on and against it - so that "
          "the wet granite paving runs unbroken up to the bottom step of the building. Keep everything else exactly as "
          "it is: the same camera, the building, its arches and columns, the corn-stalk sheaves tied to the columns, "
          "the garlands, the banner and its lettering, the vehicles, the people, the drizzle and the grey light. A "
          "modest scatter of pumpkins and gourds may remain on the granite steps themselves and at the foot of the "
          "columns, but nothing stands on the paving in front of the steps. Fill what you remove with wet granite "
          "setts matching the surrounding paving, its puddles and its reflections. Photographic realism, matching grain.")

STRIP = ("Edit this exact photograph. In front of the granite steps of City Hall there is a low raw-timber platform "
         "banked with straw bales and heaped pumpkins - a small second stage. REMOVE IT COMPLETELY: the timber deck, "
         "its front edge, the straw bales and the pumpkins piled on and against it, so that the wet granite paving "
         "runs unbroken from the camera right up to the bottom step. Keep everything else exactly as it is - the same "
         "camera, the same building and its arches and columns, the tall corn-stalk sheaves tied to the columns, the "
         "garlands, the banner with its lettering, the long timber rally stage out in the square, the vehicles, the "
         "people, the drizzle and the grey light. A modest scatter of orange and white pumpkins and gourds may remain "
         "on the granite steps themselves and at the foot of the columns, but nothing stands on the paving in front of "
         "the steps. Fill what you remove with wet granite setts that match the surrounding paving, its puddles and "
         "its reflections. Photographic realism, matching grain.")

JOBS = {
 "plate_first": ("21:9", [os.path.join(HERE, "plate_exterior_firstlight_LOCKED.png")], STRIP),
 "plate_dusk":  ("21:9", [os.path.join(HERE, "plate_exterior_dusk_LOCKED.png")], STRIP2 +
                 " At dusk the cleared paving reflects the lit windows and the street lamps. The tall timber truss "
                 "behind the rally stage, its uprights and crossbeam and their garlands, must remain exactly as it is."),
 "SH007": ("16:9", [os.path.join(KEYS, "NH-S901-SH007_key.png")], STRIP2 +
           " The crossbeam on its cables, the two uprights and the workmen in the foreground are untouched."),
 "SH009": ("16:9", [os.path.join(KEYS, "NH-S901-SH009_key.png")], STRIP +
           " The finished stage in the foreground with its steps, chairs, podium, garlanded upright and the pumpkins "
           "and hay bales along ITS front edge are untouched - only the separate platform at the building's steps goes."),
}


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
    jobs = sys.argv[1:] or list(JOBS)
    os.makedirs(OUT, exist_ok=True)
    preflight()
    import fal_client
    cache = {}
    for job in jobs:
        ar, refs, prompt = JOBS[job]
        print("-- %s" % job, flush=True)
        try:
            urls = []
            for rp in refs:
                if rp not in cache:
                    cache[rp] = fal_client.upload_file(rp)
                urls.append(cache[rp])
            res = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={
                "prompt": prompt, "image_urls": urls, "aspect_ratio": ar,
                "resolution": "2K", "output_format": "png", "num_images": 1})
            imgs = res.get("images") or []
            if not imgs:
                print("   [FAIL] no image: %s" % str(res)[:200], flush=True); continue
            dst = os.path.join(OUT, job + ".png")
            urllib.request.urlretrieve(imgs[0]["url"], dst)
            print("   [OK] %s (%d KB)" % (os.path.basename(dst), os.path.getsize(dst) // 1024), flush=True)
        except Exception as exc:
            print("   [FAIL] %s: %s" % (job, exc), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
