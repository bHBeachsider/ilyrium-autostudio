#!/usr/bin/env python3
r"""Stage 3.10 - verify each LoRA reproduces its anchor face.

A LoRA that only works on the shots it was trained on is worthless. Each is
tested on TWO prompts that are deliberately NOT in the training set - a scene,
not a portrait - to check the face generalises rather than being memorised.

Trigger phrases are included in the prompt but the character is ALSO described
in full. Flux trigger tokens have twice failed to bind in this studio's library
(see broderick_char and broderick_flux_v2 in ilyrium-shots/lora_library.json),
so a test that leaned on the token alone would be testing the wrong thing.

Cost: fal flux-lora inference, 8 images, well under $1.
"""
import json
import os
import sys
import urllib.request

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_verify")

for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env",
            r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

LOOK = ("photographic realism, natural skin texture, cinematic lighting, 35mm, "
        "sharp focus on the eyes")

TESTS = [
 ("valencia", "valencia_strong_nh",
  ["valencia_strong_nh, a woman of twenty-eight of unplaceable ethnicity with heavy dark brows, a strong "
   "nose and dark hair worn loose, in a thrifted cardigan, standing at a bus stop in the rain at dusk, "
   "full body, wide shot. " + LOOK,
   "valencia_strong_nh, a woman of twenty-eight of unplaceable ethnicity with heavy dark brows and a strong "
   "nose, seen in profile against a bright window, backlit, three-quarter view. " + LOOK]),
 ("summer", "summer_winters_nh",
  ["summer_winters_nh, a woman of thirty-eight with ash-blonde hair in a low chignon, a narrow patrician "
   "face, in a dark blazer, seated at a long table in a boardroom, medium wide shot. " + LOOK,
   "summer_winters_nh, a woman of thirty-eight with ash-blonde hair in a low chignon, laughing at a party, "
   "warm low light, three-quarter view. " + LOOK]),
 ("pengold", "pengold_heavens_nh",
  ["pengold_heavens_nh, a man of forty-one with dark hair slicked back and a short neat dark beard, in a "
   "navy suit, walking down a corridor, full body, wide shot. " + LOOK,
   "pengold_heavens_nh, a man of forty-one with dark hair slicked back and a short neat dark beard, seen "
   "from a low angle against a night sky, three-quarter view. " + LOOK]),
 ("dick", "dick_suede_nh",
  ["dick_suede_nh, a soft delicately handsome man of thirty-one with long dirty-blond hair past the jaw and "
   "a slim athletic build, in a workwear jacket, standing on a beach at sunset, full body, wide shot. " + LOOK,
   "dick_suede_nh, a soft delicately handsome man of thirty-one with long dirty-blond hair gathered into a "
   "man-bun, in a plain tee, seen in profile in hard daylight. " + LOOK]),
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
    os.makedirs(OUT, exist_ok=True)

    for character, trigger, prompts in TESTS:
        path = os.path.join(HERE, "%s.safetensors" % trigger)
        if not os.path.exists(path):
            print("[SKIP] %s - no safetensors yet" % character, flush=True)
            continue
        print("== %s" % character, flush=True)
        try:
            lora_url = fal_client.upload_file(path)
        except Exception as exc:
            print("   [FAIL] upload %s: %s" % (character, exc), flush=True)
            continue
        for k, prompt in enumerate(prompts):
            try:
                res = fal_client.subscribe("fal-ai/flux-lora", arguments={
                    "prompt": prompt,
                    "loras": [{"path": lora_url, "scale": 1.0}],
                    "image_size": "landscape_4_3",
                    "num_inference_steps": 28,
                    "guidance_scale": 3.5,
                    "num_images": 1,
                    "output_format": "png",
                    "enable_safety_checker": False,
                })
                imgs = res.get("images") or []
                if not imgs:
                    print("   [FAIL] %d no image: %s" % (k, str(res)[:200]), flush=True)
                    continue
                dst = os.path.join(OUT, "%s_test%d.png" % (character, k))
                urllib.request.urlretrieve(imgs[0]["url"], dst)
                print("   [OK] test%d -> %s" % (k, os.path.basename(dst)), flush=True)
            except Exception as exc:
                print("   [FAIL] %s test%d: %s" % (character, k, exc), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
