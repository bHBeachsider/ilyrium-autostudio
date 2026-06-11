#!/usr/bin/env python3
"""
bible_scaffold.py - materialize the Stage-1 bible dimensions (bible_checklist.json) as folders
+ template stubs inside a project, and report per-element completion. The control panel reads
the same manifest + status, so the folder tree and the UI checklist never drift.

USAGE
  python bible_scaffold.py scaffold --project satesh    # create dimension folders + stubs
  python bible_scaffold.py status   --project satesh    # JSON: per-element done/empty
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "bible_checklist.json")


def _repo_root():
    return os.path.dirname(os.path.dirname(HERE))


def _bible_dir(project):
    from project_paths import resolve_project
    return os.path.join(resolve_project(project), "01_development", "bible")


def _load():
    return json.load(open(MANIFEST, encoding="utf-8"))


def scaffold(project):
    bible = _bible_dir(project)
    made = []
    for dim in _load()["dimensions"]:
        folder = dim["folder"]
        if folder.startswith("../") or folder.endswith(".json"):   # cross-stage home, not created here
            continue
        os.makedirs(os.path.join(bible, folder), exist_ok=True)
        for el in dim["elements"]:
            tgt = el["target"]
            if tgt in ("auto",) or tgt.startswith("../") or "#" in tgt or "<" in tgt:
                continue
            path = os.path.join(bible, tgt)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if not os.path.exists(path):
                hdr = f"# {el['name']}\n\n> {el['what']}\n> inputs: {', '.join(el['inputs']) or 'auto'}\n\n[TODO]\n"
                open(path, "w", encoding="utf-8").write(hdr)
                made.append(os.path.relpath(path, bible))
    print(f"scaffolded {len(made)} stubs under {os.path.relpath(bible, _repo_root())}/")
    for m in made:
        print("  +", m)


def status_data(project):
    bible = _bible_dir(project)
    out = {"project": project, "dimensions": []}
    for dim in _load()["dimensions"]:
        de = {"key": dim["key"], "name": dim["name"], "elements": []}
        for el in dim["elements"]:
            tgt = el["target"]
            done, detail, _value = False, "", ""
            if tgt == "auto":
                done = True; detail = "auto"
            elif "#" in tgt:                                  # a style_kernel.json field
                from project_paths import resolve_project
                kf = os.path.join(resolve_project(project), "style_kernel.json")
                field = tgt.split("#")[1]
                try:
                    k = json.load(open(kf)); v = k.get(field)
                    done = bool(v) and (not isinstance(v, str) or "DRAFT" not in v); detail = "kernel:" + field
                    _value = (json.dumps(v) if not isinstance(v, str) else v) if v else ""
                except Exception:
                    pass
            elif tgt.startswith("../") or "<" in tgt:         # cross-stage dir / multi
                p = os.path.join(bible, tgt.replace("<NN_name>", "").replace("<location>", "").rstrip("/"))
                p = os.path.normpath(p)
                done = os.path.isdir(p) and any(os.scandir(p)) if os.path.isdir(p) else False
                detail = "dir"
            else:
                p = os.path.join(bible, tgt)
                if os.path.exists(p):
                    txt = open(p, encoding="utf-8").read()
                    done = "[TODO]" not in txt and "[AUTHOR" not in txt and len(txt.strip()) > 60
                    _value = txt.split("\n\n", 1)[-1].strip()[:600]
                detail = tgt
            de["elements"].append({"key": el["key"], "name": el["name"], "what": el["what"],
                                   "required": el.get("required", False), "inputs": el["inputs"],
                                   "done": done, "detail": detail, "value": _value})
        out["dimensions"].append(de)
    return out


def status(project):
    print(json.dumps(status_data(project), indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scaffold", "status"])
    ap.add_argument("--project", required=True)
    a = ap.parse_args()
    (scaffold if a.cmd == "scaffold" else status)(a.project)


if __name__ == "__main__":
    main()
