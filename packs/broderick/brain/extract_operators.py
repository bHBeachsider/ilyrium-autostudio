#!/usr/bin/env python3
"""extract_operators.py — reverse-engineer Broderick's comedic OPERATOR from finished strips.

Groups the panel manifest by `strip`, orders panels by `scene_numbers`, asks an OPEN-WEIGHT teacher
(DeepSeek via OpenRouter) to fill operator_schema.json per strip, validates, and appends to
data/broderick_operators.jsonl. Resumable (skips strips already extracted).

In-panel TEXT: if a transcript sidecar exists at <dataset>/transcripts/<panel-base>.txt it is fed
to the teacher alongside the visual caption (see TRANSCRIPTION_SPEC.md). Without it, the teacher
reads staging only and is told to lower confidence.

Usage:
  python extract_operators.py --manifest <dataset_v0/manifest.jsonl> [--limit N]
  python extract_operators.py --manifest ... --dry-run        # print the prompt for 1 strip, no API
  python extract_operators.py --review                        # list extracted strips, lowest-confidence first

Env: OPENROUTER_API_KEY (live runs only). BRODERICK_TEACHER overrides the model (default deepseek/deepseek-chat).
"""
import argparse
import json
import os
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = json.loads((HERE / "operator_schema.json").read_text(encoding="utf-8"))
OUT = HERE / "data" / "broderick_operators.jsonl"
MODEL = os.environ.get("BRODERICK_TEACHER", "deepseek/deepseek-chat")

SYSTEM = """You are a comedy analyst reverse-engineering the comedic GRAMMAR of the cartoonist \
"Broderick" from his finished strips. Your job is NOT to describe pictures — it is to recover the \
transferable OPERATOR that generates his comedy, so that operator can later produce NEW strips on \
NEW subjects.

Broderick's known voice (use as a lens; let the strip override it where they conflict):
- An iconoclastic satirical sledgehammer aimed at banal social conventions and pompous personality \
types — e.g. a stoner music critic delivering overwrought pseudo-intellectual analysis of a \
forgettable record.
- The engine: take something banal, inflate it with ridiculous complexity and UNWAVERING, MISPLACED \
CONFIDENCE — he is never wrong, he just escalates — then (often) puncture the grandiosity on \
something trivial. Delivery is deadpan and flat.
- The joke usually lives in the GAP between the banality of the subject and the grandiosity of the \
treatment.

Rules:
1. Extract the MECHANISM, not the surface. The operator must be general enough to re-run on a \
different subject.
2. Separate TARGET from VEHICLE. The pompous critic is the vehicle; the target may be pretension \
itself, the trivial thing he over-analyzes, or the convention he violates. Name both.
3. Write `premise` as a NEUTRAL seed — the setup a writer would start from — NOT the punchline.
4. Do NOT sanitize, soften, or moralize the satire. A defanged reading is a wrong reading.
5. Be honest about uncertainty. If the verbal content isn't available and you're inferring the joke \
from staging alone, LOWER `confidence` and say what's missing in `ambiguity_notes`. Never invent.
6. Output ONLY one JSON object conforming exactly to the schema. No prose, no markdown fences."""

USER_TMPL = """SCHEMA (your output must validate against this):
{schema}

STRIP: {strip_id}   —   {panel_count} panel(s), in order:

{panels}

Return the JSON operator object for this strip and nothing else."""


def load_strips(manifest_path: Path) -> dict:
    """Group non-excluded rows by `strip`, ordered by first scene number then filename."""
    groups = defaultdict(list)
    with manifest_path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row.get("excluded"):
                continue
            groups[row.get("strip") or row["file_name"]].append(row)
    for sid in groups:
        groups[sid].sort(key=lambda r: ((r.get("scene_numbers") or [0])[0], r["file_name"]))
    return groups


def panel_text(row: dict, dataset_dir: Path) -> str:
    """Visual caption + transcribed in-panel text if a sidecar exists."""
    base = Path(row["file_name"]).stem
    text = row.get("caption", "").strip()
    tx = dataset_dir / "transcripts" / f"{base}.txt"
    if tx.exists():
        t = tx.read_text(encoding="utf-8").strip()
        if t:
            text += f"\nIN-PANEL TEXT (transcribed): {t}"
    return text


def build_user(strip_id: str, panels: list, dataset_dir: Path) -> str:
    blocks = []
    for i, row in enumerate(panels, 1):
        scenes = row.get("scene_numbers") or []
        blocks.append(f"--- Panel {i} (scene {scenes}) ---\n{panel_text(row, dataset_dir)}\n")
    return USER_TMPL.format(schema=json.dumps(SCHEMA), strip_id=strip_id,
                            panel_count=len(panels), panels="\n".join(blocks))


def call_teacher(user: str, timeout: int = 120) -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set (needed for live extraction)")
    body = json.dumps({"model": MODEL, "messages": [
        {"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def parse_and_validate(raw: str) -> dict:
    if "{" not in raw or "}" not in raw:
        raise ValueError("no JSON object in teacher output")
    blob = raw[raw.find("{"):raw.rfind("}") + 1]
    try:
        obj = json.loads(blob)
    except json.JSONDecodeError:
        import ast  # tolerate python-dict (single-quote) output from the teacher
        obj = ast.literal_eval(blob)
    try:
        import jsonschema
        jsonschema.validate(obj, SCHEMA)
    except ImportError:
        req = SCHEMA["required"] + ["target", "inflation_mechanism", "comedic_thesis"]
        flat = {**obj, **obj.get("comedic_operator", {})}
        missing = [k for k in req if k not in flat]
        if missing:
            raise ValueError(f"missing required keys (jsonschema not installed): {missing}")
    return obj


def done_strips() -> set:
    if not OUT.exists():
        return set()
    return {json.loads(l)["strip_id"] for l in OUT.read_text(encoding="utf-8").splitlines() if l.strip()}


def review():
    rows = [json.loads(l) for l in OUT.read_text(encoding="utf-8").splitlines() if l.strip()] if OUT.exists() else []
    rows.sort(key=lambda r: r.get("confidence", 0))
    print(f"{len(rows)} operators extracted — lowest-confidence first (review these):\n")
    for r in rows:
        print(f"  [{r.get('confidence', 0):.2f}] {r['strip_id']}: {r.get('comedic_operator', {}).get('comedic_thesis', '')}")
        if r.get("ambiguity_notes"):
            print(f"         ↳ {r['ambiguity_notes']}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true", help="print the prompt for the first strip, no API call")
    ap.add_argument("--review", action="store_true", help="list extracted operators, lowest confidence first")
    args = ap.parse_args(argv)

    if args.review:
        review()
        return 0
    if not args.manifest:
        ap.error("--manifest is required (except for --review)")

    dataset_dir = args.manifest.parent
    strips = load_strips(args.manifest)
    todo = [s for s in strips if s not in done_strips()]
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(strips)} strips total, {len(todo)} to extract")

    if args.dry_run:
        if todo:
            print("\n===== DRY RUN: prompt for first strip =====\n")
            print("[SYSTEM]\n" + SYSTEM + "\n\n[USER]\n" + build_user(todo[0], strips[todo[0]], dataset_dir))
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    ok = fail = 0
    for sid in todo:
        try:
            obj = parse_and_validate(call_teacher(build_user(sid, strips[sid], dataset_dir)))
            obj["strip_id"] = sid  # authoritative
            with OUT.open("a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            ok += 1
            print(f"  ✓ {sid}  conf={obj.get('confidence', '?')}")
        except Exception as e:
            fail += 1
            print(f"  ✗ {sid}: {e}", file=sys.stderr)
    print(f"\ndone: {ok} extracted, {fail} failed -> {OUT}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
