#!/usr/bin/env python3
r"""edit_keyframe.py - the paid image-edit path (fal nano-banana-pro/edit), with the incident rules baked in as presets.

This folds three one-off scripts from the NH-S901 record into one tool so their lessons stop being re-learned:
  fal_weather.py       -> preset "weather"   : change light/weather of ONE keyframe and nothing else (NH-USA-043: single
                                                reference, the camera cannot be stolen)
  fal_v9_cleanup.py    -> preset "remove"    : delete a named thing; the KEEPER is named first and the target is
                                                described by contrast (NH-USA-048: "remove the platform" took the stage)
  fal_rekey_frontal.py -> preset "rekey"     : re-key from a clay/pass render FIRST, plate SECOND (NH-USA-043/047)
Every preset states invariants positively with counts (NH-USA-051) and never as negations; banner lettering is never
asked of the model (NH-USA-033/042) - re-letter in pixels afterwards with set_banner_text.py.

Cost goes through cost_preflight (budget.yaml) before any call; provenance JSON is written beside every output.

usage: edit_keyframe.py weather KEY.png --out OUT.png [--extra "..."]
       edit_keyframe.py remove  KEY.png --out OUT.png --target "the low timber platform at the foot of the steps"
                                --keeper "the long rally stage out in the square" [--fill "wet granite setts"]
       edit_keyframe.py rekey   CLAY.png --plate PLATE.png --out OUT.png --scene "..." [--state finished]
       common: [--ar 16:9] [--dry-run]
"""
import argparse
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(PKG))

LOOK = ("prestige political drama, House of Cards season one color grade, anamorphic cinematography, Arri Alexa, slight "
        "35mm film grain, color palette desaturated twelve percent, warm tungstens lifted, deep browns and charcoals in "
        "shadows, photographic realism, cinematic")
GLOOM = ("a heavy flat overcast, a featureless sheet-cake grey sky, no sun anywhere, no cast shadows; a light drizzle is "
         "falling - fine rain just visible against the dark stone, the granite paving wet and dully reflective with "
         "shallow puddles mirroring the grey sky, the timber darkened where it is wet, the banner fabric damp and hanging "
         "heavier, drops on the pumpkins. Soft, even, cold, bluish-grey daylight; windows of the building glow faintly "
         "warm by contrast.")
KEEP_TEXT = " Keep the banner's existing text exactly as it is; do not redraw or reword it."
STAGE_RULE = (" The rally stage keeps exactly two tall square pine uprights, one at each END of the stage, and exactly "
              "one row of folding chairs on the decking.")


def preset_weather(a):
    return ([a.image], "Change the weather of this exact photograph and NOTHING else - same camera, same framing, same "
            "building, same people in the same places, same vehicles, same timber, same decorations, same banner in the "
            "same place with the same lettering. The new weather: " + GLOOM + STAGE_RULE + KEEP_TEXT +
            (" " + a.extra if a.extra else "") + " Photographic realism, matching grain.")


def preset_remove(a):
    if not (a.target and a.keeper):
        sys.exit("[FAIL] remove needs --target and --keeper (name what STAYS first - NH-USA-048)")
    return ([a.image], "Edit this exact photograph. KEEP %s exactly as it is, in exactly its place. Separately from it "
            "there is %s. REMOVE that completely, and fill what you remove with %s matching the surroundings, puddles and "
            "reflections included. Keep everything else exactly as it is - the same camera, the same building, the same "
            "people, vehicles, decorations, weather and the banner with its lettering.%s%s Photographic realism, matching "
            "grain." % (a.keeper, a.target, a.fill, STAGE_RULE, KEEP_TEXT))


def preset_rekey(a):
    if not (a.plate and a.scene):
        sys.exit("[FAIL] rekey needs --plate and --scene")
    layout = ("The FIRST image is a plain grey architectural model rendered from the exact camera of this shot. Reproduce "
              "its camera, lens and framing precisely and put every object exactly where the model puts it at exactly the "
              "size the model shows. The camera looks straight at the building, square to its facade, so the long timber "
              "stage runs perfectly horizontal across the frame, parallel to the facade, both ends at the same height. ")
    dress = ("Use the SECOND image for what everything is made of and how it is dressed and for the weather and light. ")
    return ([a.image, a.plate], layout + a.scene + " " + STAGE_RULE + " Weather and light exactly as in the SECOND image: "
            + GLOOM + " " + dress + LOOK)


PRESETS = {"weather": preset_weather, "remove": preset_remove, "rekey": preset_rekey}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("preset", choices=sorted(PRESETS))
    ap.add_argument("image")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ar", default="16:9")
    ap.add_argument("--extra", default="")
    ap.add_argument("--target"); ap.add_argument("--keeper"); ap.add_argument("--fill", default="wet granite setts")
    ap.add_argument("--plate"); ap.add_argument("--scene"); ap.add_argument("--state", default="finished")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    refs, prompt = PRESETS[a.preset](a)
    if a.dry_run:
        print("refs:", refs); print(prompt); return
    from backlot import cost_preflight
    cost = cost_preflight.preflight("nano-banana-pro/edit", images=1)
    from dotenv import load_dotenv
    for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env", os.path.expanduser("~/.ilyrium.env")):
        load_dotenv(env, override=False)
    import fal_client
    urls = [fal_client.upload_file(r) for r in refs]
    t0 = time.time()
    res = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={
        "prompt": prompt, "image_urls": urls, "aspect_ratio": a.ar, "resolution": "2K",
        "output_format": "png", "num_images": 1})
    imgs = res.get("images") or []
    if not imgs:
        sys.exit("[FAIL] no image: %s" % str(res)[:300])
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    urllib.request.urlretrieve(imgs[0]["url"], a.out)
    cost_preflight.book("nano-banana-pro/edit", cost, note="edit_keyframe %s %s" % (a.preset, os.path.basename(a.image)))
    json.dump(dict(preset=a.preset, refs=refs, prompt=prompt, model="fal-ai/nano-banana-pro/edit", ar=a.ar,
                   seconds=round(time.time() - t0, 1)), open(a.out[:-4] + ".json", "w"), indent=1)
    print("[OK] %s -> %s" % (a.preset, a.out))


if __name__ == "__main__":
    main()
