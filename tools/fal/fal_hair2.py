#!/usr/bin/env python3
"""Stage-6 hair (Fal): add the Norwood-6 horseshoe fringe via a single maskless
TEXT edit through nano-banana-pro/edit (Gemini 3 Pro Image).

Replaces the old SAM(evf-sam) + Flux-Fill carve-the-scalp pipeline: that needed
an accurate scalp mask, a deterministic side-band carve, and an inpaint pass, and
still fought the crown. The text editor lands the horseshoe in one instruction
while preserving the face, beard, body, outfit, and the B&W cartoon ink style.
No GPU box. See tools/fal/nano_banana_edit.py for the reusable helper.
"""
import os

from nano_banana_edit import edit_image

OUT = r"C:/Users/bradu/Documents/ilyrium-autostudio/projects/stripe/refs/fal_hair2"
os.makedirs(OUT, exist_ok=True)
IMAGES = [
    r"C:/Users/bradu/Documents/ilyrium-autostudio/projects/stripe/refs/stripe_cartoon_front_bracelet.jpg",
    r"C:/Users/bradu/Documents/ilyrium-autostudio/projects/stripe/lora_seeds/v6/seed1_front.png",
    r"C:/Users/bradu/Documents/ilyrium-autostudio/projects/stripe/lora_seeds/v6/seed2_threequarter.png",
]

HAIR_PROMPT = (
    "Give this bald cartoon man a bold, solid-black Norwood-6 horseshoe fringe of "
    "hair: thick black hair and sideburns clearly visible on the sides and back of "
    "the head above the ears, the very top of the crown stays bald. Keep his face, "
    "beard, sunglasses, body, outfit, and the black-and-white cartoon ink line-art "
    "style exactly the same."
)


def run(img_path):
    name = os.path.splitext(os.path.basename(img_path))[0]
    edit_image(HAIR_PROMPT, img_path, out=f"{OUT}/{name}_hair.png",
               resolution="2K", aspect_ratio="auto", seed=7)
    print("done", name, flush=True)


if __name__ == "__main__":
    for p in IMAGES:
        run(p)
    print("FAL_HAIR2_DONE", flush=True)
