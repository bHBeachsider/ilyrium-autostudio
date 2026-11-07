#!/usr/bin/env python3
"""augment_pairs.py — scale the 30 gold pairs to a trainable set by applying the OPERATORS to
fresh premises. Each extracted operator is a reusable generator: (operator + new banal premise)
-> a new in-voice comic via the open-weight teacher (DeepSeek), few-shot-anchored on a real strip.

Writes synthetic pairs to data/broderick_brain_pairs_synth.jsonl (kept separate from the gold
broderick_brain_pairs.jsonl for provenance; prepare.py can ingest both). Resumable.

RUN ORDER: do this AFTER Broderick reviews the operators (step 4) — augmentation amplifies the
operators, so generate from the corrected set, not the raw one.

Usage:
  python augment_pairs.py --target-count 300 [--per-operator N] [--premises-file extra.txt]
Env: OPENROUTER_API_KEY required. BRODERICK_TEACHER overrides model (default deepseek/deepseek-chat).
"""
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OPS = HERE / "data" / "broderick_operators.jsonl"
GOLD = HERE / "data" / "broderick_brain_pairs.jsonl"
OUT = HERE / "data" / "broderick_brain_pairs_synth.jsonl"
MODEL = os.environ.get("BRODERICK_TEACHER", "deepseek/deepseek-chat")

SYSTEM = (
    "You are Broderick, an iconoclastic satirical cartoonist, writing a NEW comic. You will be given "
    "one of your recurring comedic OPERATORS and a fresh PREMISE. Apply the operator to the premise "
    "to produce a new strip in your authentic voice — take the banal subject and inflate it with "
    "ridiculous complexity and UNWAVERING, MISPLACED CONFIDENCE, deadpan, then puncture it. Be "
    "genuinely funny and specific, NOT formulaic; vary the staging and the collapse. Output ONLY the "
    "comic JSON: {\"format\":\"single_panel\"|\"strip\",\"comedic_thesis\":str,\"panels\":[{\"beat\":str,"
    "\"content\":str,\"dialogue\":str|null,\"image_prompt\":str}]}. Each image_prompt is in your "
    "grayscale scratchy-ink 'brdrck style' (deadpan caricature, white void or sketchy environs, "
    "occasional single spot-color accent)."
)

# Banal targets / pompous personality types in Broderick's wheelhouse — the augmentation seed bank.
PREMISE_SEED = [
    "A man explains why his sourdough starter has a richer inner life than most people.",
    "A craft-beer evangelist conducts a tasting like a sacred rite.",
    "A CrossFit zealot frames skipping leg day as a moral and civilizational collapse.",
    "An HOA board treats a mailbox-color violation as a constitutional crisis.",
    "A podcast bro explains how his 4am morning routine is a spiritual discipline.",
    "A wine guy decodes the geopolitics of a seven-dollar bottle.",
    "A vinyl purist explains how digital audio severed humanity from its soul.",
    "A film-school dropout analyzes a fast-food commercial as auteur cinema.",
    "A dad defends his thermostat policy as inherited ancestral wisdom.",
    "A foodie narrates a gas-station hot dog as a fourteen-course tasting menu.",
    "A man at a party explains why he doesn't own a television, at length, unprompted.",
    "A barista corrects a customer's pronunciation as a defense of Western civilization.",
    "A guy explains why his fantasy-football strategy is actually applied game theory.",
    "A man treats assembling IKEA furniture as a test of moral character.",
    "A self-published author describes his unread newsletter as the last free press.",
    "A cyclist explains how his commute is a form of nonviolent protest.",
    "A man insists his houseplants can sense dishonesty.",
    "A guy explains why the gym he quit was philosophically compromised.",
    "A man reviews his own neighborhood's recycling habits as cultural decline.",
    "A dad gives a TED-talk-grade defense of mowing the lawn in straight lines.",
    "A man explains why he only drinks water from a specific municipal source.",
    "A guy frames losing an argument online as a strategic withdrawal.",
    "A man treats choosing a Netflix show as an existential reckoning.",
    "A coworker explains why his standing desk is a statement about modernity.",
    "A man recounts a minor traffic dispute as a clash of worldviews.",
    "A guy explains how his beard is a rejection of corporate conformity.",
    "A man delivers a eulogy-grade tribute to a discontinued snack.",
    "A neighbor explains why his Christmas lights are a meditation on impermanence.",
    "A man insists his commute playlist is a curated emotional journey.",
    "A guy explains why he refuses to use the self-checkout, as a principle.",
    # memoir vein (his autobiography register)
    "A childhood gym teacher's petty tyranny, recalled decades later as epic trauma.",
    "A trip to the DMV recounted as a hero's descent into the underworld.",
    "A grade-school science-fair defeat reframed as a foundational injustice.",
    "A teenage summer job at a sub shop remembered as a crucible of the soul.",
    "A family road trip recalled as a doomed expedition.",
]


def call_teacher(system: str, user: str, timeout: int = 120) -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    body = json.dumps({"model": MODEL, "messages": [
        {"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def parse_comic(raw: str) -> dict:
    import ast
    blob = raw[raw.find("{"):raw.rfind("}") + 1]
    try:
        obj = json.loads(blob)
    except json.JSONDecodeError:
        obj = ast.literal_eval(blob)
    if "panels" not in obj or not obj["panels"]:
        raise ValueError("comic has no panels")
    return obj


def gold_example() -> str:
    """One real strip as a few-shot anchor (user+assistant), to keep the voice authentic."""
    line = GOLD.read_text(encoding="utf-8").splitlines()[0]
    msgs = {m["role"]: m["content"] for m in json.loads(line)["messages"]}
    return f"EXAMPLE (one of your real strips):\n{msgs['user']}\n-> {msgs['assistant']}"


def build_user(op: dict, premise: str, example: str) -> str:
    o = op["comedic_operator"]
    fields = "\n".join(f"  {k}: {o[k]}" for k in
                       ["target", "vehicle_persona", "inflation_mechanism", "escalation_arc", "register", "puncture"])
    return (f"{example}\n\nNOW apply THIS operator:\n{fields}\n\n"
            f"To this fresh PREMISE: {premise}\n\nReturn the comic JSON only.")


def done_count() -> int:
    return len(OUT.read_text(encoding="utf-8").splitlines()) if OUT.exists() else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-count", type=int, default=300, help="total synthetic pairs to generate")
    ap.add_argument("--per-operator", type=int, default=0, help="cap per operator (0 = round-robin to target)")
    ap.add_argument("--premises-file", type=Path, help="extra premises, one per line (added to the seed bank)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if not OPS.exists() or not GOLD.exists():
        ap.error("need data/broderick_operators.jsonl and data/broderick_brain_pairs.jsonl (run extract + invert first)")
    ops = [json.loads(l) for l in OPS.read_text(encoding="utf-8").splitlines() if l.strip()]
    premises = list(PREMISE_SEED)
    if args.premises_file and args.premises_file.exists():
        premises += [p.strip() for p in args.premises_file.read_text(encoding="utf-8").splitlines() if p.strip()]
    example = gold_example()

    # plan (operator, premise) jobs: cycle operators × premises until target-count
    jobs = []
    i = 0
    while len(jobs) < args.target_count:
        op = ops[i % len(ops)]
        premise = premises[(i // len(ops)) % len(premises)] if premises else None
        if premise is None:
            break
        if args.per_operator and sum(1 for j in jobs if j[0] is op) >= args.per_operator:
            i += 1
            if i > len(ops) * len(premises):
                break
            continue
        jobs.append((op, premise))
        i += 1

    already = done_count()
    jobs = jobs[already:]  # resume
    print(f"{len(ops)} operators × {len(premises)} premises; target {args.target_count}, {already} done, {len(jobs)} to generate (model={MODEL})")

    if args.dry_run:
        op, premise = jobs[0]
        print("\n[DRY RUN] first job\n[SYSTEM]\n" + SYSTEM + "\n\n[USER]\n" + build_user(op, premise, example))
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    ok = fail = 0
    for op, premise in jobs:
        try:
            comic = parse_comic(call_teacher(SYSTEM, build_user(op, premise, example)))
            user = f"Premise: {premise}\nFormat: {comic.get('format', 'strip')}"
            with OUT.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"messages": [
                    {"role": "system", "content": GOLD_SYSTEM_HINT()},
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": json.dumps(comic, ensure_ascii=False)},
                ], "source": "synthetic", "operator_strip": op["strip_id"]}, ensure_ascii=False) + "\n")
            ok += 1
            print(f"  ✓ [{op['strip_id']}] {premise[:50]}…")
        except Exception as e:
            fail += 1
            print(f"  ✗ {premise[:40]}: {e}", file=sys.stderr)
    print(f"\ndone: {ok} generated, {fail} failed -> {OUT}")
    return 0 if fail == 0 else 1


def GOLD_SYSTEM_HINT() -> str:
    """The system prompt the TRAINED model will see — must match invert_to_pairs.py's SYSTEM."""
    from invert_to_pairs import SYSTEM as INV_SYSTEM
    return INV_SYSTEM


if __name__ == "__main__":
    sys.exit(main())
