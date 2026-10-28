#!/usr/bin/env python3
r"""Stage 3.9 - train the four character LoRAs on fal.

WHY fal AND NOT THE REPO'S OWN TRAINER (NH-USA-019)
---------------------------------------------------
`ilyrium-shots/train_lora.py` drives Tensor.art against endpoint paths that were
never verified - every one returns 405 - and its urllib transport sends no
User-Agent, so Cloudflare answers 403 "error code: 1010" whatever the token. No
trainer is installed on the EC2 box either. fal's portrait trainer is verified,
runs on the balance already funded, and returns `diffusers_lora_file`: a real
portable .safetensors, unlike Astria whose tunes expire and yield no checkpoint
(NH-USA-013).

MODEL CHOICE
------------
`flux-lora-portrait-trainer` over `flux-lora-fast-training`: these are faces, and
the portrait trainer crops to the subject and trains multiresolution. Steps are set
to 2000 rather than its 2500 default - 18-image character sets converge well before
2500 and the trainer bills per step ($0.0024), so this is $4.80 a head instead of
$6.00.

TRIGGER PHRASES
---------------
Set for bookkeeping, but do NOT rely on them: Flux trigger tokens have twice failed
to bind in this studio's own library. Identity comes from the LoRA weights, and the
shot prompt should describe the character rather than lean on a magic token.

Run:  venv\Scripts\python.exe projects\new_harnomy_usa\03_design\characters\loras\train_loras.py
Cost: 2000 steps x $0.0024 x 4 = ~$19.20.
"""
import json
import os
import sys
import time
import urllib.request
import zipfile

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
CHARS = os.path.dirname(HERE)
SETS = os.path.join(CHARS, "training", "sets")
OUT = HERE

for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env",
            r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

STEPS = 2000

CHARACTERS = [
    ("valencia", "valencia_strong_nh", "VAL-FINAL.png"),
    ("summer",   "summer_winters_nh",  "SUM-FINAL.png"),
    ("pengold",  "pengold_heavens_nh", "PEN-FINAL.png"),
    ("dick",     "dick_suede_nh",      "DIC-FINAL.png"),
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


def make_zip(character):
    src = os.path.join(SETS, character)
    pngs = sorted(f for f in os.listdir(src) if f.lower().endswith(".png"))
    if not pngs:
        return None, 0
    zp = os.path.join(OUT, "_%s_trainset.zip" % character)
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in pngs:
            z.write(os.path.join(src, f), f)
    return zp, len(pngs)


def main():
    preflight()
    import fal_client
    os.makedirs(OUT, exist_ok=True)
    results = {}

    for character, trigger, anchor in CHARACTERS:
        print("=" * 60, flush=True)
        print("== %s  (trigger: %s)" % (character, trigger), flush=True)
        zp, n = make_zip(character)
        if not zp:
            print("   [SKIP] no images in %s" % os.path.join(SETS, character), flush=True)
            continue
        print("   %d images, zip %.1f MB" % (n, os.path.getsize(zp) / 1e6), flush=True)

        t0 = time.time()
        try:
            data_url = fal_client.upload_file(zp)
            print("   uploaded, training %d steps ..." % STEPS, flush=True)
            res = fal_client.subscribe("fal-ai/flux-lora-portrait-trainer", arguments={
                "images_data_url": data_url,
                "trigger_phrase": trigger,
                "steps": STEPS,
                "subject_crop": True,
                "multiresolution_training": True,
            })
        except Exception as exc:
            print("   [FAIL] %s: %s" % (character, exc), flush=True)
            continue

        lora = (res or {}).get("diffusers_lora_file") or {}
        cfg = (res or {}).get("config_file") or {}
        if not lora.get("url"):
            print("   [FAIL] no lora in result: %s" % str(res)[:300], flush=True)
            continue

        dst = os.path.join(OUT, "%s.safetensors" % trigger)
        urllib.request.urlretrieve(lora["url"], dst)
        if cfg.get("url"):
            urllib.request.urlretrieve(cfg["url"], os.path.join(OUT, "%s.config.json" % trigger))

        mins = (time.time() - t0) / 60.0
        meta = {
            "character": character,
            "trigger_phrase": trigger,
            "note": "Trigger phrases have twice failed to bind on Flux in this studio. "
                    "Describe the character in the prompt; do not rely on the token.",
            "base": "FLUX.1-dev (fal flux-lora-portrait-trainer)",
            "steps": STEPS,
            "images": n,
            "anchor": "03_design/characters/casting/finals/" + anchor,
            "trainset": "03_design/characters/training/sets/%s/ (gitignored, "
                        "reproducible from training/gen_trainset.py with seeds 770000+i)" % character,
            "file": os.path.basename(dst),
            "bytes": os.path.getsize(dst),
            "trained_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "minutes": round(mins, 1),
            "cost_usd": round(STEPS * 0.0024, 2),
        }
        with open(os.path.join(OUT, "%s.meta.json" % trigger), "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2)
        results[character] = meta
        print("   [OK] %s  %.1f MB  %.1f min" % (os.path.basename(dst),
                                                 os.path.getsize(dst) / 1e6, mins), flush=True)
        os.remove(zp)

    with open(os.path.join(OUT, "_TRAIN_RESULTS.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("=" * 60, flush=True)
    print("DONE %d/%d" % (len(results), len(CHARACTERS)), flush=True)


if __name__ == "__main__":
    main()
