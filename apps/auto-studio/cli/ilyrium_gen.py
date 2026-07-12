#!/usr/bin/env python3
"""ilyrium_gen.py -- qwen3-coder prompt -> ComfyUI (registry models) -> PNG.

Runs ON the EC2 box (local access to ollama :11434 and ComfyUI :8188).
Driven from the desktop by box.ps1 / the ilyrium REPL, which ship this file
PLUS media/comfyui_engine.py PLUS model_registry.json over SSM and run it
with the ComfyUI venv python.

This is a THIN CLI over comfyui_engine — all graph building, editing logic
and ComfyUI HTTP live in the engine (the studio's single ComfyUI module).
Models come from model_registry.json (provider 'comfyui'); add a model there,
not here.

Modes:
  text-to-image (default)        just an idea/prompt
  image-to-image (--img NAME)    NAME is a file already uploaded to ComfyUI
                                 /input (the REPL uploads it via /upload/image),
                                 used as the init latent with --denoise strength.
  inpainting (--img + --mask or --region)   only the masked area changes.

Examples (on the box):
  python ilyrium_gen.py "a lighthouse at dawn" --model zimage
  python ilyrium_gen.py "cyberpunk street" --model flux2 --seed 12
  python ilyrium_gen.py "make it watercolor" --model flux2 \
      --img ref.png --denoise 0.65
  python ilyrium_gen.py "a fox" --prompt-only
"""
import argparse
import os
import sys

# The engine sits next to this file on the box (shipped flat by box.ps1);
# in the repo it lives in ../media/.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, "..", "media"), os.path.join(_HERE, "..")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import comfyui_engine as ce           # box layout (flat)
except ImportError:                       # repo layout (package)
    from media import comfyui_engine as ce


def main():
    try:
        model_ids = ce.available_model_ids()
    except Exception as e:
        sys.exit(f"model registry unavailable: {e}")

    ap = argparse.ArgumentParser(
        description="qwen3-coder prompt -> ComfyUI image (thin CLI over comfyui_engine)")
    ap.add_argument("idea", help="idea to expand, OR the final prompt w/ --raw")
    ap.add_argument("--model", choices=model_ids, default=ce.DEFAULT_MODEL)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=1024)
    ap.add_argument("--prefix", default=None,
                    help="ComfyUI filename_prefix (default cli/<model>_<seed>)")
    ap.add_argument("--img", default=None,
                    help="reference image name already in ComfyUI /input "
                         "(enables img2img)")
    ap.add_argument("--mask", default=None,
                    help="mask image name in ComfyUI /input; white=change, "
                         "black=keep. With --img, enables inpainting.")
    ap.add_argument("--region", default=None,
                    help="build a rectangular inpaint mask from x1,y1,x2,y2 "
                         "(fractions 0-1, or pixels). Alternative to --mask.")
    ap.add_argument("--denoise", type=float, default=0.65,
                    help="img2img strength; lower keeps more of the reference")
    ap.add_argument("--base-prompt", default=None,
                    help="previous scene's prompt; when set, qwen3 edits it "
                         "with the idea as a change (iterative editing)")
    ap.add_argument("--base-prompt-b64", default=None,
                    help="base prompt as base64 (avoids shell-escaping); "
                         "takes precedence over --base-prompt")
    ap.add_argument("--raw", action="store_true",
                    help="use idea verbatim, skip qwen prompt-gen")
    ap.add_argument("--prompt-only", action="store_true",
                    help="print the qwen prompt and exit")
    a = ap.parse_args()

    base = a.base_prompt
    if a.base_prompt_b64:
        import base64
        base = base64.b64decode(a.base_prompt_b64).decode("utf-8")

    entry = ce.load_model(a.model)
    hint = (entry.get("recipe") or {}).get("hint", entry.get("base", "photo"))
    if a.raw:
        prompt = a.idea
    else:
        prompt = ce.gen_prompt(a.idea, hint, base=base)
    print("PROMPT:", prompt, flush=True)
    if a.prompt_only:
        return

    prefix = a.prefix or f"cli/{a.model}_{a.seed}"
    denoise = a.denoise if a.img else 1.0
    wf = ce.build_graph(entry, prompt, seed=a.seed, width=a.width,
                        height=a.height, img=a.img, mask=a.mask,
                        region=(a.region if a.img else None),
                        denoise=denoise, prefix=prefix)
    # No output_dir -> the box-local ComfyUI output path (box.ps1 scp's it down).
    print("IMAGE:", ce.submit_and_wait(wf, timeout=600), flush=True)


if __name__ == "__main__":
    main()
