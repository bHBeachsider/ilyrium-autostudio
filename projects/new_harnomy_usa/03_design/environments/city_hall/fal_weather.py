#!/usr/bin/env python3
r"""fal_weather.py - NH-S901 v8: the build day turns gloomy. Brad, 2026-09-05: "The weather should be gloomier. Light
drizzle, sheetcake gray skies." Also: the build must appear IN ORDER (SH006's POV re-opens the joists that the v7 key had
decked), and the banner is re-worded to the TWEEEDS party's Ersatzgiving gathering (lettered in pixels afterwards, never
by the model - NH-USA-033/042).

Every job is a SINGLE-reference edit on the keyframe itself, so the camera cannot be stolen by a second reference
(NH-USA-043); the weather is described in words and the two plates set the tone the words describe. Outputs land in
_weather/ and are installed by hand after review; then set_banner_text.py re-letters every banner.
usage: fal_weather.py JOB [JOB ...]   jobs: plate_first plate_dusk SH003 SH004 SH006 SH007 SH008 SH009 SH012 SH012_letter
"""
import os
import sys
import urllib.request

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
KEYS = os.path.join(PROJ, "04_preproduction", "keyframes", "NH-S901")
OUT = os.path.join(HERE, "_weather")
for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env", r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

GLOOM = ("Change the weather of this exact photograph and NOTHING else - same camera, same framing, same building, same "
         "people in the same places, same vehicles, same timber, same decorations, same banner in the same place with the "
         "same lettering. The new weather: a heavy flat overcast, a featureless sheet-cake grey sky, no sun anywhere, no "
         "cast shadows, no frost; a light drizzle is falling - fine rain just visible against the dark stone, the granite "
         "paving wet and dully reflective with shallow puddles mirroring the grey sky, the timber darkened where it is "
         "wet, the banner fabric damp and hanging heavier, drops on the pumpkins. Soft, even, cold, bluish-grey daylight; "
         "windows of the building glow faintly warm by contrast. Photographic realism, matching grain.")
KEEP_TEXT = " Keep the banner's existing text exactly as it is; do not redraw or reword it."
KEEP_TRUSS = (" CRITICAL: the tall raw-timber truss behind the stage - the two square pine uprights at the ends of the stage "
              "and the solid crossbeam across their tops, with their garlands - must remain EXACTLY as it is.")
PLATE_FIRST = os.path.join(HERE, "plate_exterior_firstlight_LOCKED.png")
PLATE_DUSK = os.path.join(HERE, "plate_exterior_dusk_LOCKED.png")
K = lambda s: os.path.join(KEYS, "NH-S901-%s_key.png" % s)

JOBS = {
 "plate_first": ("21:9", [PLATE_FIRST], GLOOM + " It is early morning; the street lamps are still on, haloed in the drizzle;"
                 " a couple of cars on the far street have their headlights on, reflected in the wet setts." + KEEP_TEXT),
 "plate_dusk":  ("21:9", [PLATE_DUSK], GLOOM.replace("cold, bluish-grey daylight", "cold, bluish-grey failing daylight at dusk")
                 + " Dusk under rain: the last grey light going, every window and street lamp lit and doubled in the wet "
                 "paving, the empty stage and its chairs dark and glistening." + KEEP_TRUSS + KEEP_TEXT),
 "SH003": ("16:9", [K("SH003")], GLOOM + " The workmen's high-visibility vests are wet and bright against the grey; their "
           "breath still steams. The banner behind them hangs damp." + KEEP_TEXT),
 "SH004": ("16:9", [K("SH004")], "Change the light and weather of this exact close-up and nothing else - same saw, same "
           "hands, same timber, same framing. Remove the sunlight: flat, even, cold grey overcast light from a drizzling "
           "sky, no sun sparkle in the sawdust, the sawdust damp and clumping on the wet pine, fine rain drops on the "
           "saw's steel and on the timber, water beading on the gloves. Photographic realism, matching grain."),
 "SH006": ("16:9", [K("SH006")], GLOOM + " Also change the state of the platform so the build is EARLIER: the decking boards "
           "are laid across only the LEFT half of the platform; the RIGHT half is still a frame of open pine joists with "
           "the wet paving visible between them; a workman kneels at the boundary fixing a board; the two tall bare "
           "uprights stay exactly where they are with no crossbeam. Nothing else about the platform's position, size or "
           "angle changes - it stays exactly parallel to the balustrade. The far street beyond the square has a few "
           "cars moving slowly with headlights on, reflected in the wet road."),
 "SH007": ("16:9", [K("SH007")], GLOOM + " The pine crossbeam on its cables and the two uprights are dark with rain; the "
           "decking is wet and reflects the grey sky." + KEEP_TEXT),
 "SH008": ("16:9", [K("SH008")], "Change the light and weather of this exact close-up and nothing else - same boots, same "
           "boards, same hand brush, same framing. Remove the raking sunlight: flat cold grey overcast light, the new pine "
           "decking wet and darkened with rain, fine drizzle drops beading on the boards, the swept sawdust damp and "
           "clumping, the boots' leather wet. Photographic realism, matching grain."),
 "SH009": ("16:9", [K("SH009")], GLOOM + " The folding chairs on the stage are wet and beaded with rain; the steps the "
           "workman tests are dark with wet." + KEEP_TRUSS + KEEP_TEXT),
 "SH012": ("16:9", [K("SH012")], GLOOM + " The banner fabric is soaked dark along its bottom edge and a few drops run off "
           "it; the corn sheaves are wet and drooping." + KEEP_TEXT),
 # lettered by the model from the re-lettered plate at insert scale, where it copies letterforms (NH-USA-040)
 "SH012_letter": ("16:9", [os.path.join(OUT, "SH012.png"), PLATE_FIRST],
           "Use the FIRST image for everything: camera, columns, corn sheaves, pumpkins, garlands, wet fabric, grey light. "
           "Change ONLY the lettering on the mauve banner so that it reads, in the same pale condensed capitals, two "
           "centred lines - line one, larger: WELCOME TO TWEEEDS' ERSATZGIVING GATHERING!  line two, slightly smaller: "
           "NEW HARNOMY'S CELEBRATION OF CONTRITION, ATONEMENT AND REPENTANCE  - exactly as the banner in the SECOND image "
           "is lettered; copy that spelling letter for letter, including the invented words TWEEEDS (three E's), HARNOMY "
           "and ERSATZGIVING. Nothing else changes. Photographic realism."),
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
    jobs = sys.argv[1:] or ["plate_first", "plate_dusk"]
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
