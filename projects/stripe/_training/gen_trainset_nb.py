#!/usr/bin/env python3
"""Generate a Stripe character-LoRA trainset with Fal nano-banana-pro/edit (no GPU box).

Uses the clean v6 seeds (seed1_front / seed2_threequarter / seed4_rear) as identity
anchors and re-renders ~24 varied single-subject views at full 1024², each with a
matching `strp, <pose>` caption for ai-toolkit. nano-banana preserves the locked
design (bald dome + Norwood-VII horseshoe rim, very hairy body, sunglasses, white
speedo, gold chain, rear skid-mark) far better than upscaled contact-sheet crops.

Run:  python projects/stripe/_training/gen_trainset_nb.py
Out:  projects/stripe/lora_seeds/v7_nb/{strpNN.png, strpNN.txt}  (+ manifest.csv)
Then: aws s3 cp ... and train via packs/stripe_flux_char_v2.yaml on the L40S box.
"""
import csv
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_FALDIR = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "tools", "fal"))
sys.path.insert(0, _FALDIR)
from nano_banana_edit import edit_image  # noqa: E402

SEEDS = os.path.abspath(os.path.join(_HERE, "..", "lora_seeds", "v6"))
FRONT = os.path.join(SEEDS, "seed1_front.png")
TQ = os.path.join(SEEDS, "seed2_threequarter.png")
REAR = os.path.join(SEEDS, "seed4_rear.png")
OUT = os.path.abspath(os.path.join(_HERE, "..", "lora_seeds", "v7_nb"))
os.makedirs(OUT, exist_ok=True)

IDENTITY = (
    "Stripe — a fat vulgar bald man with a completely bald shiny dome (NO hair on "
    "top), only a black horseshoe rim of hair at the back and sides (Norwood type "
    "VII), a VERY hairy body with thick dark hair on chest, belly, back, arms and "
    "legs, dark sunglasses, a thick gold chain, and a stained white speedo"
)
STYLE = (
    "clean confident black ink outlines, sparse minimal linework, flat gray-tone "
    "shading, lots of white space, black and white hand-drawn cartoon, plain solid "
    "white background, full-body single character reference, no text, no panels, "
    "no labels, no borders, no grid"
)
SKID = ("a brown vertical skid-mark stain running down the centerline of the white "
        "speedo seat, darkest in the center")

# (name, caption-pose, render-instruction). Back/rear views anchor on the rear seed.
VIEWS = [
    ("strp01", "front view, arms relaxed at sides", "standing facing forward, full body, arms relaxed at sides"),
    ("strp02", "front view, both hands on hips", "standing facing forward, full body, both hands on his hips, smug"),
    ("strp03", "front view, arms crossed", "standing facing forward, full body, arms crossed over his chest"),
    ("strp04", "front view, pointing forward", "standing facing forward, full body, one arm pointing toward the viewer"),
    ("strp05", "front view, flexing both arms", "standing facing forward, full body, flexing both biceps"),
    ("strp06", "front view, hands behind head", "standing facing forward, full body, both hands behind his head, elbows out"),
    ("strp07", "three-quarter left view, one hand on hip", "standing in a three-quarter left view, full body, one hand on hip"),
    ("strp08", "three-quarter right view, arms at sides", "standing in a three-quarter right view, full body, arms at sides"),
    ("strp09", "three-quarter left view, mid-stride walking", "walking mid-stride in a three-quarter left view, full body"),
    ("strp10", "left side profile, arms at sides", "standing in a left side profile, full body, belly in profile, arms at sides"),
    ("strp11", "right side profile, gesturing", "standing in a right side profile, full body, one arm raised gesturing"),
    ("strp12", "left side profile, mid-stride walking", "walking in a left side profile, full body, one leg forward"),
    ("strp13", "front view, leaning back laughing", "standing facing forward, full body, leaning back laughing, belly out"),
    ("strp14", "front view, thumbs up", "standing facing forward, full body, giving a thumbs up with one hand"),
    ("strp15", "front view, arms spread wide", "standing facing forward, full body, both arms spread out wide"),
    ("strp16", "three-quarter right view, hand on chin", "standing in a three-quarter right view, full body, one hand on chin"),
    ("strp17", "front view, hands on belly", "standing facing forward, full body, both hands resting on his belly"),
    ("strp18", "three-quarter left view, arms crossed", "standing in a three-quarter left view, full body, arms crossed"),
    # --- rear / back views (anchor on the rear seed; keep the signature skid-mark) ---
    ("strp19", "rear view, arms at sides", f"standing with his back to the viewer, full body rear view, hands at sides, {SKID}"),
    ("strp20", "rear view, hands on hips", f"standing with his back to the viewer, full body rear view, both hands on hips, {SKID}"),
    ("strp21", "three-quarter back left view", f"standing in a three-quarter back-left view, full body, looking over his shoulder, {SKID}"),
    ("strp22", "three-quarter back right view", f"standing in a three-quarter back-right view, full body, {SKID}"),
    ("strp23", "rear view, mid-stride walking away", f"walking away from the viewer mid-stride, full body rear view, {SKID}"),
    ("strp24", "rear view, looking back over shoulder", f"standing back to the viewer, full body, turning his head to look back over his shoulder, {SKID}"),
]


def refs_for(name):
    return [REAR, TQ] if name >= "strp19" else [FRONT, TQ]


def main():
    for f in (FRONT, TQ, REAR):
        if not os.path.exists(f):
            raise FileNotFoundError(f"Missing anchor seed: {f}")
    manifest = []
    for i, (name, caption_pose, instruction) in enumerate(VIEWS):
        png = os.path.join(OUT, f"{name}.png")
        txt = os.path.join(OUT, f"{name}.txt")
        prompt = (
            f"Re-draw this exact same character as a single full-body reference. "
            f"{IDENTITY}. Pose: {instruction}. Render in this style: {STYLE}. "
            f"Keep his face, body shape, hair pattern and outfit identical to the "
            f"reference images — only change the pose and camera angle."
        )
        print(f"[{i+1}/{len(VIEWS)}] {name}: {caption_pose}", flush=True)
        try:
            edit_image(prompt, refs_for(name), out=png, resolution="1K",
                       aspect_ratio="2:3", seed=100 + i, verbose=False)
        except Exception as e:
            print(f"  FAILED {name}: {e}", flush=True)
            continue
        with open(txt, "w", encoding="utf-8") as fh:
            fh.write(f"strp, {caption_pose}\n")
        manifest.append((name, caption_pose))
        print(f"  saved {os.path.basename(png)} + caption", flush=True)

    with open(os.path.join(OUT, "manifest.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "caption"])
        for name, cap in manifest:
            w.writerow([f"{name}.png", f"strp, {cap}"])
    print(f"\nTRAINSET_DONE — {len(manifest)}/{len(VIEWS)} images in {OUT}", flush=True)


if __name__ == "__main__":
    main()
