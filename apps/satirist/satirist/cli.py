"""CLI for the satirist creative loop.

  python -m satirist.cli --topic "Tammany" [--ingest-feed URL] [--no-judge] [--dry-run]

--dry-run swaps the GPU render for a placeholder image so the loop runs without a GPU.
"""
import argparse
import json
import sys
import textwrap

from PIL import Image, ImageDraw

from . import config
from .brain import ideate
from .judge import score_concept
from .pipeline import run


def placeholder_render(image_prompt: str, out_path: str) -> str:
    """Non-GPU stand-in: writes the image_prompt as text onto a gray canvas."""
    img = Image.new("RGB", (768, 768), (210, 210, 210))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "PLACEHOLDER RENDER (no GPU)\n\n" + "\n".join(
        textwrap.wrap(image_prompt, width=70)[:24]), fill=(20, 20, 20))
    img.save(out_path)
    return out_path


def main(argv=None):
    ap = argparse.ArgumentParser(prog="satirist")
    ap.add_argument("--topic", required=True)
    ap.add_argument("--ingest-feed", default=None, help="RSS/Atom URL to ingest before selecting")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="placeholder render (no GPU)")
    ap.add_argument("--db", default=config.DB_PATH)
    ap.add_argument("--out", default=config.OUT_DIR)
    args = ap.parse_args(argv)

    if args.ingest_feed:
        import intake_core.pipeline as ip
        import intake_core.store as store
        store.init_db(args.db)
        ip.ingest_feed(args.ingest_feed, args.db)

    if args.dry_run:
        render_fn = placeholder_render
    else:
        from .render import render_sdxl
        render_fn = lambda prompt, out_path: render_sdxl(prompt, out_path)

    judge_fn = None if args.no_judge else score_concept
    res = run(args.topic, render_fn=render_fn, brain_fn=ideate,
              judge_fn=judge_fn, db_path=args.db, out_dir=args.out)
    print(json.dumps({k: v for k, v in res.items() if k != "signal"}, indent=2, default=str))
    return 0 if res["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
