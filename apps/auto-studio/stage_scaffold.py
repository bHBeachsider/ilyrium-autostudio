#!/usr/bin/env python3
"""
stage_scaffold.py - materialize the per-stage element checklists (bible_checklist.json for
Stage 1 + stage_checklists.json for 2-11) as folders/stubs inside a project, and report
per-element completion. One generalized tool for all 11 stages.

USAGE
  python stage_scaffold.py scaffold --project satesh            # all stages
  python stage_scaffold.py scaffold --project satesh --stage 4
  python stage_scaffold.py status   --project satesh [--stage N]
  python stage_scaffold.py scaffold --all-projects              # every project under projects/
"""
import argparse, json, os, glob

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))


def _proj(project):
    from project_paths import resolve_project
    return resolve_project(project)


def stages():
    """Unified {stage_num: {name, base, elements:[{key,name,what,inputs,required,target}]}}."""
    out = {}
    # Stage 1 — flatten the 6 bible dimensions; targets are relative to 01_development/bible/
    b = json.load(open(os.path.join(HERE, "bible_checklist.json"), encoding="utf-8"))
    els = []
    for dim in b["dimensions"]:
        for el in dim["elements"]:
            els.append({**el, "dimension": dim["key"]})
    out[1] = {"name": b["name"], "base": "01_development/bible", "elements": els}
    # Stages 2-11 — targets relative to project root
    s = json.load(open(os.path.join(HERE, "stage_checklists.json"), encoding="utf-8"))
    for num, sd in s["stages"].items():
        out[int(num)] = {"name": sd["name"], "base": "", "elements": sd["elements"]}
    return out


def _concrete(tgt):
    """A target we can create as a stub now (not auto / kernel-field / cross-stage / instance)."""
    return not (tgt == "auto" or "#" in tgt or tgt.startswith("../") or "<" in tgt)


def scaffold(project, stage=None, root=None):
    proj, st = (root or _proj(project)), stages()
    made = []
    for num, sd in sorted(st.items()):
        if stage and num != stage:
            continue
        base = os.path.join(proj, sd["base"])
        for el in sd["elements"]:
            tgt = el["target"]
            if tgt == "auto" or "#" in tgt or tgt.startswith("../"):
                continue
            if "<" in tgt:                                   # instance-named -> ensure parent dir
                d = os.path.join(base, os.path.dirname(tgt))
                os.makedirs(d, exist_ok=True); continue
            path = os.path.join(base, tgt)
            if tgt.endswith("/"):
                os.makedirs(path, exist_ok=True); continue
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if not os.path.exists(path):
                if path.endswith(".json"):
                    open(path, "w", encoding="utf-8").write("[]\n")   # valid empty JSON, not a markdown stub
                else:
                    hdr = f"# {el['name']}\n\n> {el['what']}\n> inputs: {', '.join(el['inputs']) or 'auto'}\n\n[TODO]\n"
                    open(path, "w", encoding="utf-8").write(hdr)
                made.append(os.path.relpath(path, proj))
    return made


def _element_state(proj, base, el):
    """(done, value) for one element."""
    tgt, done, value = el["target"], False, ""
    if tgt == "auto":
        done = False
    elif "#" in tgt:
        kf = os.path.join(proj, "style_kernel.json"); field = tgt.split("#")[1]
        try:
            v = json.load(open(kf)).get(field)
            done = bool(v) and (not isinstance(v, str) or "DRAFT" not in v)
            value = (json.dumps(v) if not isinstance(v, str) else v) if v else ""
        except Exception:
            pass
    elif "<" in tgt or tgt.endswith("/") or tgt.startswith("../"):
        d = os.path.normpath(os.path.join(base, tgt.split("<")[0].rstrip("/")))
        done = os.path.isdir(d) and any(os.scandir(d)) if os.path.isdir(d) else False
    else:
        p = os.path.join(base, tgt)
        if os.path.exists(p):
            txt = open(p, encoding="utf-8", errors="ignore").read()
            done = "[TODO]" not in txt and "[AUTHOR" not in txt and len(txt.strip()) > 60
            value = txt.split("\n\n", 1)[-1].strip()[:600] if not tgt.endswith(".json") else txt.strip()[:600]
    return done, value


def status(project, stage=None, root=None):
    proj, st = (root or _proj(project)), stages()
    out = {"project": project, "stages": []}
    for num, sd in sorted(st.items()):
        if stage and num != stage:
            continue
        base = os.path.join(proj, sd["base"])
        se = {"stage": num, "name": sd["name"], "what": sd.get("what", ""), "elements": []}
        for el in sd["elements"]:
            done, value = _element_state(proj, base, el)
            se["elements"].append({"key": el["key"], "name": el["name"], "what": el.get("what", ""),
                                   "inputs": el.get("inputs", []), "required": el.get("required", False),
                                   "done": done, "detail": el["target"], "value": value,
                                   "dimension": el.get("dimension")})
        out["stages"].append(se)
    return out


def find_element(stage, key):
    for el in stages().get(int(stage), {}).get("elements", []):
        if el["key"] == key:
            return el
    return None


def write_element(project, stage, key, text, instance="", root=None):
    """Write a natural-language element to its target (md / kernel field / json)."""
    proj = root or _proj(project)
    st = stages().get(int(stage))
    el = find_element(stage, key)
    if not el:
        raise ValueError("unknown element")
    tgt = el["target"]
    if "#" in tgt:
        kf = os.path.join(proj, "style_kernel.json"); field = tgt.split("#")[1]
        k = json.load(open(kf, encoding="utf-8"))
        if field == "casting_canon" or tgt.endswith(".json"):
            k[field] = json.loads(text)
        else:
            k[field] = text
        json.dump(k, open(kf, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        return field
    base = os.path.join(proj, st["base"])
    rel = tgt.replace("<NN_name>", instance or "01_unnamed").replace("<char>", instance or "character").replace("<location>", instance or "location").replace("<prop>", instance or "prop").replace("<scene>", instance or "scene")
    path = os.path.join(base, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if path.endswith(".json"):
        json.loads(text)  # validate
        open(path, "w", encoding="utf-8").write(text if text.strip().endswith(("]", "}")) else text + "\n")
    else:
        open(path, "w", encoding="utf-8").write(f"# {el['name']}\n\n{text}\n")
    return os.path.relpath(path, proj)


def media_dir(project, stage, key, root=None):
    proj = root or _proj(project)
    st = stages().get(int(stage)); base = os.path.join(proj, st["base"])
    folder = st["base"] or st.get("folder", f"{stage:02d}_stage")
    d = os.path.join(proj, (st["base"] or "."), "_media") if st["base"] else os.path.join(proj, "_stage_media", str(stage))
    os.makedirs(d, exist_ok=True)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scaffold", "status"])
    ap.add_argument("--project"); ap.add_argument("--stage", type=int)
    ap.add_argument("--all-projects", action="store_true")
    a = ap.parse_args()
    if a.all_projects:
        from project_paths import list_projects
        projs = [n for n, _ in list_projects()]
    else:
        projs = [a.project]
    for pr in projs:
        if not pr:
            continue
        if a.cmd == "scaffold":
            made = scaffold(pr, a.stage)
            print(f"[{pr}] scaffolded {len(made)} stubs across {'stage '+str(a.stage) if a.stage else 'all stages'}")
        else:
            d = status(pr, a.stage)
            print(f"[{pr}]")
            for s in d["stages"]:
                done = sum(e["done"] for e in s["elements"])
                print(f"  Stage {s['stage']:>2} {s['name']:<34} {done}/{len(s['elements'])}")


if __name__ == "__main__":
    main()
