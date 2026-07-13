#!/usr/bin/env python3
"""
bible_scaffold.py - materialize the Stage-1 bible dimensions (bible_checklist.json) as folders
+ template stubs inside a project, and report per-element completion. The control panel reads
the same manifest + status, so the folder tree and the UI checklist never drift.

USAGE
  python bible_scaffold.py scaffold --project satesh    # create dimension folders + stubs
  python bible_scaffold.py status   --project satesh    # JSON: per-element done/empty
"""
import argparse, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "bible_checklist.json")


def _repo_root():
    return os.path.dirname(os.path.dirname(HERE))


def _bible_dir(project):
    from project_paths import resolve_project
    return os.path.join(resolve_project(project), "01_development", "bible")


def _load():
    return json.load(open(MANIFEST, encoding="utf-8"))


def _templates_dir():
    return os.path.join(_repo_root(), "docs", "bible_templates")


def _drop_templates(bible):
    """Copy the authoring templates (docs/bible_templates/) into the project bible.

    Non-destructive (only writes files that don't exist). Drops the full kit under
    `_templates/` as reference, and the character template at `characters/_CHARACTER_TEMPLATE.md`
    — right where per-character `<NN_name>/bible.md` files are authored (the manifest can't
    materialize those since names aren't known at scaffold time)."""
    tdir = _templates_dir()
    dropped = []
    if not os.path.isdir(tdir):
        return dropped
    kit = os.path.join(bible, "_templates")
    os.makedirs(kit, exist_ok=True)
    for fn in sorted(os.listdir(tdir)):
        src = os.path.join(tdir, fn)
        dst = os.path.join(kit, fn)
        if os.path.isfile(src) and not os.path.exists(dst):
            shutil.copyfile(src, dst); dropped.append(os.path.relpath(dst, bible))
    ch_src = os.path.join(tdir, "CHARACTER_TEMPLATE.md")
    if os.path.isfile(ch_src):
        chars = os.path.join(bible, "characters"); os.makedirs(chars, exist_ok=True)
        ch_dst = os.path.join(chars, "_CHARACTER_TEMPLATE.md")
        if not os.path.exists(ch_dst):
            shutil.copyfile(ch_src, ch_dst); dropped.append(os.path.relpath(ch_dst, bible))
    return dropped


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
    dropped = _drop_templates(bible)
    print(f"scaffolded {len(made)} stubs + {len(dropped)} templates under {os.path.relpath(bible, _repo_root())}/")
    for m in made:
        print("  +", m)
    for d in dropped:
        print("  +", d, "(template)")


# Media attachments: bible_media (studio_pipeline_service) saves uploads as
# <bible>/<dim_key>/_media/{element_key}_{timestamp}{ext} — timestamped, so files accumulate.
_KIND_EXT = {
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".tif", ".tiff"},
    "video": {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"},
    "audio": {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"},
    "text":  {".txt", ".md", ".json", ".csv", ".rtf"},
    "pdf":   {".pdf"},
}
_MEDIA_INPUTS = {"image", "video", "audio", "file", "refs"}


def media_kind(filename):
    """Infer a coarse media kind (image/video/audio/text/pdf/other) from the extension."""
    ext = os.path.splitext(filename)[1].lower()
    for kind, exts in _KIND_EXT.items():
        if ext in exts:
            return kind
    return "other"


def element_files(bible, dim_key, el_key):
    """List an element's attached media files as [{name, rel, size, kind}], oldest first.

    `rel` is the path relative to the bible dir (forward slashes) so the control panel can
    fetch/delete via the pipeline service's /media/file and /media/delete endpoints."""
    mdir = os.path.join(bible, dim_key, "_media")
    if not os.path.isdir(mdir):
        return []
    rows = []
    for fn in os.listdir(mdir):
        p = os.path.join(mdir, fn)
        if not (fn.startswith(el_key + "_") and os.path.isfile(p)):
            continue
        rows.append((os.path.getmtime(p), fn,
                     {"name": fn, "rel": os.path.relpath(p, bible).replace(os.sep, "/"),
                      "size": os.path.getsize(p), "kind": media_kind(fn)}))
    return [r[2] for r in sorted(rows, key=lambda r: (r[0], r[1]))]


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
            files = element_files(bible, dim["key"], el["key"]) if _MEDIA_INPUTS & set(el["inputs"]) else []
            if files:                                     # media attachments count as done
                done = True
            de["elements"].append({"key": el["key"], "name": el["name"], "what": el["what"],
                                   "required": el.get("required", False), "inputs": el["inputs"],
                                   "done": done, "detail": detail, "value": _value, "files": files})
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
