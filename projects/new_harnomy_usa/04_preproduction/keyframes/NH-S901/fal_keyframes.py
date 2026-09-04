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
 ("NH-S901-SH003", "16:9", [EXT_FIRST],
  "Use the reference for the building and the square, which must be this exact building. New camera: a LOW "
  "angle from the granite setts looking UP at two heavy fresh pine timber uprights being raised toward vertical "
  "against a flat white winter sky, two workmen in high-visibility vests and heavy gloves guiding them, seen "
  "from behind and below so no faces are visible, breath steaming in the cold, the semicircular colonnade and "
  "cupola of the city hall rising behind. Morning. " + LOOK + ", no faces, no people looking at camera"),

 ("NH-S901-SH004", "16:9", [],
  "Extreme close-up insert: a chop saw blade cutting through a length of fresh pale pine timber, fine sawdust "
  "hanging in the air and catching a low winter sun from the left, heavy gloved hands steadying the wood, "
  "shallow depth of field, sharp focus on the blade and the fresh cut, an out-of-focus grey granite square and "
  "pale stone building far behind. " + LOOK + ", no faces"),

 ("NH-S901-SH005", "16:9", [OFFICE, ANCHOR],
  "Use the FIRST reference as the room: this exact office, unchanged - the curved panelled walls, the heavy "
  "damask curtains, the unlit brass chandelier, the tall French windows with the giant limestone columns just "
  "outside, the desk with its brass lamp lit, the coffee cup, the folded newspaper, the mauve book. Use the "
  "SECOND reference for the man: pengold_heavens_nh, this exact man, same face, same slicked-back dark hair "
  "with grey at the temples, same short neat dark beard, same navy suit and open white collar. Place him "
  "standing at the centre French window with his back three-quarters to the camera, looking down and out "
  "through the glass into the square, one hand in his trouser pocket, completely still, backlit by the flat "
  "winter daylight so his face is half in shadow and half lit by the window. Medium shot from inside the room, "
  "the desk lamp glowing in the foreground. " + LOOK),

 ("NH-S901-SH006", "16:9", [POV],
  "Keep this exact view: the same two giant columns close on either side, the same balustrade, the same square, "
  "steeple and rooflines beyond, the same flat winter light and the faint reflection of the office on the glass. "
  "Change only the timber structure below: it is now HALF-BUILT - the two uprights standing but no crossbeam "
  "yet, the platform frame laid but not yet decked, fresh lumber stacked beside it, and four workmen in "
  "high-visibility vests moving around its base, small and seen from above. " + LOOK + ", no faces"),

 ("NH-S901-SH007", "16:9", [EXT_FIRST],
  "Use the reference for the building and the square, which must be this exact building. New camera: a MEDIUM "
  "shot at ground level in the square at midday under flat overcast winter light, a heavy horizontal timber "
  "crossbeam being lowered by rope into its seat on top of two tall vertical timber uprights, two workmen in "
  "high-visibility vests reaching up to guide it with gloved hands, seen from behind so no faces are visible, "
  "the raw undecked platform frame at their feet, the semicircular colonnade of the city hall behind. The "
  "crossbeam is the centre of the frame. " + LOOK + ", no faces"),

 ("NH-S901-SH008", "16:9", [],
  "Close insert at platform height: worn leather work boots standing on freshly laid pale pine decking, a "
  "gloved hand sweeping fine sawdust off the square edge of the new boards, low late-afternoon winter sun "
  "raking across the wood grain from the right, the grey granite setts of a square out of focus below. "
  + LOOK + ", no faces"),

 ("NH-S901-SH009", "16:9", [EXT_FIRST],
  "Use the reference for the building and the square, which must be this exact building. New camera: a MEDIUM "
  "shot at ground level in late winter afternoon with long shadows, a short flight of freshly built pale pine "
  "wooden steps set against the side of a finished raw timber platform, a single workman in a high-visibility "
  "vest seen from behind putting his weight on the bottom tread to test it, the two uprights and crossbeam "
  "above, the city hall colonnade behind. " + LOOK + ", no faces"),

 ("NH-S901-SH011", "21:9", [EXT_DUSK],
  "Keep this exact image completely unchanged in every detail - the same building, windows, square and timber "
  "platform, identical framing. Change only the light: it is now several minutes later, the sky a deeper and "
  "darker blue, the last daylight gone, the timber structure fallen fully into silhouette, the lit windows a "
  "little brighter by contrast. " + LOOK),
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
    Image.new("RGB", (1920, 1080), (0, 0, 0)).save(os.path.join(HERE, "NH-S901-SH001_key.png"))
    print("[OK] NH-S901-SH001_key.png (black, local)", flush=True)
    # plates that are the shot
    for sid, src in COPY.items():
        Image.open(src).convert("RGB").save(os.path.join(HERE, sid + "_key.png"))
        print("[OK] %s_key.png (copied from %s)" % (sid, os.path.basename(src)), flush=True)

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
