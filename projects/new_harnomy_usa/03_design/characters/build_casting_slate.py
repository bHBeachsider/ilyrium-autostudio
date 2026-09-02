"""
build_casting_slate - the Stage-3 CASTING SLATE generator.

Emits six candidate prompts per principal (24 total) so Brad can pick a face.
This is the *casting set*, not the training set - see LOOK_DEVELOPMENT_PLAN.md §0:

  casting set   -> lighting HELD CONSTANT within a character, so candidates
                   differ by face and nothing else. Judged by a human.
  training set  -> lighting deliberately VARIED, so the LoRA learns the face
                   rather than one key light. Generated later, from the winner.

Why this is not build_anchor_manifest.py
----------------------------------------
The bibles' LOCKED VISUAL DESCRIPTORs still carry provisional specifics -
Summer's "dark hair drawn back", Pengold's "greying at the temples", Dick's
"thin wire-frame glasses". Those are exactly the choices Stage 3 exists to make,
and the anchor manifest bakes them in. So each character here is split:

  CANON_CORE - what v11 and the kernel fix. Present in all six candidates.
  VARIANTS   - the open axes. The only thing that changes between candidates.

After Brad picks, the winning variant text is folded back into the bible's
LOCKED VISUAL DESCRIPTOR (step 3.7) and build_anchor_manifest.py regenerates
the anchors from the decided face.

    python build_casting_slate.py                  # write CASTING_SLATE.json + .md
    python build_casting_slate.py --print valencia # read one character's six

LEGAL: age, origin, build, wardrobe and affect only. Never a likeness to a real
person - the negatives carry an explicit likeness guard on top of the kernel's.

Pure stdlib. No network, no spend. Writes prompts; renders nothing.
"""

import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
KERNEL = os.path.join(PROJECT, "style_kernel.json")
OUT_JSON = os.path.join(HERE, "casting", "CASTING_SLATE.json")
OUT_MD = os.path.join(HERE, "casting", "CASTING_SLATE.md")

# Identical for all 24 - a casting portrait, not a shot. Comparability is the
# whole point: same framing, same distance, same non-performance.
FRAMING = (
    "medium close-up from the chest, straight-on to camera, plain neutral "
    "background, even exposure, the face at rest and not performing, no smile, "
    "no eyebrow lift, no dramatic gesture"
)
ASPECT = "3:2"

# On top of the kernel negatives. The kernel has no likeness clause; casting needs one.
LIKENESS_GUARD = (
    "resemblance to any real or famous person, celebrity likeness, recognizable "
    "public figure, portrait of a known actor"
)

CHARACTERS = {
    "valencia": {
        "order": 1,
        "role": "Mezzo. The Greek chorus. The only character who tells the truth.",
        # Her canon lighting differs from the others by design (v11: "photographed
        # truthfully"). Held constant across HER six.
        "lighting": "flat honest documentary light, no sculpting, no glamour",
        "canon_core": (
            "a sturdy grounded woman in her late forties, direct steady eyes, a "
            "weathered capable face with no makeup performance, real practical work "
            "clothes in plain worn fabrics that have been worn more than once this "
            "week, working hands, photographed truthfully"
        ),
        "test_question": "Does she read as staff, or as cast?",
        "trap": "Every model drifts toward attractive. If she reads as an actress playing working-class, the opera loses its one honest voice.",
        "variants": [
            "cropped practical grey-streaked hair, solid heavy-set build, broad face",
            "dark hair going grey tied back plainly, wiry lean build, angular lined face",
            "short salt-and-pepper hair, solid build, angular face with a strong jaw",
            "greying hair in a loose worn-in bun, wiry build, broad open face",
            "close-cropped fully grey hair, heavy solid build, broad face",
            "dark hair pulled back tight, medium build, long angular deeply lined face",
        ],
    },
    "summer": {
        "order": 2,
        "role": "Soprano. The moral center. The hardest identity problem in the film.",
        "lighting": "single-source tungsten key, soft falloff",
        "canon_core": (
            "a poised woman in her early forties, patrician bearing, composed "
            "watchful eyes, slim upright frame, professional-class activist tailoring "
            "in muted expensive fabrics, no jewellery beyond the minimal, still hands, "
            "sincere unsmiling composure"
        ),
        "test_question": "Can this face be glorified in a Socialist-Realist portrait AND freeze in horror beneath it?",
        "trap": "Too cold cannot be idealized. Too warm cannot freeze.",
        "variants": [
            "dark hair drawn back with professional precision, narrow face, cool remote affect",
            "ash-blonde hair in a low chignon, narrow face, cool neutral affect",
            "chestnut hair at the shoulder tucked behind one ear, medium-width face, warmer affect",
            "dark hair with early silver drawn back severely, narrow face, markedly cool affect",
            "light brown hair in a sleek jaw-length bob, medium-width face, neutral affect",
            "dark auburn hair gathered low, broader face with fuller cheekbones, warm affect",
        ],
    },
    "pengold": {
        "order": 3,
        "role": "Baritone. The machine. Carries two of the three load-bearing silences.",
        "lighting": "single-source tungsten key, soft falloff",
        "canon_core": (
            "a controlled man in his late forties, calculating unhurried eyes, "
            "municipal mayoral suiting in dark muted wool, white shirt, no "
            "ostentation, unhurried processional bearing"
        ),
        "test_question": "Is the face readable at rest? He opens on 22 seconds of silence and closes on the smallest possible smile.",
        "trap": "Casting him smooth. His character is a working-class origin showing through acquired polish - the face should look constructed, slightly effortful.",
        "variants": [
            "heavy-set thickening build, receding hairline, the acquired polish sitting visibly uneasily",
            "solid but not fat, full hair greying at the temples, the polish worn easily and well",
            "thickening through the neck and jaw, high forehead and thinning crown, visibly effortful composure",
            "burly broad-shouldered build, close-cropped receding hair, the tailoring not quite fitting the man",
            "medium build, dark hair combed back neatly, smooth surface with watchfulness underneath",
            "heavy jaw and thick neck, a thinning widow's peak, the whole presentation obviously constructed",
        ],
    },
    "dick": {
        "order": 4,
        "role": "Tenor. The sacrifice. His fall must land as pathos.",
        "lighting": "single-source tungsten key, soft falloff",
        "canon_core": (
            "a lean charismatic man, earnest alive expression, dark raw selvedge "
            "denim, a tailored heritage workwear jacket over a faded vintage band "
            "t-shirt, a handwoven scarf, an expensive-looking effortless \"worker\" "
            "aesthetic, sincere passionate bearing, softness in the face of someone "
            "who has never had to be hard"
        ),
        "test_question": "Does the audience want to see him arrested? If yes, the ending does not work.",
        "trap": "Making him punchable. 'Little Dickie' was called soft by his family and must look it.",
        "variants": [
            "reads late twenties, collar-length grown-out hair, thin wire-frame glasses",
            "reads mid thirties, shoulder-length hair tucked behind the ears, no glasses",
            "reads early thirties, chin-length wavy hair, thin wire-frame glasses",
            "reads late twenties, shorter grown-out hair just past the ears, no glasses",
            "reads mid thirties, long loose hair, thin wire-frame glasses",
            "reads early thirties, collar-length hair pushed back off the forehead, no glasses",
        ],
    },
}

# Deterministic seeds so any single candidate can be re-rolled identically.
SEED_BASE = {"valencia": 310000, "summer": 320000, "pengold": 330000, "dick": 340000}


def build(kernel):
    look = kernel["look"]
    register = kernel["register"]
    negatives = kernel["negatives"] + ", " + LIKENESS_GUARD

    entries = []
    for key, c in sorted(CHARACTERS.items(), key=lambda kv: kv[1]["order"]):
        for i, variant in enumerate(c["variants"], start=1):
            entries.append({
                "character": key,
                "candidate": i,
                "candidate_id": "%s-C%02d" % (key.upper()[:3], i),
                "output": "casting/%s/%s_c%02d.png" % (key, key, i),
                "seed": SEED_BASE[key] + i,
                "aspect_ratio": ASPECT,
                "varied_axis": variant,
                "prompt": ", ".join([
                    c["canon_core"], variant, FRAMING, c["lighting"], look, register,
                ]),
                "negative_prompt": negatives,
            })

    return {
        "$comment": (
            "Stage-3 CASTING SLATE for NEW HARNOMY, U.S.A. Six candidates per "
            "principal. Lighting is held constant WITHIN each character so that "
            "candidates differ by face alone. Generated by build_casting_slate.py; "
            "regenerate after any kernel change."),
        "project": "new_harnomy_usa",
        "stage": "03_design/characters — step 3.2",
        "framing_constant": FRAMING,
        "aspect_ratio": ASPECT,
        "legal_rule": kernel.get("legal_rule", ""),
        "how_to_judge": [
            "Compare within a character only. The six differ by face, not by light.",
            "Read each character's test_question below before looking.",
            "Reject anything resembling a real person (step 3.3) BEFORE choosing.",
            "After picking four, run the silhouette test: all four at 40px, value only.",
            "Summer's pick must also pass the portrait test before it locks.",
        ],
        "characters": {
            k: {
                "order": c["order"], "role": c["role"],
                "test_question": c["test_question"], "trap": c["trap"],
                "lighting": c["lighting"], "canon_core": c["canon_core"],
            } for k, c in CHARACTERS.items()
        },
        "counts": {"characters": len(CHARACTERS), "candidates": len(entries)},
        "entries": entries,
    }


def to_markdown(m):
    L = ["# CASTING SLATE — NEW HARNOMY, U.S.A.", ""]
    L.append("*Step 3.2. Six candidates per principal, 24 total. Copy any block into "
             "Higgsfield / ComfyUI / fal. Lighting is constant within a character — "
             "the candidates differ by face.*")
    L.append("")
    L.append("**Framing (identical for all 24):** " + m["framing_constant"])
    L.append("")
    L.append("**Aspect:** " + m["aspect_ratio"] + "  ·  **Negatives:** identical for all 24, see the JSON.")
    L.append("")
    L.append("## How to judge")
    for h in m["how_to_judge"]:
        L.append("- " + h)
    L.append("")

    order = sorted(m["characters"].items(), key=lambda kv: kv[1]["order"])
    for key, c in order:
        L.append("---")
        L.append("")
        L.append("## %d. %s" % (c["order"], key.upper()))
        L.append("")
        L.append("*%s*" % c["role"])
        L.append("")
        L.append("**Ask:** %s" % c["test_question"])
        L.append("")
        L.append("**Trap:** %s" % c["trap"])
        L.append("")
        for e in m["entries"]:
            if e["character"] != key:
                continue
            L.append("### %s — %s" % (e["candidate_id"], e["varied_axis"]))
            L.append("")
            L.append("`seed %d`" % e["seed"])
            L.append("")
            L.append("```")
            L.append(e["prompt"])
            L.append("```")
            L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", dest="who", default=None)
    args = ap.parse_args()

    with open(KERNEL, encoding="utf-8") as fh:
        kernel = json.load(fh)
    m = build(kernel)

    if args.who:
        c = m["characters"][args.who]
        print("\n%s — %s\nASK: %s\n" % (args.who.upper(), c["role"], c["test_question"]))
        for e in m["entries"]:
            if e["character"] == args.who:
                print("[%s] seed %d\n%s\n" % (e["candidate_id"], e["seed"], e["prompt"]))
        return

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=2)
        fh.write("\n")
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(to_markdown(m))
        fh.write("\n")
    print("[OK] %s" % OUT_JSON)
    print("[OK] %s" % OUT_MD)
    print("     %d candidates across %d principals"
          % (m["counts"]["candidates"], m["counts"]["characters"]))


if __name__ == "__main__":
    main()
