#!/usr/bin/env python3
"""Composite the 5 rendered STRIPE panels into a finished strip with title card + dialogue
balloons, using the committed strip_compositor (run locally for the Windows comic fonts)."""
import sys
sys.path.insert(0, r"C:/Users/bradu/Documents/ilyrium-autostudio/apps/satirist")
from satirist import strip_compositor as sc
from PIL import Image

PD = r"C:/Users/bradu/Documents/ilyrium-autostudio/projects/stripe/render_test"
comic = {"title": "STRIPE", "panels": [
    {"n": 1, "dialogue": "STRIPE: The Gulfstream's in for a refit, doll. The hardship is real."},
    {"n": 2, "dialogue": "STRIPE: Twelve bedrooms. Built it all on refurbished mattresses, baby."},
    {"n": 3, "dialogue": "STRIPE: Boca? Aspen? The Shore?! A man can't be three places at once!"},
    {"n": 4, "dialogue": "LADY: ...is that a stripe?"},
    {"n": 5, "dialogue": "STRIPE: They simply cannot resist the Stripe."},
]}
imgs = {n: Image.open(f"{PD}/panel{n}.png") for n in range(1, 6)}
strip = sc.compose_strip(comic, imgs, cell=(512, 512), border=2)
out = f"{PD}/STRIPE_strip.png"
sc.save_strip(strip, {"title": "STRIPE", "series": "Stripe", "panels": 5,
                      "logline": "Boca mattress mogul brags poolside, oblivious to the stripe on his speedo."}, out)
print("saved", out, strip.size)
