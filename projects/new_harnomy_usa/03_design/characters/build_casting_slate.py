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
#
# REVISED 2026-09-02 after the first slate came back unusable. Three fixes:
#   NH-USA-005 - naming a body part makes the model FEATURE it. "hands still"
#     produced prayer hands in 17 of 24 frames. Hands are now explicitly OUT.
#   NH-USA-006 - negations barely hold on an engine with no negative field
#     (soul_cinematic has none). Everything is phrased POSITIVELY now.
#   NH-USA-007 - the kernel grade buried every face in shadow. A casting still
#     is lit to REVEAL A FACE; the grade belongs on shots. See CASTING_LOOK.
FRAMING = (
    "head-and-shoulders portrait framed just below the collarbone, hands out of "
    "frame, straight-on to camera, plain unlit grey backdrop, mouth closed with "
    "the lips together, jaw relaxed, eyes steady on the lens, the expression "
    "completely neutral and still, blank unmarked clothing with no printed graphics"
)

# Replaces the kernel look for CASTING ONLY. Even, generous, revealing.
CASTING_LOOK = (
    "even neutral daylight-balanced exposure, soft frontal key, shadows open and "
    "detailed, natural skin tones, sharp focus on the eyes, photographic realism, "
    "documentary portrait, shot on a 85mm lens"
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
        # Her canon lighting REPLACES the kernel's Deakins tungsten clause rather than
        # sitting beside it - v11 photographs her truthfully while the others are lit.
        # See "look_strip" below.
        "lighting": "flat honest documentary light, no sculpting, no glamour",
        "look_strip": "Roger Deakins single-source tungsten lighting, ",
        # REVISED 2026-09-02 (Brad). Early twenties, not late forties. Hipster styling
        # worn as a uniform, not a belief. And the inversion that carries the whole
        # character: she has real working hands and WANTS them fixed. Calloused hands
        # are not a badge to her - they are a problem she cannot afford to solve.
        # Aspiration she cannot fund is the point; do not cast it away by making her
        # already beautiful. The gap is the character.
        # ETHNICALLY AMBIGUOUS BY DECISION (2026-09-02, Brad). Her POV is the
        # universal truth and must not reduce to a subject position - every other
        # principal reads the world through identity categories, and the one who
        # sees clearly is the one the Framework cannot sort. Name no region.
        # Her rough hands remain canon for SHOTS; they are out of the casting frame
        # per NH-USA-005.
        "canon_core": (
            "a young woman in her late twenties of deliberately ambiguous ethnicity - "
            "features that do not resolve to any one part of the world, warm mid-tone "
            "skin, dark eyes, dark hair at a practical length - slight build, a direct "
            "steady gaze that assesses before it answers, secondhand layering worn as a "
            "work uniform rather than a statement, a thrifted cardigan over a plain tee, "
            "small cheap jewellery, visibly assembled from what was affordable rather "
            "than curated at expense, grooming attempted on a budget"
        ),
        "test_question": "Do you believe she wants a manicure she cannot afford? The gap between what she is and what she wants to be IS the character.",
        "trap": "Two opposite failures. Cast her already beautiful and the wanting evaporates. Cast her as picturesque poverty and she becomes the working-class cosplay the opera is attacking. She is neither: she is a young woman with real calluses who would fix them tomorrow if she had the money.",
        "variants": [
            "sharp features, hair in a plain low ponytail, minimal makeup applied with obvious care",
            "softer rounder face, black hair cut blunt at the shoulder by her own hand, one small gold hoop - the only jewellery she owns",
            "angular face with a strong nose, hair scraped back flat, no makeup at all, faint shadows under the eyes",
            "wide-set eyes and a plain unremarkable face, hair in a practical bun, drugstore lipstick the only colour on her",
            "long face with heavy dark brows, hair loose and practical, careful eyeliner that took time she does not have",
            "delicate features undercut by tiredness, hair pinned back off the face, cheap black dye growing out at the roots",
        ],
    },
    "summer": {
        "order": 2,
        "role": "Soprano. The moral center. The hardest identity problem in the film.",
        "lighting": "single-source tungsten key, soft falloff",
        # REVIEWED 2026-09-02. Old core said "composed" three ways and never said what
        # is underneath; "professional-class activist tailoring" is unrenderable, so it
        # is now described. The axis changed too: hair colour is not the interesting
        # variable - how much the composure is HOLDING is.
        "canon_core": (
            "a woman in her early forties, patrician bearing, slim and upright, a "
            "well-cut dark blazer over a fine plain knit in expensive unpatterned "
            "fabric, no logo, one minimal earring and nothing else, composure that is "
            "visibly maintained rather than natural, a stillness that is holding "
            "something down"
        ),
        "test_question": "Can this face be glorified in a Socialist-Realist portrait AND freeze in horror beneath it? Too cold cannot be idealized; too warm cannot freeze.",
        "trap": "She is Valencia's mirror. Valencia wants something she cannot afford; Summer has bought something she cannot return - she runs a reproductive-justice organization and had herself sterilized, and the Act III portrait glorifies her as a mother of the movement. None of that renders directly. What renders is that her stillness COSTS her something. A merely serene face has not understood the part.",
        "variants": [
            "dark hair drawn back with professional precision, narrow face, composure entirely intact, nothing showing at all",
            "ash-blonde hair in a low chignon, narrow face, composure intact but the jaw faintly set",
            "chestnut hair at the shoulder tucked behind one ear, medium-width face, warmth still surviving underneath the control",
            "dark hair with early silver drawn back severely, narrow face, sleeplessness under the eyes she has not bothered to conceal",
            "light brown hair in a sleek jaw-length bob, medium-width face, a decade of donor-room smile lines with no smile in them now",
            "dark auburn hair gathered low, broader face with fuller cheekbones, the composure very slightly slipped at the mouth",
        ],
    },
    "pengold": {
        "order": 3,
        "role": "Baritone. The machine. Carries two of the three load-bearing silences.",
        "lighting": "single-source tungsten key, soft falloff",
        # REVIEWED 2026-09-02. "calculating" was producing the villain squint the trap
        # warns against - replaced with the watcher note (v11: the intern who sat front
        # row and took notes). "no ostentation" was a negative instruction inside a
        # positive prompt; restated positively. Added the two class tells that actually
        # render: the hands, and grooming a shade too correct.
        "canon_core": (
            "a man in his late forties, eyes that have been listening a long time, "
            "plain correct unshowy municipal suiting in dark muted wool, a white "
            "shirt, grooming a shade too precise - the correctness of a man who "
            "learned the rules rather than grew up inside them, a heavy build that did "
            "not come from an office, unhurried processional bearing"
        ),
        "test_question": "Is the face readable at rest? He opens on 22 seconds of silence and closes on the smallest possible smile.",
        "trap": "Two failures. A calculating face makes him a villain - he is not one, he is the intern who watched and learned, so the eyes read attentive, never scheming. And casting him smooth kills him: Dick's expensive clothes perform poverty, Pengold's perform belonging. Both are costumes; only Pengold knows it. The polish must look acquired.",
        "variants": [
            "heavy-set and thickening, receding hairline, the acquired polish sitting visibly uneasily on him",
            "solid but not fat, full hair greying at the temples, the polish worn easily and well - the most dangerous version",
            "thickening through the neck and jaw, high forehead and thinning crown, composure that visibly takes effort",
            "burly and broad-shouldered, close-cropped receding hair, good tailoring that does not quite fit the man inside it",
            "medium build, dark hair combed back with care, a smooth surface and something watchful underneath",
            "heavy jaw and thick neck, a thinning widow's peak, the whole presentation obviously and recently constructed",
        ],
    },
    "dick": {
        "order": 4,
        "role": "Tenor. The sacrifice. His fall must land as pathos.",
        "lighting": "single-source tungsten key, soft falloff",
        # REVIEWED 2026-09-02. "charismatic" is a judgement, not a feature - a model
        # cannot render it. Leads with the face now; the wardrobe list was long enough
        # to dominate the generation, and wardrobe is a separate lock anyway (train the
        # face, not the jacket). The Valencia rhyme is deliberate and load-bearing.
        "canon_core": (
            "a lean young man with an open unguarded face that gives everything away, "
            "immediately likeable, no wariness anywhere in it, the softness of someone "
            "who has never had to be hard, dark raw selvedge denim and a heritage "
            "workwear jacket over a faded band t-shirt, a handwoven scarf - the same "
            "silhouette a broke twenty-something would wear, bought at ten times the price"
        ),
        "test_question": "Does the audience want to see him arrested? If yes, the ending does not work.",
        "trap": "Punchability. The audience has to understand why Summer fell for him and why a bodega owner opened the door - so he must be genuinely likeable, which is not the same as handsome. He is the only principal whose face gives everything away, which is exactly why he never sees it coming. Note the rhyme with Valencia: near-identical silhouette, opposite bank balance. Hers is assembled from what was affordable; his is curated at expense to look that way.",
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
    base_look = kernel["look"]
    register = kernel["register"]
    negatives = kernel["negatives"] + ", " + LIKENESS_GUARD

    entries = []
    for key, c in sorted(CHARACTERS.items(), key=lambda kv: kv[1]["order"]):
        # A character whose canon lighting differs from the kernel's strips the
        # kernel's lighting clause instead of stacking a second, contradictory one.
        # NH-USA-007: the kernel grade is NOT used for casting stills.
        look = CASTING_LOOK
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
                    c["canon_core"], variant, FRAMING, look, register,
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
