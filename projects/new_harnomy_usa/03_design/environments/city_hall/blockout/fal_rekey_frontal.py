#!/usr/bin/env python3
r"""fal_rekey_frontal.py - NH-S901 v8: re-key SH003 and SH009 from the blockout's FRONTAL cameras (NH-USA-047).

Brad on v8: SH003 and SH009 read as "not parallel" - the stage was parallel but the cameras were oblique. Rule now:
every exterior camera looks square at the facade, so the stage is a horizontal line in every frame. The FIRST
reference is the clay render from the new camera (carries camera + layout; SH003 in build state, SH009 finished); the
SECOND is the LOCKED first-light plate (v8: drizzling overcast, TWEEEDS' banner) for materials, weather and dressing.
The banner text is re-lettered in pixels afterwards (set_banner_text.py). Outputs: _rekey/SH003.png, _rekey/SH009.png.
usage: fal_rekey_frontal.py [SH003 SH009]
"""
import os
import sys
import urllib.request

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
ENV = os.path.join(PROJ, "03_design", "environments", "city_hall")
OUT = os.path.join(HERE, "_rekey")
for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env", r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

PLATE = os.path.join(ENV, "plate_exterior_firstlight_LOCKED.png")
LOOK = ("prestige political drama, House of Cards season one color grade, anamorphic cinematography, Arri Alexa, slight "
        "35mm film grain, color palette desaturated twelve percent, warm tungstens lifted, deep browns and charcoals in "
        "shadows, photographic realism, cinematic")
GLOOM = ("Weather and light exactly as in the SECOND image: a heavy flat sheet-cake grey overcast, no sun, no cast shadows, "
         "a light drizzle falling, the granite setts wet and dully reflective with shallow puddles, timber darkened where "
         "wet, street lamps and the building's windows glowing warm and doubled in the wet. ")
LAYOUT = ("The FIRST image is a plain grey architectural model rendered from the exact camera of this shot. Reproduce its "
          "camera, lens and framing precisely and put every object exactly where the model puts it at exactly the size "
          "the model shows. The camera looks STRAIGHT at the building, square to its facade, so the long timber stage "
          "runs perfectly HORIZONTAL across the frame, parallel to the facade and to the bottom edge of the picture, "
          "both ends at the same height. ")
DRESS = ("Use the SECOND image for what everything is made of and how it is dressed: the same limestone City Hall with "
         "its semicircular colonnade, drum and cupola, the mauve banner hanging between the columns with its pale "
         "lettering, corn-stalk sheaves tied to the columns and lampposts, pumpkins and gourds at the column bases, "
         "garlands on the balustrade, the parked cars along the kerbs, the lumber flatbed and white box van, a bus at "
         "the far corner, a few distant pedestrians under umbrellas with their backs to us; nobody faces the camera. ")

JOBS = {
 "SH003": ([os.path.join(HERE, "clay_SH003_build.png"), PLATE],
   LAYOUT + "Low angle from the wet paving in FRONT of the stage, looking across the near edge of the platform toward "
   "City Hall. The platform is under construction: a frame of open raw-pine joists with NO decking yet, its long near "
   "edge running horizontally across the lower third of the frame. On its far edge, toward the building, stands a tall "
   "square pine upright just to the right of centre; two workmen in wet high-visibility vests and knit caps, seen "
   "from behind and in profile, are steadying it upright hand over hand while a third holds a temporary diagonal "
   "prop; a second tall upright already stands at the far left end. No crossbeam. Their breath steams in the cold. "
   "Behind and above them the full colonnade and the banner. " + GLOOM + DRESS + LOOK),
 "SH009": ([os.path.join(HERE, "clay_SH009.png"), PLATE],
   LAYOUT + "Head-height medium shot from the wet paving in front of the LEFT end of the finished stage, looking "
   "straight at City Hall. The stage's long near edge runs horizontally across the frame; its left end with a short "
   "flight of four raw-pine steps is at frame centre-right; a row of folding chairs and, further right, the podium "
   "stand on the wet decking; the tall square pine upright at the stage's left end rises at the frame's right of "
   "centre with the solid crossbeam leaving frame to the right, both wrapped in garlands of autumn leaves; pumpkins, "
   "gourds and hay bales along the stage front and beside the steps. A single workman in a wet high-visibility "
   "vest, seen in profile, puts his weight on the first tread of the steps to test it, one hand on the platform "
   "edge, face turned to the steps. Behind, the colonnade and the banner, the lumber flatbed and box van at the "
   "left kerb. " + GLOOM + DRESS + LOOK),
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
    only = set(sys.argv[1:]) or set(JOBS)
    os.makedirs(OUT, exist_ok=True)
    preflight()
    import fal_client
    cache = {}
    for name, (refs, prompt) in JOBS.items():
        if name not in only:
            continue
        print("-- %s" % name, flush=True)
        try:
            urls = []
            for rp in refs:
                if rp not in cache:
                    cache[rp] = fal_client.upload_file(rp)
                urls.append(cache[rp])
            res = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={
                "prompt": prompt, "image_urls": urls, "aspect_ratio": "16:9",
                "resolution": "2K", "output_format": "png", "num_images": 1})
            imgs = res.get("images") or []
            if not imgs:
                print("   [FAIL] no image: %s" % str(res)[:200], flush=True); continue
            dst = os.path.join(OUT, "%s.png" % name)
            urllib.request.urlretrieve(imgs[0]["url"], dst)
            print("   [OK] %s (%d KB)" % (os.path.basename(dst), os.path.getsize(dst) // 1024), flush=True)
        except Exception as exc:
            print("   [FAIL] %s: %s" % (name, exc), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
