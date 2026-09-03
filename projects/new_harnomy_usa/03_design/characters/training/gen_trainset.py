#!/usr/bin/env python3
"""Stage 3.8 - LoRA training-set generation, ON THE BOX via ComfyUI + FLUX.2-Klein.

WHY ON THE BOX AND NOT fal
--------------------------
NH-USA-014: every API edit re-draws the face a little. Eighteen independent edits
per character is eighteen slightly different faces, and a LoRA trained on that
averages them into a person who does not exist. Here the anchor is carried as a
ReferenceLatent on every generation and the seed is pinned per image, so a drifted
frame is reproducible and re-rollable instead of a one-off spend.

THE TWO-SET RULE
----------------
The CASTING set was lit flat to judge a face. The TRAINING set must vary
everything EXCEPT the face - light, angle, distance, expression, wardrobe,
background - or the LoRA learns the key light instead of the person.

Usage (on the box):
    python3 ~/gen_trainset.py valencia          # one character
    python3 ~/gen_trainset.py valencia --n 4    # short proof run
"""
import argparse
import json
import os
import time
import urllib.request

COMFY = "http://127.0.0.1:8188"
OUTDIR = os.path.expanduser("~/nh_out")

# --- identity, from the LOCKED VISUAL DESCRIPTORs in the character bibles -----
CANON = {
 "valencia": ("a woman of twenty-eight, unmistakably in her twenties with smooth firm skin across the cheek "
              "and jaw, of unplaceable ethnicity, heavy dark brows and a strong nose framing steady dark eyes, "
              "the mouth soft rather than held, faint shadows of tiredness beneath the eyes, dark hair worn "
              "loose and practical and slightly undone, slight build, grave but not defended, secondhand "
              "layering worn as a work uniform"),
 "summer":   ("a woman of thirty-eight, genuinely beautiful in a cool patrician way, skin smooth and firm at "
              "the cheek, jaw and throat, ash-blonde hair in a low chignon, a narrow face, luminous and "
              "well-rested, slim and strong, the brow entirely smooth and unfurrowed, the lips softly closed "
              "and resting rather than pressed, a serene inward calm with light in it, the neck long and the "
              "chin carried level, grace rather than satisfaction"),
 "pengold":  ("a man of forty-one, youthful and pampered, dark hair slicked back tight to the skull over a "
              "clean high forehead with a light silvering of grey at the temples, a short well-manicured dark "
              "hipster beard tidy at the cheek line, smooth clear unweathered skin, full rounded lower cheeks "
              "with the jaw angle softened into a gentle curve, a small soft fullness under the chin, a fuller "
              "neck at the collar, the frame trim and upright, faintly amused and completely unbothered"),
 "dick":     ("a man of thirty-one, soft and delicately beautiful, fine-boned and almost feminine, a smooth "
              "unlined jaw, full soft lips, long lashes and gentle brows, tanned and clear-skinned, the slim "
              "light athletic build of a professional tennis player with no bulk and no hollowing at the "
              "cheeks, dirty-blond hair worn long and loose past the jaw to the collarbone, soft and shining, "
              "an easy open face with nothing behind the eyes"),
}
ANCHOR = {
 "valencia": "nh/VAL-FINAL.png",
 "summer":   "nh/SUM-FINAL.png",
 "pengold":  "nh/PEN-FINAL.png",
 "dick":     "nh/DIC-FINAL.png",
}

# --- the variation axes. Everything here changes; the face does not. ---------
# (framing, light, angle/expression) - 18 per character.
VARIATIONS = [
 ("head-and-shoulders portrait",  "soft north-facing window light from camera left, gentle falloff",      "three-quarter turn to camera left, looking at the lens, mouth closed, calm"),
 ("head-and-shoulders portrait",  "hard midday sun, crisp shadow under the brow and nose",                "straight on to camera, eyes level, faint amusement at the corner of the mouth"),
 ("head-and-shoulders portrait",  "flat overcast daylight, no visible shadow direction",                  "three-quarter turn to camera right, mid-listening, attentive"),
 ("tight close-up of the face",   "warm tungsten lamp low and to one side, deep shadow on the far cheek", "straight on, chin slightly lowered, eyes up to the lens, guarded"),
 ("tight close-up of the face",   "cool blue evening light through glass, low contrast",                  "near profile to camera left, eyes off frame, thinking"),
 ("chest-up portrait",            "single hard key from above, eye sockets in shadow",                    "straight on, head tipped slightly back, unreadable"),
 ("chest-up portrait",            "backlit against a bright window, face in soft open shade",             "three-quarter to camera right, a real open smile"),
 ("chest-up portrait",            "practical overhead fluorescent light, greenish and even",              "straight on, mid-speech, mouth open, animated"),
 ("waist-up medium shot",         "late afternoon sun raking across from camera right",                   "turned away and looking back over the shoulder, curious"),
 ("waist-up medium shot",         "mixed warm interior lamp against cool daylight from a window",         "three-quarter turn, laughing, head back"),
 ("waist-up medium shot",         "dim low-key interior, one small source, most of the frame in shadow",  "straight on, still, weight settled, sombre"),
 ("head-and-shoulders portrait",  "bright bounced fill, almost shadowless, high key",                     "straight on, a polite social smile that does not reach the eyes"),
 ("head-and-shoulders portrait",  "candlelit warmth from below, flickering and uneven",                   "three-quarter to camera left, absorbed, lips parted"),
 ("tight close-up of the face",   "harsh direct on-camera flash, flat and unflattering",                  "straight on, caught off guard, eyes wide, startled"),
 ("chest-up portrait",            "dappled light through leaves, broken highlights across the face",      "three-quarter to camera right, squinting slightly into the light, easy"),
 ("waist-up medium shot",         "streetlight sodium orange at night, dark surroundings",                "straight on, tired, jaw relaxed, eyes heavy"),
 ("head-and-shoulders portrait",  "soft rim light from behind separating the head from a dark ground",    "near profile to camera right, chin level, composed"),
 ("chest-up portrait",            "even studio softbox from the front, natural and clean",                "three-quarter turn to camera left, resting face, eyes steady on the lens"),
]

# Wardrobe must VARY or the LoRA bakes the anchor's clothes into the identity.
# The reference latent pins wardrobe hard, so each frame states its own.
WARDROBE = {
 "valencia": ["a thrifted grey cardigan over a plain white tee","a plain dark tee on its own",
   "a faded flannel work shirt","a cheap nylon rain jacket over a tee","a stained canvas work apron over a tee",
   "a thin secondhand sweater with a stretched neck"],
 "summer": ["a well-cut dark blazer over a fine plain knit","a silk blouse in a muted stone colour",
   "a cashmere roll-neck","a tailored wool coat over a blouse","a plain expensive white tee",
   "a sleeveless shift dress in unpatterned charcoal"],
 "pengold": ["immaculate dark suiting and a crisp white shirt","shirtsleeves with the tie pulled loose",
   "a dark overcoat over the suit","a fine merino polo shirt","black tie and a dinner jacket",
   "an open-collar shirt with no jacket"],
 "dick": ["a beautifully cut heritage workwear jacket over a plain fitted tee","a plain white tee on its own",
   "a canvas chore coat","a fine merino crew neck","a raw denim jacket","a matte technical shell jacket"],
}


TAIL = ("photographic realism, natural skin texture with visible pores and fine detail, sharp focus on the "
        "eyes, 85mm lens, shallow depth of field, documentary photograph, no text, no watermark")


def build(character, idx, seed):
    frame, light, pose = VARIATIONS[idx]
    wear = WARDROBE[character][idx % len(WARDROBE[character])]
    prompt = "%s. Wearing %s. %s. %s. %s. %s" % (
        CANON[character], wear, frame, light, pose, TAIL)
    return {
      "1":  {"class_type":"UNETLoader","inputs":{"unet_name":"flux-2-klein-4b.safetensors","weight_dtype":"default"}},
      "2":  {"class_type":"CLIPLoader","inputs":{"clip_name":"qwen_3_4b.safetensors","type":"flux2"}},
      "3":  {"class_type":"VAELoader","inputs":{"vae_name":"flux2-vae.safetensors"}},
      "4":  {"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["2",0]}},
      "5":  {"class_type":"CLIPTextEncode","inputs":{"text":"","clip":["2",0]}},
      # the anchor, carried as reference conditioning on every single frame
      "10": {"class_type":"LoadImage","inputs":{"image":ANCHOR[character],"upload":"image"}},
      # Downscale the anchor BEFORE encoding. The anchors are 2K 3:2, which at full
      # size becomes a ~15k-token reference context on top of the 4k-token output -
      # a 4-step generation then takes >7 minutes and the A10G thrashes weights
      # between RAM and VRAM. 1024 on the long edge carries identity just as well.
      "13": {"class_type":"ImageScale","inputs":{"image":["10",0],"upscale_method":"lanczos",
              "width":1024,"height":683,"crop":"disabled"}},
      "11": {"class_type":"VAEEncode","inputs":{"pixels":["13",0],"vae":["3",0]}},
      "12": {"class_type":"ReferenceLatent","inputs":{"conditioning":["4",0],"latent":["11",0]}},
      "6":  {"class_type":"EmptyFlux2LatentImage","inputs":{"width":1024,"height":1024,"batch_size":1}},
      "7":  {"class_type":"KSampler","inputs":{"seed":seed,"steps":4,"cfg":1.0,"sampler_name":"euler",
              "scheduler":"simple","denoise":1.0,"model":["1",0],"positive":["12",0],
              "negative":["5",0],"latent_image":["6",0]}},
      "8":  {"class_type":"VAEDecode","inputs":{"samples":["7",0],"vae":["3",0]}},
      "9":  {"class_type":"SaveImage","inputs":{"filename_prefix":"nh/%s/%s_%02d" % (character,character,idx),
              "images":["8",0]}},
    }


def post(graph):
    data = json.dumps({"prompt": graph}).encode()
    req = urllib.request.Request(COMFY + "/prompt", data=data,
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))["prompt_id"]


def wait(pid, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            h = json.load(urllib.request.urlopen(COMFY + "/history/" + pid, timeout=30))
            if pid in h:
                st = h[pid].get("status", {})
                if st.get("completed"):
                    outs = h[pid].get("outputs", {}).get("9", {}).get("images", [])
                    return [o["filename"] for o in outs]
                if st.get("status_str") == "error":
                    return None
        except Exception:
            pass
        time.sleep(3)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("character", choices=sorted(CANON))
    ap.add_argument("--n", type=int, default=len(VARIATIONS))
    ap.add_argument("--seed-base", type=int, default=770000)
    a = ap.parse_args()

    os.makedirs(OUTDIR, exist_ok=True)
    ok = 0
    for i in range(min(a.n, len(VARIATIONS))):
        seed = a.seed_base + i
        t0 = time.time()
        try:
            pid = post(build(a.character, i, seed))
        except Exception as exc:
            print("  [FAIL] %02d submit: %s" % (i, exc), flush=True)
            continue
        files = wait(pid)
        if files:
            ok += 1
            print("  [OK] %02d seed=%d %.0fs -> %s" % (i, seed, time.time()-t0, files[0]), flush=True)
        else:
            print("  [FAIL] %02d seed=%d (timeout or error)" % (i, seed), flush=True)
    print("DONE %s: %d/%d" % (a.character, ok, min(a.n, len(VARIATIONS))), flush=True)


if __name__ == "__main__":
    main()
