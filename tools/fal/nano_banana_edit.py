#!/usr/bin/env python3
"""Text-driven image editing via Fal `nano-banana-pro/edit` (Google Gemini 3 Pro Image).

Maskless edits: you describe the change in plain text and pass one or more
reference images. Replaces the SAM+FluxFill mask dance for edits that can be
expressed as an instruction ("give him a black horseshoe fringe", "put a gold
bracelet on the left wrist", "make the background a newsroom"). No GPU box.

Reuses the studio's existing Fal conventions (fal_client.subscribe /
upload_file, FAL_KEY from slm-foundry/.env, result["images"][i]["url"]).

CLI:
    python tools/fal/nano_banana_edit.py "add a black horseshoe fringe of hair" \
        --image projects/stripe/refs/stripe_cartoon_front_bracelet.jpg \
        --out projects/stripe/refs/nb_edit/front_hair.png --resolution 2K

Library:
    from tools.fal.nano_banana_edit import edit_image
    paths = edit_image("...prompt...", ["a.png", "b.png"], out="out/edited.png")
"""
import argparse
import os
import urllib.request

from dotenv import load_dotenv

ENDPOINT = "fal-ai/nano-banana-pro/edit"
_ENV = r"C:/Users/bradu/Documents/slm-foundry/.env"

ASPECT_RATIOS = {"auto", "21:9", "16:9", "3:2", "4:3", "5:4", "1:1",
                 "4:5", "3:4", "2:3", "9:16"}
RESOLUTIONS = {"1K", "2K", "4K"}
OUTPUT_FORMATS = {"jpeg", "png", "webp"}


def _ensure_key():
    if not os.getenv("FAL_KEY"):
        load_dotenv(_ENV)
    if not os.getenv("FAL_KEY"):
        raise RuntimeError(f"FAL_KEY not set and not found in {_ENV}.")


def _to_url(src):
    """Pass http(s) URLs through; upload local files and return the fal URL."""
    import fal_client
    if isinstance(src, str) and src.startswith(("http://", "https://")):
        return src
    if not os.path.exists(src):
        raise FileNotFoundError(f"Image not found: {src}")
    return fal_client.upload_file(src)


def edit_image(prompt, images, out=None, *, aspect_ratio="auto", resolution="2K",
               output_format="png", seed=None, num_images=1, system_prompt="",
               safety_tolerance="4", verbose=True):
    """Edit image(s) by text instruction. Returns the list of saved local paths
    (or, if `out` is None, the list of result URLs).

    images:       a path/URL or list thereof (passed to the model as image_urls)
    out:          output path; for num_images>1, an index is inserted before the ext
    aspect_ratio: one of ASPECT_RATIOS (default 'auto' = keep input ratio)
    resolution:   1K | 2K | 4K
    """
    _ensure_key()
    import fal_client

    if isinstance(images, (str, os.PathLike)):
        images = [images]
    if not images:
        raise ValueError("At least one input image is required.")
    if aspect_ratio not in ASPECT_RATIOS:
        raise ValueError(f"aspect_ratio must be one of {sorted(ASPECT_RATIOS)}")
    if resolution not in RESOLUTIONS:
        raise ValueError(f"resolution must be one of {sorted(RESOLUTIONS)}")
    if output_format not in OUTPUT_FORMATS:
        raise ValueError(f"output_format must be one of {sorted(OUTPUT_FORMATS)}")

    image_urls = [_to_url(s) for s in images]
    args = {
        "prompt": prompt,
        "image_urls": image_urls,
        "num_images": num_images,
        "aspect_ratio": aspect_ratio,
        "output_format": output_format,
        "resolution": resolution,
        "safety_tolerance": str(safety_tolerance),
    }
    if seed is not None:
        args["seed"] = seed
    if system_prompt:
        args["system_prompt"] = system_prompt

    def _on_update(update):
        if verbose and isinstance(update, getattr(fal_client, "InProgress", ())):
            for log in getattr(update, "logs", []) or []:
                msg = log.get("message") if isinstance(log, dict) else str(log)
                if msg:
                    print(f"   fal: {msg}", flush=True)

    if verbose:
        print(f"🎨 [nano-banana-pro/edit] {len(image_urls)} ref(s) -> "
              f"{num_images} image(s) @ {resolution} ({aspect_ratio})", flush=True)

    result = fal_client.subscribe(ENDPOINT, arguments=args, with_logs=True,
                                  on_queue_update=_on_update)

    imgs = result.get("images") if isinstance(result, dict) else None
    if not imgs:
        raise RuntimeError(f"fal returned no images. keys="
                           f"{list(result) if isinstance(result, dict) else type(result)}")
    urls = [im["url"] for im in imgs if isinstance(im, dict) and im.get("url")]
    if not urls:
        raise RuntimeError("fal images contained no URLs.")

    if out is None:
        return urls

    saved = []
    base, ext = os.path.splitext(out)
    ext = ext or f".{output_format}"
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    for i, url in enumerate(urls):
        path = out if len(urls) == 1 else f"{base}_{i}{ext}"
        urllib.request.urlretrieve(url, path)
        saved.append(path)
        if verbose:
            print(f"   saved {path}", flush=True)
    return saved


def _main():
    ap = argparse.ArgumentParser(description="Text-driven image edit via Fal nano-banana-pro/edit")
    ap.add_argument("prompt", help="Edit instruction in plain text")
    ap.add_argument("--image", "-i", action="append", required=True, dest="images",
                    help="Input image path or URL (repeatable for multi-reference edits)")
    ap.add_argument("--out", "-o", required=True, help="Output path (index inserted if -n > 1)")
    ap.add_argument("--aspect", default="auto", choices=sorted(ASPECT_RATIOS))
    ap.add_argument("--resolution", default="2K", choices=sorted(RESOLUTIONS))
    ap.add_argument("--format", dest="output_format", default="png", choices=sorted(OUTPUT_FORMATS))
    ap.add_argument("-n", "--num-images", type=int, default=1)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--system-prompt", default="")
    args = ap.parse_args()

    edit_image(args.prompt, args.images, out=args.out, aspect_ratio=args.aspect,
               resolution=args.resolution, output_format=args.output_format,
               num_images=args.num_images, seed=args.seed,
               system_prompt=args.system_prompt)
    print("NANO_BANANA_EDIT_DONE", flush=True)


if __name__ == "__main__":
    _main()
