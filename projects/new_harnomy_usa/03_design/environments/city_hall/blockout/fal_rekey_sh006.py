#!/usr/bin/env python3
r"""fal_rekey_sh006.py - re-key NH-S901 SH006 (Pengold's POV) against the blockout's clay render (NH-USA-044).

The v3 key put the stage at the foot of the building; every other shot has it ~32 m out. The FIRST reference is the
grey clay render from the blockout's SH006 camera (build-day state: bare uprights, no beam) - it carries the camera,
the framing and where everything sits. The SECOND reference carries materials, light and the life of the square.
Two variants, one generation each (~$0.15 each), written beside the script as _rekey/SH006_A.png / SH006_B.png:
  A  second ref = the v3 SH006 key (same view, right look; only the layout is wrong)
  B  second ref = the LOCKED first-light plate
Pick one, then copy it over 04_preproduction/keyframes/NH-S901/NH-S901-SH006_key.png (the v3 take goes to _v3_takes/).
usage: fal_rekey_sh006.py [A B C]   (C = cleanup edit on B; run after B exists)
"""
import os
import sys
import urllib.request

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
ENV = os.path.join(PROJ, "03_design", "environments", "city_hall")
KEYS = os.path.join(PROJ, "04_preproduction", "keyframes", "NH-S901")
OUT = os.path.join(HERE, "_rekey")

for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env", r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

CLAY = os.path.join(HERE, "clay_SH006_build.png")
V3 = os.path.join(KEYS, "NH-S901-SH006_key.png")
EXT_FIRST = os.path.join(ENV, "plate_exterior_firstlight_LOCKED.png")

LOOK = ("prestige political drama, House of Cards season one color grade, Roger Deakins single-source lighting, "
        "anamorphic cinematography, Arri Alexa, slight 35mm film grain, color palette desaturated twelve percent, "
        "warm tungstens lifted, deep browns and charcoals in shadows, photographic realism, cinematic")
LIFE = ("The square is a normal mid-sized American downtown on a weekday morning in November: cars parked nose to "
        "tail along the kerbs at the sides of the square, a flatbed truck stacked with fresh pine lumber and a white "
        "box van with its rear doors open at the left kerb, a city bus at the far corner, a few pedestrians in winter "
        "coats crossing the granite paving at a distance with their backs to the camera, a dog-walker, a courier on a "
        "bicycle. Nobody is close, nobody faces the camera, nobody looks at the timber structure. ")

LAYOUT = ("The FIRST reference is a plain grey architectural model rendered from the exact camera of this shot. "
          "Reproduce its camera, lens and framing precisely, and put every object exactly where the model puts it, "
          "at exactly the size the model shows: the two giant limestone columns filling the left and right edges "
          "of the frame and rising out of it; their square plinths and the stone balustrade across the bottom; the "
          "wide granite square beyond; and, FAR OUT IN THE SQUARE - a good thirty metres from the building, in the "
          "MIDDLE DISTANCE, occupying only the middle third of the frame's width and sitting just below the frame's "
          "centre line - a long low timber rally stage under construction, running left to right, parallel to the "
          "building. There is NOTHING between the balustrade and that stage but empty granite paving; the stage is "
          "NOT at the foot of the building. Along the stage's near edge (toward the camera) two tall square pine "
          "uprights stand vertical with temporary diagonal props, one near each end, with NO crossbeam - their tops "
          "are bare. The platform is a frame of open pine joists with decking laid across about half of it; stacks of "
          "fresh lumber lie on the paving beside it; six workmen in high-visibility vests move around it, small, seen "
          "from above, no faces. Above the stage, the low brick blocks of the far side of the square with a street "
          "opening on the axis, and a flat winter sky. ")

JOBS = {
 "A": ([CLAY, V3],
       LAYOUT + "Use the SECOND reference for everything about how it looks - the same limestone columns, the same "
       "balustrade, the same faint reflection of the room on the glass, the same flat winter daylight, the same "
       "photographic style - but NOT for where the stage is: the second reference's stage is in the wrong place and "
       "must be ignored for position and size. " + LIFE + LOOK),
 # C (after B): B has the layout right but a dog-walker and a cyclist crossing close below the balustrade; a
 # single-reference removal edit keeps the camera (one reference = no camera vote, NH-USA-043).
 "C": ([os.path.join(OUT, "SH006_B.png")],
       "Edit this photograph. Remove the woman walking the dog and the cyclist in the foreground below the "
       "balustrade, and the two people standing on the paving just beyond the far end of the stage; fill those "
       "areas with the same empty grey granite paving, matching the low raking winter light and frost. Change "
       "nothing else: the columns, balustrade, stage, workmen, vehicles, distant pedestrians, buildings and light "
       "stay exactly as they are."),
 "B": ([CLAY, EXT_FIRST],
       LAYOUT + "Use the SECOND reference only for materials, light and the life of the square - the warm limestone, "
       "the grey granite setts, the low winter sun and frost, the parked cars, the lumber flatbed, the box van, the "
       "pedestrians - never for its camera: this shot is seen from inside the building looking down, not from across "
       "the square. " + LIFE + LOOK),
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
    only = set(sys.argv[1:]) or {"A", "B"}
    os.makedirs(OUT, exist_ok=True)
    preflight()
    import fal_client
    cache = {}
    for name, (refs, prompt) in JOBS.items():
        if name not in only:
            continue
        print("-- SH006 variant %s" % name, flush=True)
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
            dst = os.path.join(OUT, "SH006_%s.png" % name)
            urllib.request.urlretrieve(imgs[0]["url"], dst)
            print("   [OK] %s (%d KB)" % (os.path.basename(dst), os.path.getsize(dst) // 1024), flush=True)
        except Exception as exc:
            print("   [FAIL] %s: %s" % (name, exc), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
