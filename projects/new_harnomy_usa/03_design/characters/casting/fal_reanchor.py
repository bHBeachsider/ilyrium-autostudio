#!/usr/bin/env python3
r"""Stage 3.5 RE-ANCHOR - Summer, Dick, Pengold. Brad's direction, 2026-09-03.

Valencia is untouched and stays LOCKED.

  SUMMER   younger (late thirties / early forties) and at rest, with beatific
           notes in the countenance that PORTEND her elevation to Queen of
           New Harnomy. Beatific is not smug and not a smile: it is serenity
           with light in it - the stillness of someone who believes herself
           chosen. THE_CASTE's guard still holds: certainty, never a wink.
  DICK     softer and more feminine. Slim athletic build of a professional
           tennis player - lean and healthy, NOT gaunt (the failure mode of
           the last set, NH-USA-016). Longer hair, man-bun capable.
  PENGOLD  more youthful. A well-manicured hipster beard, not clean-shaven.
           Soft and squishy - a political consultant who eats out at too many
           high-end restaurants. NOT fat. NOT rough.

Two variants each so there is a real choice: A states the note plainly,
B pushes it further.

Cost: $0.15/image at 2K. Six images = ~$0.90.
"""
import os
import sys
import urllib.request

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "reanchor")

for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env",
            r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

FRAME = ("Head-and-shoulders portrait framed just below the collarbone, hands out of "
         "frame, straight-on to camera, plain unlit grey backdrop, even neutral "
         "daylight-balanced exposure, soft frontal key, shadows open and detailed, "
         "natural skin tones, photographic realism, 85mm, sharp focus on the eyes.")

REST = ("Mouth closed with the lips together, jaw relaxed, eyes steady on the lens, "
        "the expression still and unforced.")

F = os.path.join(HERE, "finals")

JOBS = [
 # ---- SUMMER ------------------------------------------------------------
 ("SUM-R01", os.path.join(F, "SUM-K02-rest.png"),
  "Keep this exact woman: the same face, the same bone structure, the same narrow "
  "face and ash-blonde hair in a low chignon, the same well-cut dark blazer. Make "
  "two changes. FIRST, make her younger - a woman of thirty-eight with smooth firm "
  "skin across the cheeks, jaw, throat and around the eyes, the expensive "
  "maintenance visibly working, luminous and well-rested. SECOND, give the face a "
  "beatific quality: a serene inward calm with light in it, the composed radiance of "
  "someone who quietly believes herself chosen, the head carried level and the eyes "
  "clear and untroubled. Serene and elevated, never pleased with herself. "
  + REST + " " + FRAME),

 ("SUM-R02", os.path.join(F, "SUM-K02-rest.png"),
  "Keep this exact woman: the same face, the same bone structure, the same narrow "
  "face and ash-blonde hair in a low chignon, the same well-cut dark blazer. Make her "
  "distinctly younger - a woman of thirty-six, skin smooth and firm at the cheeks, "
  "jaw and throat, no lines at the eyes, glowing with health and money. Give her the "
  "countenance of a saint in a Renaissance altarpiece rendered as a modern patrician "
  "woman: luminous, tranquil, the chin level, the eyes lit from within and looking "
  "steadily out, a face that seems already elevated above the room. Grave, radiant "
  "and completely still. " + REST + " " + FRAME),

 # ---- DICK --------------------------------------------------------------
 ("DIC-R01", os.path.join(F, "DIC-K02-hair-v2.png"),
  "Keep this exact man's identity: the same eyes, the same nose, the same tan and "
  "clear skin. Make three changes. FIRST, soften the features - a delicate, "
  "fine-boned, almost feminine face with a smooth unlined jaw, full soft lips, long "
  "lashes and gentle brows; pretty rather than rugged. SECOND, give him the build of "
  "a professional tennis player - slim, light and athletic with lean healthy muscle "
  "and smooth full cheeks, never hollow or gaunt. THIRD, make the dirty-blond hair "
  "longer, falling well below the jaw to the collarbone, soft and loose and easily "
  "gathered into a man-bun. A beautiful young man of thirty-two. " + REST + " " + FRAME),

 ("DIC-R02", os.path.join(F, "DIC-K02-hair-v2.png"),
  "Keep this exact man's identity: the same eyes, the same nose, the same tan and "
  "clear skin. Make him markedly softer and more feminine - a delicate androgynous "
  "beauty, fine features, a smooth rounded jaw, full lips, a slender neck, skin "
  "flawless and unlined, the face youthful and full with no hollowing at the cheeks. "
  "Give him the light slim frame of a professional tennis player, athletic and lean "
  "without bulk. His dirty-blond hair is long, past the collarbone, soft and shining "
  "and worn loose, obviously long enough to tie up into a man-bun. A very pretty man "
  "of thirty. " + REST + " " + FRAME),

 # ---- PENGOLD -----------------------------------------------------------
 ("PEN-R01", os.path.join(F, "PEN-K03-rest.png"),
  "Keep this exact man's identity: the same eyes, the same nose, the same dark hair "
  "combed back with care, the same immaculate dark suiting and crisp white shirt. "
  "Make three changes. FIRST, make him younger - a man of forty-one with smooth "
  "skin. SECOND, give him a short, neat, carefully groomed hipster beard, precisely "
  "barbered and expensively maintained, no stubble and no wildness. THIRD, make him "
  "soft rather than hard - a smooth well-fed indoor softness in the cheeks and under "
  "the chin, comfortable and unweathered, the face of a political consultant who eats "
  "out at too many expensive restaurants. Well-fed and pampered but trim, not fat and "
  "not heavy, and never rough or coarse. " + REST + " " + FRAME),

 ("PEN-R02", os.path.join(F, "PEN-K03-rest.png"),
  "Keep this exact man's identity: the same eyes, the same nose, the same dark hair "
  "combed back with care, the same immaculate dark suiting and crisp white shirt. Make "
  "him a youthful, pampered thirty-nine: skin smooth and clear and indoor-pale-warm, "
  "no weathering, no hard lines. Give him a short well-manicured hipster beard, "
  "sculpted by an expensive barber, tidy at the cheek line and neatly trimmed. His "
  "face is soft and slightly plush - a little squish at the cheek and just under the "
  "jaw from a life of tasting menus - but his frame stays trim and his suit fits "
  "cleanly. Soft, groomed and comfortable; not fat, not coarse, not rugged. "
  + REST + " " + FRAME),
]


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
    cache = {}
    for name, src, prompt in JOBS:
        if not os.path.exists(src):
            print("[SKIP] %s - source missing: %s" % (name, src), flush=True)
            continue
        print("-- %s" % name, flush=True)
        try:
            if src not in cache:
                cache[src] = fal_client.upload_file(src)
            res = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={
                "prompt": prompt,
                "image_urls": [cache[src]],
                "aspect_ratio": "3:2",
                "resolution": "2K",
                "output_format": "png",
                "num_images": 1,
            })
            images = res.get("images") or []
            if not images:
                print("   [FAIL] no image: %s" % str(res)[:200], flush=True)
                continue
            dst = os.path.join(OUT, name + ".png")
            urllib.request.urlretrieve(images[0]["url"], dst)
            print("   [OK] %s (%d KB)" % (name, os.path.getsize(dst) // 1024), flush=True)
        except Exception as exc:
            print("   [FAIL] %s: %s" % (name, exc), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
