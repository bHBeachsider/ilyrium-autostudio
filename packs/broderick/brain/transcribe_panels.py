#!/usr/bin/env python3
"""transcribe_panels.py — recover in-panel TEXT (the verbal payload the captions omit) per panel.

Vision-LLM transcription (open-weight Qwen3-VL via OpenRouter) over each non-excluded panel in the
manifest. Writes structured-text sidecars at <dataset>/transcripts/<base>.txt that
extract_operators.py consumes, plus a confidence index for the human spot-check queue. Resumable.

Usage:
  python transcribe_panels.py --manifest <dataset_v0/manifest.jsonl> [--limit N] [--dry-run]
  python transcribe_panels.py --manifest ... --review        # list panels, lowest confidence first
Env: OPENROUTER_API_KEY required (live). BRODERICK_VISION overrides model (default qwen/qwen3-vl-32b-instruct).
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

MODEL = os.environ.get("BRODERICK_VISION", "qwen/qwen3-vl-32b-instruct")

PROMPT = """Transcribe ALL text visible in this single comic panel EXACTLY as written — do not \
paraphrase, correct, or translate. Read in natural order (top-to-bottom, left-to-right; follow \
balloon tails).

Label each piece by type:
  CAPTION:  narration / caption-box text
  <SPEAKER>: dialogue inside a speech balloon (use a short speaker label if identifiable, else SPEAKER)
  SIGN:     text that appears in the artwork (signs, shirts, labels, stickers)
  SFX:      sound effects / onomatopoeia

If any text is unreadable, write "[illegible: <what + why>]" — NEVER invent or complete words.
If the panel has no text, output exactly: (no text)
End with a line: CONFIDENCE: <0.0-1.0> — your confidence in the transcription.
Output only the labeled lines."""


def _key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if not k:
        env = Path(r"C:\Users\bradu\Documents\PermitHub-API\.env")
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("OPENROUTER_API_KEY="):
                    k = line.split("=", 1)[1].strip().strip('"')
    if not k:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    return k


def panels(manifest: Path):
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not row.get("excluded"):
            yield row


def transcribe(img_path: Path, timeout: int = 120) -> str:
    mime = "image/png" if img_path.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(img_path.read_bytes()).decode()
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": [
        {"type": "text", "text": PROMPT},
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}]}]}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def split_confidence(raw: str):
    """Return (transcript_without_confidence_line, confidence_float)."""
    conf = 0.5
    lines = raw.splitlines()
    out = []
    for ln in lines:
        m = re.match(r"\s*CONFIDENCE:\s*([0-9.]+)", ln, re.I)
        if m:
            try:
                conf = max(0.0, min(1.0, float(m.group(1))))
            except ValueError:
                pass
            continue
        out.append(ln)
    return "\n".join(out).strip(), conf


def review(tdir: Path):
    idx = tdir / "_index.jsonl"
    rows = [json.loads(l) for l in idx.read_text(encoding="utf-8").splitlines() if l.strip()] if idx.exists() else []
    rows.sort(key=lambda r: r.get("confidence", 0))
    print(f"{len(rows)} panels transcribed — lowest confidence first (spot-check these):\n")
    for r in rows:
        flag = "  ← review" if r.get("confidence", 1) < 0.6 else ""
        print(f"  [{r.get('confidence', 0):.2f}] {r['base']}{flag}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--review", action="store_true")
    args = ap.parse_args(argv)

    dataset = args.manifest.parent
    tdir = dataset / "transcripts"
    if args.review:
        review(tdir)
        return 0

    tdir.mkdir(parents=True, exist_ok=True)
    rows = list(panels(args.manifest))
    todo = [r for r in rows if not (tdir / (Path(r["file_name"]).stem + ".txt")).exists()]
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(rows)} panels total, {len(todo)} to transcribe (model={MODEL})")

    if args.dry_run:
        print("\n[DRY RUN] first panel:", todo[0]["file_name"] if todo else "(none)")
        print("[PROMPT]\n" + PROMPT)
        return 0

    ok = fail = 0
    for r in todo:
        base = Path(r["file_name"]).stem
        img = dataset / r["file_name"]
        try:
            text, conf = split_confidence(transcribe(img))
            (tdir / f"{base}.txt").write_text(text + "\n", encoding="utf-8")
            with (tdir / "_index.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps({"base": base, "confidence": conf}) + "\n")
            ok += 1
            print(f"  ✓ {base}  conf={conf:.2f}")
        except Exception as e:
            fail += 1
            print(f"  ✗ {base}: {e}", file=sys.stderr)
    print(f"\ndone: {ok} transcribed, {fail} failed -> {tdir}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
