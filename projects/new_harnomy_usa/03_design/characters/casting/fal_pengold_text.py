#!/usr/bin/env python3
r"""Stage 3.5 - PENGOLD text-generated candidates, guided by PEN-K03.

WHY TEXT AND NOT AN EDIT (NH-USA-021)
-------------------------------------
Two edit passes failed to add softness to Pengold's face. A reference latent
pins facial geometry, and body fat IS geometry, so "keep this exact man" and
"make his face fuller" are contradictory and the reference wins every time.

The rule that came out of it: classify the change before choosing the method.
SURFACE changes (light, colour, hair, beard, wardrobe, skin age) survive an
edit. STRUCTURAL changes (bone width, body fat, build) must be generated from
text and re-cast.

So this generates from text with NO reference image. To stay near the man Brad
approved, PEN-K03's actual features are described in detail - dark hair combed
back, the strong brow, the particular set of the eyes, the clean heavy Roman
nose, the immaculate suiting - and the soft well-fed body is built in from the
start rather than bolted on afterwards.

Four candidates varying only in how far the softness is pushed, so the choice
Brad makes is about degree and nothing else.

Cost: $0.15/image at 2K. Four images = ~$0.60.
"""
import os
import sys
import urllib.request

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "pengold_text")

for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env",
            r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

# PEN-K03's face, described so a text generation lands in the same family.
IDENTITY = (
    "A white man of forty-one with a broad squarish head, dark brown hair combed "
    "straight back from a high forehead and kept with obvious care, a strong heavy "
    "brow ridge over deep-set dark eyes that sit close together, a large straight "
    "Roman nose, and a wide mouth. A short, neat, well-manicured hipster beard, "
    "precisely barbered, tidy at the cheek line and along the neck, expensively "
    "maintained, dark with no grey. He wears immaculate dark navy suiting in fine "
    "wool over a crisp white shirt open at the collar, every detail correct."
)

# The one axis: how much tissue. Everything else is held constant.
SOFTNESS = [
    ("PEN-T01",
     "His face is smooth and comfortable: the lower cheeks lightly full and rounded, "
     "the jaw angle just beginning to soften under a little padding, the neck sitting "
     "easily against the shirt collar. Well-fed and unweathered, with no muscle "
     "definition in the face."),
    ("PEN-T02",
     "His face carries a clear well-fed softness: full rounded lower cheeks with a "
     "comfortable padding over them, the jaw angle softened and partly hidden beneath "
     "that fullness so the jawline reads as a gentle curve rather than an edge, a small "
     "soft fullness under the chin with his head level, and a fuller neck resting "
     "against the shirt collar."),
    ("PEN-T03",
     "His face is distinctly plush: the cheeks full and rounded and slightly heavy, "
     "pushing up a little beneath the eyes, the jawline entirely absorbed into a "
     "smooth soft curve, a clear soft fullness beneath the chin and a thick "
     "comfortable neck filling the shirt collar. Rosy, well-fed, pampered colouring."),
    ("PEN-T04",
     "His face carries a clear well-fed softness - full rounded lower cheeks, the "
     "jawline softened into a gentle curve, a small fullness under the chin - and his "
     "colouring is pink and warm and indoor, the skin smooth and slightly shiny with "
     "good living. He looks like he has just come from a long lunch."),
]

BODY = ("His shoulders and frame stay trim and upright and the suit fits him cleanly - "
        "the softness lives in his face and neck, not his build. He is comfortable and "
        "pampered, never large, never coarse, never weathered.")

CASTE = ("His expression is faintly amused and completely unbothered, the face of a man "
         "who has never been seriously contradicted. Certain, never smug, and never "
         "playing to the camera. Mouth closed with the lips together, jaw relaxed, eyes "
         "steady on the lens, the expression still.")

FRAME = ("Head-and-shoulders portrait framed just below the collarbone, hands out of "
         "frame, straight-on to camera, plain unlit grey backdrop, even neutral "
         "daylight-balanced exposure, soft frontal key, shadows open and detailed, "
         "natural skin tones, sharp focus on the eyes, photographic realism, "
         "documentary portrait, 85mm lens.")


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
    os.makedirs(OUT, exist_ok=True)
    for name, soft in SOFTNESS:
        prompt = " ".join([IDENTITY, soft, BODY, CASTE, FRAME])
        print("-- %s" % name, flush=True)
        try:
            res = fal_client.subscribe("fal-ai/nano-banana-pro", arguments={
                "prompt": prompt,
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
