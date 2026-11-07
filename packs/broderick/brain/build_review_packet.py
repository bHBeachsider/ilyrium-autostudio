#!/usr/bin/env python3
"""build_review_packet.py — generate Broderick's two-pass review doc (no GPU).

Pass 1: low-confidence transcripts (spot-check). Pass 2: low-confidence operators (confirm/correct).
Pulls the actual transcripts + operators so each item has full context + a fill-in slot. His answers
feed back: transcript fixes -> the .txt sidecars; operator fixes -> broderick_operators.jsonl;
then re-invert + augment from the corrected set.

Usage: python build_review_packet.py --transcripts <dataset_v0/transcripts> [--out BRODERICK_REVIEW.md]
       [--tx-threshold 0.6] [--op-threshold 0.95]
"""
import argparse
import glob
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
OPS = HERE / "data" / "broderick_operators.jsonl"


def strip_transcripts(tdir: Path, strip_id: str, max_panels=8) -> str:
    out = []
    for fp in sorted(glob.glob(str(tdir / f"{strip_id}__*.txt")))[:max_panels]:
        body = Path(fp).read_text(encoding="utf-8").strip().replace("\n", " / ")
        out.append(f"  - **{Path(fp).stem.split('__')[-1]}:** {body[:240]}")
    return "\n".join(out) or "  - (no transcripts found)"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcripts", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=HERE / "BRODERICK_REVIEW.md")
    ap.add_argument("--tx-threshold", type=float, default=0.6)
    ap.add_argument("--op-threshold", type=float, default=0.95)
    ap.add_argument("--priority-threshold", type=float, default=0.85)
    args = ap.parse_args(argv)

    idx = args.transcripts / "_index.jsonl"
    tx = [json.loads(l) for l in idx.read_text(encoding="utf-8").splitlines() if l.strip()] if idx.exists() else []
    low_tx = sorted([r for r in tx if r["confidence"] < args.tx_threshold], key=lambda r: r["confidence"])

    ops = [json.loads(l) for l in OPS.read_text(encoding="utf-8").splitlines() if l.strip()]
    low_ops = sorted([o for o in ops if o.get("confidence", 1) < args.op_threshold], key=lambda o: o["confidence"])

    L = []
    L.append("# Broderick — Review Packet (v0 Brain dataset)\n")
    L.append("Two quick passes. Your answers feed straight back into the dataset; then we generate "
             "~300 new in-voice scripts from your *corrected* operators and train the Brain.\n")
    L.append("**How to use:** for each item, tick a box / write the fix in the **▶ YOUR CALL** slot, "
             "then hand it back. I apply every correction, then run augmentation.\n")
    L.append("\n---\n")
    L.append("## Why you're only seeing a handful of items\n")
    L.append("Every one of your **190 panels and 30 strips was processed automatically** — the AI "
             "transcribed the in-panel text and reverse-engineered the comedic *operator* (the engine) "
             "of each strip. It also **scores its own confidence** on every read, and this packet "
             "surfaces only the ones it was *least* sure about — so your time lands exactly where the "
             "machine is weakest. The 1 transcript + 1 priority operator below are the genuinely "
             "uncertain reads; the 22 'optional' ones are solid (skim if you like); the other 7 strips "
             "came back clean and need nothing.\n")
    L.append("## What your answers are used for\n")
    L.append("Your corrections get written back into the dataset, which then (1) **generates ~300 "
             "brand-new comic scripts in your voice** by applying *your* operators to fresh subjects, "
             "and (2) **trains a small language model — the 'Broderick Brain' —** that writes new "
             "comics the way you do. The machine captured the *patterns*; only you know which readings "
             "are *actually you*. So these few corrections disproportionately shape everything "
             "downstream — this is the step where your taste gets encoded.\n")
    L.append("\n---\n")

    L.append(f"## PASS 1 — Transcript spot-check ({len(low_tx)} panel)\n")
    L.append("The vision model read the in-panel text on all 190 panels; only these came back "
             "low-confidence. Confirm the text is right.\n")
    for r in low_tx:
        body = (args.transcripts / f"{r['base']}.txt").read_text(encoding="utf-8").strip()
        L.append(f"### {r['base']}  (confidence {r['confidence']:.2f})\n")
        L.append("**It transcribed:**\n")
        L.append("```\n" + body + "\n```\n")
        L.append("**▶ YOUR CALL:**  [ ] Correct as-is   [ ] Wrong → real text:\n\n> \n")
        L.append("")

    priority = [o for o in low_ops if o.get("confidence", 1) < args.priority_threshold]
    optional = [o for o in low_ops if args.priority_threshold <= o.get("confidence", 1) < args.op_threshold]

    L.append("\n---\n")
    L.append("## PASS 2 — Operator review\n")
    L.append(f"The teacher reverse-engineered your comedic *operator* (the reusable engine) for each "
             f"strip. **Required: {len(priority)}.** Optional skim: {len(optional)}. "
             f"({len(ops) - len(low_ops)} came back clean.) This is where your tacit 'why' gets locked in.\n")

    L.append(f"### 2A · Please review — {len(priority)} (lowest confidence)\n")
    for i, o in enumerate(priority, 1):
        op = o["comedic_operator"]
        L.append(f"#### {i}. {o['strip_id']}  (confidence {o.get('confidence',0):.2f})\n")
        L.append(f"**Premise (the neutral seed):** {o.get('premise','')}\n")
        L.append("**Operator the teacher inferred:**\n")
        for k in ["target", "vehicle_persona", "inflation_mechanism", "escalation_arc", "register", "puncture", "comedic_thesis"]:
            L.append(f"- *{k}:* {op.get(k)}")
        L.append("\n**What the strip actually says:**\n")
        L.append(strip_transcripts(args.transcripts, o["strip_id"]))
        L.append(f"\n**The specific question:** {o.get('ambiguity_notes') or '(none — just confirm it reads right)'}\n")
        L.append("**▶ YOUR CALL:**  [ ] Operator is right   [ ] Fix it:\n\n> \n")
        L.append("*(answer to the question above):*\n\n> \n")
        L.append("")

    L.append(f"### 2B · Optional confirm — {len(optional)} (solid; minor noted ambiguity — skim & tick)\n")
    for o in optional:
        op = o["comedic_operator"]
        L.append(f"- **{o['strip_id']}** ({o.get('confidence',0):.2f}) — *{op.get('comedic_thesis','')}*")
        if o.get("ambiguity_notes"):
            L.append(f"  - ❓ {o['ambiguity_notes']}")
        L.append("  - ▶ [ ] fine   [ ] fix: ____________")

    L.append("\n---\n")
    L.append("## What happens with your answers\n")
    L.append("1. I apply transcript fixes to the `.txt` sidecars + operator fixes to "
             "`broderick_operators.jsonl`.\n2. Re-run the inverter (corrected gold pairs).\n"
             "3. Run the augmenter from the **corrected** operators → ~300 in-voice scripts.\n"
             "4. (GPU) QLoRA-train `broderick-brain`.\n")

    L.append("\n---\n")
    L.append("## Optional but high-value — things only you can give us\n")
    L.append("The reverse-engineering gives a competent v0, but these inputs sharpen the voice from "
             "*plausibly* Broderick to *unmistakably* Broderick. Add whatever you have time for — "
             "**#1 and #3 are the two biggest levers if you only do two.**\n")
    L.append("1. **A few premise → joke examples in your own words.** Take 3–5 everyday situations and "
             "write how *you'd* turn each into a bit — the actual move, not just the finished strip. "
             "This teaches your *generative* logic, which finished art alone can't show.")
    L.append("2. **Your recurring targets & characters.** Who/what do you skewer again and again — "
             "personality types, institutions, the author-avatar, named characters? A roster guides "
             "both the writing and the character art.")
    L.append("3. **Your 'greatest hits.'** Point to 5–10 strips that are the *most you*. These become "
             "the gold standard your generated output is judged against.")
    L.append("4. **Anti-examples — what is NOT you.** Describe a version of your comedy that would feel "
             "like a bad imitation (too cute? too explained? wrong target?). What to *avoid* is as "
             "valuable as what to do.")
    L.append("5. **The 'why,' in your words (even partial).** When a bit lands, what's the mechanism? "
             "(e.g. 'it's not the complexity — it's the misplaced confidence.') Any articulation helps "
             "lock in the operator.")
    L.append("6. **Targets you WANT skewered.** A list of subjects ripe for your treatment — these seed "
             "the 300 new scripts directly.")
    L.append("7. **The canonical 'you' (for the character art).** A reference of the recurring "
             "protagonist — a drawing, or just confirm 'bald, full beard, thick black glasses, "
             "heavyset' — anchors the character-consistency model.")
    L.append("8. **Lettering & format preferences.** A favorite hand-lettering face, and whether you "
             "lean single-panel / 3-panel / longer — tunes the layout + lettering of the finished strips.\n")
    L.append("Drop answers inline here, in a separate note, or just talk it through — any form works.\n")

    args.out.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote review packet: {args.out}  ({len(low_tx)} transcript + {len(low_ops)} operator items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
