"""Orchestrate the creative loop. Brain/judge/render are injected callables (real ones wired in cli.py)."""
import os
import re

from . import caption as cap_mod
from . import config
from . import render
from .signal_select import select_signal

_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    return _SLUG.sub("_", (text or "").lower()).strip("_")


def run(topic, *, render_fn, brain_fn, judge_fn=None, db_path=None, out_dir=None,
        threshold=None, avatar_desc=None):
    """Run signal -> ideate -> (judge -> one revise) -> render -> caption -> save.

    render_fn(image_prompt, out_path) -> out_path   (writes a PNG; GPU in prod)
    brain_fn(event_summary, revise_hint="") -> {"allegory_rationale","image_prompt"[, "caption"]}
    judge_fn(concept) -> {"score","rationale"} or None to skip the judge.
    avatar_desc: pass the recurring-character description (e.g. config.AVATAR_DESC) for a
        CHARACTER panel so it's injected after the style block; None for a general cartoon.

    Returns {"status": "ok"|"no_signal", ...}.
    """
    db_path = db_path or config.DB_PATH
    out_dir = out_dir or config.OUT_DIR
    thr = config.JUDGE_THRESHOLD if threshold is None else threshold

    signal = select_signal(topic, db_path)
    if signal is None:
        return {"status": "no_signal", "topic": topic}

    event = signal["summary"] or signal["topic"]
    concept = brain_fn(event)
    verdict = None
    if judge_fn is not None:
        verdict = judge_fn(concept)
        if float(verdict.get("score", 0.0)) < thr:
            concept = brain_fn(event, revise_hint="Sharpen the central allegory; "
                                                  "make the villain and the labeled symbols unmistakable.")
            verdict = judge_fn(concept)

    caption = concept.get("caption") or cap_mod.derive_caption(concept["allegory_rationale"])
    slug = slugify(signal["topic"]) or "cartoon"

    os.makedirs(out_dir, exist_ok=True)
    raw_png = os.path.join(out_dir, f"{slug}_raw.png")
    prompt = render.compose_prompt(concept["image_prompt"], style_block=config.STYLE_BLOCK,
                                   avatar_desc=avatar_desc, trigger=config.STYLE_TRIGGER)
    render_fn(prompt, raw_png)

    from PIL import Image
    final = cap_mod.compose_caption_banner(Image.open(raw_png), caption)
    meta = {"topic": signal["topic"], "allegory_rationale": concept["allegory_rationale"],
            "image_prompt": concept["image_prompt"], "caption": caption,
            "verdict": verdict, "signal": signal}
    png = cap_mod.save_artifact(final, meta, out_dir, slug)
    return {"status": "ok", "png": png, "concept": concept, "verdict": verdict,
            "signal": signal}
