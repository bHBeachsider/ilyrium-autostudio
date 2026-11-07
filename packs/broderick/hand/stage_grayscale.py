#!/usr/bin/env python3
"""Stage the Broderick grayscale subset for Flux LoRA training.

Reads the dataset_v0 manifest, selects rows with color_mode == "grayscale" and excluded == False,
and copies each image + its same-name .txt caption sidecar into the training dir. The grayscale
subset IS the house style; the 17 color panels are left out so they don't dilute the ink look.

Usage:
  python stage_grayscale.py --src <dataset_v0 dir> [--dst <train dir>]
Default --dst is packs/broderick/data/hand/train relative to this file.
"""
import argparse
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DST = os.path.join(os.path.dirname(HERE), "data", "hand", "train")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="dataset_v0 directory (has manifest.jsonl + images/)")
    ap.add_argument("--dst", default=DEFAULT_DST)
    args = ap.parse_args()

    manifest = os.path.join(args.src, "manifest.jsonl")
    os.makedirs(args.dst, exist_ok=True)
    copied = skipped = missing = 0
    with open(manifest, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row.get("color_mode") != "grayscale" or row.get("excluded"):
                skipped += 1
                continue
            img_rel = row["file_name"]                      # e.g. images/foo.png
            base, ext = os.path.splitext(os.path.basename(img_rel))
            img_src = os.path.join(args.src, img_rel)
            txt_src = os.path.join(args.src, "images", base + ".txt")
            if not (os.path.exists(img_src) and os.path.exists(txt_src)):
                missing += 1
                continue
            shutil.copy2(img_src, os.path.join(args.dst, base + ext))
            shutil.copy2(txt_src, os.path.join(args.dst, base + ".txt"))
            copied += 1
    print(f"staged {copied} grayscale image+caption pairs -> {args.dst}")
    print(f"(skipped {skipped} non-grayscale/excluded, missing {missing})")


if __name__ == "__main__":
    main()
