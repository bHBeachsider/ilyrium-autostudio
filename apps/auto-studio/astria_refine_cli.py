#!/usr/bin/env python3
"""
astria_refine_cli.py - run the Astria character-LoRA refine op WITHOUT the pipeline service.

Same engine as the Stage-4 console (producer.refine_shot_astria): it reuses producer._resolve_tune
(tune lookup + 'trained' gate) and media.astria_renderer.render_refine (submit/poll/download), so
results are identical to the in-app path. Use it to put a garment/reference image on the character
ad-hoc, or to batch-process a prop_concepts shortlist.

PREREQS
  - ASTRIA_API_KEY in the repo-root .env (or the real env, or ~/.astria/config.json).
  - The character tune registered as status="trained" with an astria_tune_id in
    projects/<project>/03_design/characters/loras/lora_library.json.

USAGE
  # single garment on the character (Flux Virtual Try-on):
  python astria_refine_cli.py --project satesh --family flux \
      --text "satesh, wearing an ornate gold patka sash, full length, studio lighting" \
      --garment-image-url https://host/sash.jpg --num-images 4

  # single reference-guided refine (any controlnet):
  python astria_refine_cli.py --project satesh --family sdxl \
      --text "satesh, embroidered mojari footwear, studio" \
      --input-image-url https://host/ref.jpg --controlnet reference --denoising 0.55

  # batch a prop_concepts shortlist (skips items whose garment_image_url is still null):
  python astria_refine_cli.py --project satesh \
      --queue projects/satesh/03_design/props/_concepts/refine_queue.json

OUTPUT
  Stills download to --out (default: projects/<project>/03_design/props/_concepts/_out/).
"""
from __future__ import annotations
import argparse, json, os, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)


def _load_env():
    """Fill missing env vars from any .env walking up from script dir + cwd (real env wins)."""
    for start in (HERE, os.getcwd()):
        d = start
        while True:
            f = os.path.join(d, ".env")
            if os.path.isfile(f):
                for line in open(f, encoding="utf-8", errors="ignore"):
                    line = line.strip()
                    if line.startswith("export "):
                        line = line[7:].strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            nd = os.path.dirname(d)
            if nd == d:
                break
            d = nd


def _proj_dir(project: str) -> str:
    from project_paths import resolve_project
    return resolve_project(project)


def _build_fields(body: dict, family: str, trigger: str) -> dict:
    """Reuse producer's passthrough map so the field mapping never drifts from the app path."""
    from producer import _REFINE_PASSTHROUGH, _FLUX_ONLY
    fields = {}
    for k, dest in _REFINE_PASSTHROUGH.items():
        v = body.get(k)
        if v is None or v == "":
            continue
        fields[dest] = ("true" if v else "false") if isinstance(v, bool) else v
    if family == "sdxl":
        for fk in _FLUX_ONLY:
            fields.pop(fk, None)
    fields.setdefault("prompt[text]", trigger)
    return fields


def _run_one(project: str, body: dict, out_dir: str, label: str) -> list:
    from producer import _resolve_tune
    from media import astria_renderer as ar
    family = (body.get("model_family") or "").lower()
    entry, tune_id = _resolve_tune(_proj_dir(project), family, body.get("character"))
    n = max(1, int(body.get("num_images") or 1))
    fields = _build_fields(body, family, entry.get("trigger_word", ""))
    fields["prompt[num_images]"] = n
    base = f"{label}_{family}_{int(datetime.now().timestamp())}"
    print(f"[astria] tune={tune_id} family={family} num_images={n}  '{label}'")
    paths = ar.render_refine(tune_id, fields, out_dir, base, num_images=n)
    for p in paths:
        print(f"   -> {p}")
    return paths


def main():
    ap = argparse.ArgumentParser(description="Ad-hoc Astria character-LoRA refine (no service).")
    ap.add_argument("--project", default="satesh")
    ap.add_argument("--out", help="output dir (default projects/<project>/03_design/props/_concepts/_out)")
    # single-shot
    ap.add_argument("--family", choices=["flux", "sdxl"])
    ap.add_argument("--character")
    ap.add_argument("--text")
    ap.add_argument("--negative-prompt", dest="negative_prompt")
    ap.add_argument("--garment-image-url", dest="garment_image_url")
    ap.add_argument("--input-image-url", dest="input_image_url")
    ap.add_argument("--mask-image-url", dest="mask_image_url")
    ap.add_argument("--controlnet")
    ap.add_argument("--denoising", type=float, dest="denoising_strength")
    ap.add_argument("--aspect-ratio", dest="aspect_ratio", default="1:1")
    ap.add_argument("--num-images", type=int, default=4, dest="num_images")
    # batch
    ap.add_argument("--queue", help="a prop_concepts refine_queue.json to batch-process")
    a = ap.parse_args()

    _load_env()
    out_dir = a.out or os.path.join(_proj_dir(a.project), "03_design", "props", "_concepts", "_out")
    os.makedirs(out_dir, exist_ok=True)

    if a.queue:
        data = json.load(open(a.queue, encoding="utf-8"))
        items = data.get("items", [])
        ok = skipped = failed = 0
        for it in items:
            if not it.get("garment_image_url") and not it.get("input_image_url"):
                print(f"[skip] {it.get('category')}/{it.get('concept_file')}: "
                      f"no garment_image_url/input_image_url set (host _local_image first)")
                skipped += 1
                continue
            label = f"{it.get('category','item')}_{os.path.splitext(it.get('concept_file','x'))[0]}"
            try:
                _run_one(a.project, it, out_dir, label)
                ok += 1
            except Exception as e:
                print(f"   ! {type(e).__name__}: {e}")
                failed += 1
        print(f"\nqueue done: {ok} generated, {skipped} skipped, {failed} failed -> {out_dir}")
        return

    if not a.family or not (a.garment_image_url or a.input_image_url):
        ap.error("single-shot needs --family and one of --garment-image-url / --input-image-url "
                 "(or use --queue)")
    body = {k: getattr(a, k) for k in
            ("family", "character", "text", "negative_prompt", "garment_image_url",
             "input_image_url", "mask_image_url", "controlnet", "denoising_strength",
             "aspect_ratio", "num_images")}
    body["model_family"] = body.pop("family")
    try:
        _run_one(a.project, body, out_dir, "refine")
        print(f"\ndone -> {out_dir}")
    except Exception as e:
        sys.exit(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
