#!/usr/bin/env python3
r"""resolve_scene.py - the Backlot Agent, step one: a scene card in, a resolved request out. It never writes a prompt.

Input: one scene from 02_script/scenes.json (or a numbers/*.scenes.json card): location text, characters, action,
visual_prompt, duration. Output: a structured REQUEST resolved against the catalog - every noun the scene needs is
either an asset that exists (reuse / configure a variant) or a BUILD item queued with a reason. The generation layer
(generate_keyframe.py) is downstream of this; the agent decides WHAT is in front of the camera, not how to say it.

    {"scene": 4, "location": {"text": "...", "set": "PengoldOffice", "match": "alias", "confidence": 0.95},
     "world": {"stage": "nh/NewHarnomy_square.usda", "variants": {"office": "dawn", "people": "office_dawn", "build": "finished", "weather": "..."}},
     "lighting": "office_dawn", "time": "dawn",
     "characters": [{"id": "pengold", "mark": "desk_chair", "posture": "seated", "mannequin": "man_pengold"}],
     "props": [{"noun": "desk lamp", "asset": "PengoldOffice/po_lamp", "status": "exists"}, ...],
     "text_planes": [...], "camera": {"suggest": "S101_SH004", "framing": "wide", "lens_hint": "24"},
     "build_queue": [{"asset": "...", "reason": "...", "scene": 4}], "invariants": [...]}

Resolution order: exact alias > tag overlap > nothing (then the location itself is a BUILD item). Characters are
placed on marks by a small table (who sits where in which set); a character with no mark is a BUILD item (a mark,
not a model). Props are matched by noun against the set's prim names and the catalog tags; unmatched props are
BUILD items ranked later by build_queue.py.

usage: resolve_scene.py SCENES.json [--scene N ...] [--out DIR] [--seq NH-S101]
"""
import argparse
import json
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(PKG))

CATALOG = os.path.join(PKG, "catalog", "nh.yaml")
LIGHTING = os.path.join(PKG, "world", "nh", "lighting.yaml")
STAGE = "nh/NewHarnomy_square.usda"

# who stands where, per set - the marks live in the set's ControlPoints (derived/control_points.json)
BLOCKING = {
    "PengoldOffice": {"pengold": ("desk_chair", "seated")},
    "RallyStage": {"pengold": ("podium", "standing"), "summer": ("beneath_portrait", "standing"),
                   "dick": ("stage_left_threshold", "standing"), "valencia": ("upstage_right", "standing")},
    # LYSTERIA: Summer works with the square behind her; a visitor takes the head of the conference table
    # LYSTERIA: Summer at her desk behind the glass, the band behind her; a visitor takes the chair with the light in
    # their face, or the sofa for the chat
    "LysteriaInterior": {"summer": ("desk_chair", "seated"), "dick": ("visitor_chair", "seated"),
                         "pengold": ("sofa", "seated"), "valencia": ("glass_door", "standing")},
}
PEOPLE_STATE = {"PengoldOffice": "office_dawn", "RallyStage": "feast", "LysteriaInterior": "lysteria"}
TIME_WORDS = [("dawn", "dawn"), ("dusk", "dusk"), ("night", "night"), ("evening", "evening"), ("morning", "morning"),
              ("meeting", "meeting_hour")]
# scene-card nouns -> prim name fragments in the set (props that exist in the blockout)
PROP_NOUNS = {
    "desk": "po_desk", "credenza": "po_credenza", "desk lamp": "po_lamp", "lamp": "po_lamp", "coffee cup": "po_cup",
    "coffee": "po_cup", "newspaper": "po_newspaper", "mauve books": "po_book", "paperbacks": "po_book", "books": "po_book",
    "portrait": "po_portrait", "drapes": "po_drape", "door": "po_door",
    "podium": "podium", "chairs": "chair", "banner": "banner_cloth", "steps": "steps", "crossbeam": "truss_beam",
    "uprights": "truss_post", "posts": "truss_post", "hay bales": None, "pumpkins": None, "garlands": None,
    "folding tables": "pilf_table", "petition": "pilf_petition", "conference table": "lyst_conf",
    "plaques": "lyst_plaque", "awards": "lyst_plaque", "framed banners": "lyst_banner", "banners": "lyst_banner",
    "tote bags": "lyst_tote", "totes": "lyst_tote", "presentation boards": "lyst_mbc_board", "easels": "lyst_easel",
    "sash": "lyst_sash", "glass wall": "lyst_glass_wall", "glass door": "lyst_glass_door", "nameplate": "lyst_nameplate",
    "wordmark": "lyst_wordmark", "reception": "lyst_reception", "photographs": "lyst_photo", "gallery": "lyst_photo",
    "sofa": "lyst_sofa", "staff desks": "lyst_bench", "benches": "lyst_bench", "pendant": "lyst_pendant", "staff": "man_staff",
}
FRAMING = [("wide", "wide"), ("establishing", "wide"), ("medium", "medium"), ("close-up", "close"), ("closeup", "close"),
           ("hands", "close"), ("insert", "close")]


def load_catalog():
    return yaml.safe_load(open(CATALOG))


def resolve_location(text, catalog):
    t = text.lower()
    best = None
    for a in catalog:
        for al in a.get("aliases", []):
            if al.lower() in t:
                score = 0.9 + 0.1 * len(al) / max(len(t), 1)
                if not best or score > best[2]:
                    best = (a["asset_id"], "alias", round(min(score, 0.99), 2), al)
    if best:
        return dict(text=text, set=best[0], match=best[1], confidence=best[2], via=best[3])
    words = set(re.findall(r"[a-z']+", t))
    scored = []
    for a in catalog:
        hits = words & {x.lower() for x in a.get("tags", [])}
        if hits:
            scored.append((len(hits), a["asset_id"], sorted(hits)))
    if scored and max(scored)[0] >= 2:          # one shared word ("stage" in "the theater stage") is not a match
        n, aid, hits = max(scored)
        return dict(text=text, set=aid, match="tags", confidence=round(0.4 + 0.1 * n, 2), via=hits)
    return dict(text=text, set=None, match="none", confidence=0.0, via=None)


def prims_of(aid):
    """Prim names of the composed asset (all states) from its geo files - cheap, no USD import."""
    d = os.path.join(PKG, "usd", "nh", "assets", aid)
    names = set()
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.startswith("geo") and f.endswith(".usda"):
                names |= set(re.findall(r'def Xform "([^"]+)"', open(os.path.join(d, f)).read()))
    return names


def resolve(scene, catalog, lighting, seq):
    loc = resolve_location(scene.get("location", ""), catalog)
    text = " ".join([scene.get("location", ""), scene.get("action", ""), scene.get("visual_prompt", "")]).lower()
    out = dict(seq=seq, scene=scene.get("scene_number"), duration_s=scene.get("duration_target_s"), location=loc,
               build_queue=[], props=[], characters=[], text_planes=[], invariants=[])
    aid = loc["set"]
    if aid is None:
        if scene.get("location", "").strip().lower() not in ("black", ""):
            out["build_queue"].append(dict(kind="set", asset=None, noun=scene.get("location"), scene=out["scene"],
                                           reason="no catalog set matches this location (alias or tag)"))
        out["world"] = None
        return out
    asset = next(a for a in catalog if a["asset_id"] == aid)
    # time / lighting
    time = next((v for w, v in TIME_WORDS if w in text), None)
    out["time"] = time
    lstates = [k for k, v in lighting["states"].items() if aid in v.get("sets", [])]
    pick = None
    for k in lstates:
        if time and (time in k or lighting["states"][k].get("time", "") == time):
            pick = k
    out["lighting"] = pick or (lstates[0] if lstates else None)
    if not out["lighting"]:
        out["build_queue"].append(dict(kind="lighting", asset=aid, noun="lighting state for %s at %s" % (aid, time), scene=out["scene"],
                                       reason="no lighting state registered for this set/time in world/nh/lighting.yaml"))
    # variants
    variants = {"build": "finished", "weather": lighting["states"].get(out["lighting"] or "", {}).get("weather", "overcast_drizzle")}
    if aid == "PengoldOffice":
        variants["office"] = "meeting" if time == "meeting_hour" else "dawn"
    if aid == "LysteriaInterior":
        variants["lysteria"] = "launch" if ("launch" in text or "man bun" in text or "festival" in text) else "working"
    if aid == "RallyStage" and ("feast" in text or "denunciation" in text or "coronation" in text):
        variants["build"] = "feast"
    chars = scene.get("characters", []) or []
    variants["people"] = PEOPLE_STATE.get(aid, "none") if chars else "none"
    out["world"] = dict(stage=STAGE, set=aid, variants=variants, states_available=asset.get("states", []))
    # characters on marks
    marks = set(asset.get("marks", []))
    for c in chars:
        mk = BLOCKING.get(aid, {}).get(c)
        if mk and mk[0] in marks:
            out["characters"].append(dict(id=c, mark=mk[0], posture=mk[1], mannequin="man_%s" % c))
        else:
            out["characters"].append(dict(id=c, mark=None, posture=None, mannequin=None))
            out["build_queue"].append(dict(kind="mark", asset=aid, noun="mark for %s in %s" % (c, aid), scene=out["scene"],
                                           reason="character has no mark in this set (add to ControlPoints + BLOCKING)"))
    # props
    prims = prims_of(aid)
    for noun, frag in PROP_NOUNS.items():
        if noun in text:
            if frag and any(frag in p for p in prims):
                out["props"].append(dict(noun=noun, asset="%s/%s" % (aid, frag), status="exists"))
            elif frag and any(frag in p for a2 in catalog for p in prims_of(a2["asset_id"])):
                other = next(a2["asset_id"] for a2 in catalog if any(frag in p for p in prims_of(a2["asset_id"])))
                out["props"].append(dict(noun=noun, asset="%s/%s" % (other, frag), status="exists (other set)"))
            else:
                out["props"].append(dict(noun=noun, asset=None, status="BUILD"))
                out["build_queue"].append(dict(kind="prop", asset=aid, noun=noun, scene=out["scene"],
                                               reason="named in the scene, absent from the blockout (%s)" % aid))
    out["text_planes"] = asset.get("text_planes", [])
    # camera
    framing = next((v for w, v in FRAMING if w in text), "medium")
    out["camera"] = dict(framing=framing, suggest=None)
    if aid == "PengoldOffice":
        out["camera"]["suggest"] = {"wide": "S101_SH004", "medium": "S101_SH005", "close": "S101_SH007"}[framing]
    elif aid == "RallyStage":
        out["camera"]["suggest"] = {"wide": "SH010", "medium": "SH009", "close": "SH009"}[framing]
    elif aid == "LysteriaInterior":
        out["camera"]["suggest"] = {"wide": "LYST_DESK", "medium": "LYST_DESK", "close": "LYST_DESK"}[framing]
    # invariants come from the set's rules and the scene's own words (positive, counted - NH-USA-051)
    if aid == "PengoldOffice":
        out["invariants"] += ["three French windows with the giant columns a metre beyond the glass",
                              "single-source tungsten from the desk lamp; dawn light held off the desk" if variants["office"] == "dawn" else "door slightly ajar",
                              "three mauve books stacked on the credenza; one pristine mauve copy squared on the desk"]
    if aid == "RallyStage":
        out["invariants"] += ["the stage runs horizontally, parallel to the City Hall facade",
                              "exactly two tall timber uprights, one at each end of the stage"]
    if aid == "LysteriaInterior":
        out["invariants"] += ["an all-white room, walls and floor, one glazed band onto the square, cold-white sun",
                              "a full-height glass wall divides the floor from her office; she sits with the band behind her",
                              "the brand rose is the only accent and it is drained, never a saturated pink",
                              "photographs hung museum-spaced in white frames, one gap with the hook still in the wall",
                              "a tight grid of grant and award plaques on the wall beside her desk",
                              "nothing in the room is ironic: everything is beautiful, tidy and certain"]
        if variants.get("lysteria") == "launch":
            out["invariants"].append("the Man Bun Collective cartons are stacked and still shrink-wrapped, unopened")
    if "no smile" in text or "does not react" in text:
        out["invariants"].append("no smile, no gesture toward the lens")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenes"); ap.add_argument("--scene", type=int, nargs="*")
    ap.add_argument("--out", default=os.path.join(PKG, "agent", "resolved")); ap.add_argument("--seq", default="NH-S101")
    a = ap.parse_args()
    scenes = json.load(open(a.scenes))
    if isinstance(scenes, dict):
        scenes = scenes.get("scenes", [])
    catalog = load_catalog(); lighting = yaml.safe_load(open(LIGHTING))
    os.makedirs(a.out, exist_ok=True)
    queue = []
    for sc in scenes:
        if a.scene and sc.get("scene_number") not in a.scene:
            continue
        r = resolve(sc, catalog, lighting, a.seq)
        json.dump(r, open(os.path.join(a.out, "%s_scene%02d.json" % (a.seq, r["scene"])), "w"), indent=1)
        queue += r["build_queue"]
        loc = r["location"]
        print("scene %2d  %-48s -> %-16s (%s %.2f)  chars %s  props %d/%d exist  builds %d" % (
            r["scene"], (loc["text"] or "")[:48], loc["set"], loc["match"], loc["confidence"],
            ",".join(c["id"] for c in r["characters"]) or "-", sum(p["status"].startswith("exists") for p in r["props"]),
            len(r["props"]), len(r["build_queue"])))
    json.dump(queue, open(os.path.join(a.out, "%s_build_requests.json" % a.seq), "w"), indent=1)
    print("%d build requests -> %s" % (len(queue), os.path.join(a.out, "%s_build_requests.json" % a.seq)))


if __name__ == "__main__":
    main()
