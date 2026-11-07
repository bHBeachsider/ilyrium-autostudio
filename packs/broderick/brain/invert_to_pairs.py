#!/usr/bin/env python3
"""invert_to_pairs.py — turn extracted operators into `premise -> comic` training pairs.

Joins data/broderick_operators.jsonl (the reverse-engineered comedic grammar) with the manifest
(whose per-panel captions ARE brdrck-style image-prompts), and emits the foundry's messages-JSONL
chat format: {"messages":[system, user(premise), assistant(comic JSON)]}.

Output -> data/broderick_brain_pairs.jsonl  (feed to src/prepare.py to split train/val/test).

Usage:
  python invert_to_pairs.py --manifest <dataset_v0/manifest.jsonl>
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OPS = HERE / "data" / "broderick_operators.jsonl"
OUT = HERE / "data" / "broderick_brain_pairs.jsonl"

SYSTEM = (
    "You are Broderick, an iconoclastic satirical cartoonist. Given a premise, respond with ONLY a "
    "JSON comic breakdown of the strip you would draw: "
    "{\"format\": \"single_panel\"|\"strip\", \"comedic_thesis\": str, "
    "\"panels\": [{\"beat\": str, \"content\": str, \"dialogue\": str|null, \"image_prompt\": str}]}. "
    "Your engine: take something banal and inflate it with ridiculous complexity and UNWAVERING, "
    "MISPLACED CONFIDENCE — never wrong, just escalating — deadpan, then puncture the grandiosity. "
    "Each image_prompt is in your grayscale scratchy-ink 'brdrck style'."
)


def manifest_panels(manifest: Path) -> dict:
    groups = defaultdict(list)
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not row.get("excluded"):
            groups[row.get("strip") or row["file_name"]].append(row)
    for sid in groups:
        groups[sid].sort(key=lambda r: ((r.get("scene_numbers") or [0])[0], r["file_name"]))
    return groups


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    args = ap.parse_args(argv)

    if not OPS.exists():
        ap.error(f"{OPS} not found — run extract_operators.py first")
    panels = manifest_panels(args.manifest)
    ops = [json.loads(l) for l in OPS.read_text(encoding="utf-8").splitlines() if l.strip()]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for op in ops:
            sid = op["strip_id"]
            beats = op.get("panel_beats", [])
            caps = panels.get(sid, [])
            comic_panels = []
            for i, b in enumerate(beats):
                img = caps[i].get("caption", "") if i < len(caps) else ""
                comic_panels.append({
                    "beat": b.get("beat"),
                    "content": b.get("content"),
                    "dialogue": b.get("dialogue"),
                    "image_prompt": img,
                })
            comic = {
                "format": op.get("format", "strip"),
                "comedic_thesis": op.get("comedic_operator", {}).get("comedic_thesis", ""),
                "panels": comic_panels,
            }
            user = f"Premise: {op.get('premise','').strip()}\nFormat: {op.get('format','strip')}"
            f.write(json.dumps({"messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user},
                {"role": "assistant", "content": json.dumps(comic, ensure_ascii=False)},
            ]}, ensure_ascii=False) + "\n")
            written += 1
    print(f"wrote {written} premise->comic pairs -> {OUT}")
    print("next: python ../../../src/prepare.py --in", OUT, "--out", HERE / "data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
