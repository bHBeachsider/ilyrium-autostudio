#!/usr/bin/env python3
r"""ledger.py - one row per generation: what made this image, exactly (Phase 2, task 17).

The ledger is a JSON-lines file (backlot/provenance/ledger.jsonl - append-only, human-readable, git-diffable) with
a SQLite index rebuilt from it on demand. A row carries: id, when, seq, shot, kind (keyframe | edit | install | motion),
path, sha256, world_version (git hash of the world at generation), stage hash, camera prim, set_state, weather,
model, prompt, seed, conditioning (paths + sha of every pass), cost_usd, gate verdict, parent (the row this was
edited from), and free-form extras. Nothing is ever deleted; corrections are new rows with `supersedes`.

    ledger.py backfill [--renders DIR ...]   read every take_*.json / *_gate.json / *.json sidecar into rows
    ledger.py show <sha-or-path>             every row about this file
    ledger.py reproduce <sha-or-path>        the exact commands that made it, from the stage down
    ledger.py rebuild                        SQLite index from the jsonl

Back-fill for NH-S901: the Phase 1a/1b takes carry full sidecars; the v3-v11 fal edits carry none (their prompts live
in the scripts and FINDINGS.md), so those rows record path, sha, kind=edit, model and the script that made them, and
`reproduce` says so plainly rather than inventing a prompt.
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import sqlite3
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
LEDGER = os.path.join(HERE, "ledger.jsonl")
INDEX = os.path.join(HERE, "ledger.sqlite")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def append(row):
    row = dict(row); row.setdefault("id", uuid.uuid4().hex[:12])
    row.setdefault("when", datetime.datetime.now().isoformat(timespec="seconds"))
    with open(LEDGER, "a") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    return row["id"]


def rows():
    if not os.path.exists(LEDGER):
        return []
    return [json.loads(l) for l in open(LEDGER) if l.strip()]


def known_shas():
    return {r.get("sha256") for r in rows()}


def record_take(png, side):
    """A generate_keyframe.py take: full provenance from its sidecar."""
    s = json.load(open(side))
    return append(dict(kind="keyframe", seq=s.get("seq"), shot=s.get("shot"), path=png, sha256=sha256(png),
                       world_version=s.get("world_version"), camera=s.get("camera"), set_state=s.get("set_state"),
                       model=s.get("model"), prompt=s.get("prompt"), seed=s.get("seed"), values=s.get("values"),
                       conditioning=[v for k, v in s.items() if k.endswith("_pass")],
                       cost_usd=0.0, server=s.get("server"), seconds=s.get("seconds")))


def record_edit(png, side):
    """An edit_keyframe.py output: preset, refs, prompt, model, cost."""
    s = json.load(open(side))
    return append(dict(kind="edit", path=png, sha256=sha256(png), model=s.get("model"), prompt=s.get("prompt"),
                       preset=s.get("preset"), parents=[dict(path=r, sha256=sha256(r) if os.path.exists(r) else None) for r in s.get("refs", [])],
                       cost_usd=0.15))


def record_gate(png, gate_json):
    g = json.load(open(gate_json))
    return append(dict(kind="gate", shot=g.get("shot"), path=png, sha256=g.get("sha256"), verdict=g.get("verdict"),
                       failed=g.get("failed"), advisory=g.get("advisory"), world_version=g.get("world_version")))


def record_install(dst, seq, shot, src, gate_rep):
    return append(dict(kind="install", seq=seq, shot=shot, path=dst, sha256=sha256(dst), source=src,
                       verdict=gate_rep.get("verdict"), world_version=gate_rep.get("world_version")))


def record_legacy(png, seq, shot, note):
    """A key with no sidecar (the v3-v11 fal edits): path, sha, and where its prompt actually lives."""
    return append(dict(kind="edit", seq=seq, shot=shot, path=png, sha256=sha256(png), model="fal-ai/nano-banana-pro/edit (assumed)",
                       prompt=None, note=note, cost_usd=None))


def backfill(dirs):
    seen = known_shas(); n = 0
    for d in dirs:
        for png in sorted(glob.glob(os.path.join(d, "**", "*.png"), recursive=True)):
            if png.endswith(("_sheet.png", "_dbg.png", "_debug.png")):
                continue
            side = png[:-4] + ".json"; gate = png[:-4] + "_gate.json"
            sha = sha256(png)
            if sha in seen:
                continue
            if os.path.exists(side):
                s = json.load(open(side))
                if "seed" in s and "prompt" in s:
                    record_take(png, side); n += 1
                elif "preset" in s:
                    record_edit(png, side); n += 1
            elif os.path.basename(png).startswith("NH-S901-") and png.endswith("_key.png"):
                shot = os.path.basename(png).split("-")[2].split("_")[0]
                record_legacy(png, "NH-S901", shot, "installed key from the v3-v11 fal edit chain; prompt in "
                              "03_design/environments/city_hall/fal_*.py and FINDINGS.md, no sidecar"); n += 1
            seen.add(sha)
            if os.path.exists(gate):
                record_gate(png, gate); n += 1
    return n


def rebuild():
    if os.path.exists(INDEX):
        os.remove(INDEX)
    db = sqlite3.connect(INDEX)
    db.execute("CREATE TABLE rows (id TEXT PRIMARY KEY, when_ TEXT, kind TEXT, seq TEXT, shot TEXT, path TEXT, sha256 TEXT, "
               "world_version TEXT, model TEXT, seed INTEGER, verdict TEXT, cost_usd REAL, json TEXT)")
    for r in rows():
        db.execute("INSERT OR REPLACE INTO rows VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (r.get("id"), r.get("when"), r.get("kind"), r.get("seq"), r.get("shot"), r.get("path"), r.get("sha256"),
                    r.get("world_version"), r.get("model"), r.get("seed"), r.get("verdict"), r.get("cost_usd"), json.dumps(r)))
    db.commit(); db.close()


def find(ref):
    sha = sha256(ref) if os.path.exists(ref) else ref
    return [r for r in rows() if r.get("sha256") == sha or (r.get("sha256") or "").startswith(sha) or r.get("path") == ref]


def reproduce(ref):
    hits = find(ref)
    if not hits:
        return ["nothing in the ledger for %s" % ref]
    out = []
    for r in hits:
        if r["kind"] == "keyframe":
            v = r.get("values", {})
            out += ["# %s %s seed %s, world %s, state %s" % (r.get("seq"), r.get("shot"), r.get("seed"), r.get("world_version"), r.get("set_state")),
                    "git checkout %s -- backlot/world backlot/usd" % (r.get("world_version") or "<world_version unknown>"),
                    "python -m backlot.usd.export_assets && python -m backlot.usd.compose && python -m backlot.usd.derive",
                    "python -m backlot.usd.render_passes %s" % r.get("shot"),
                    "python backlot/generation/generate_keyframe.py %s --takes 1 --seed %s --width %s --height %s --steps %s "
                    "--guidance %s --cn-strength %s --cn-end %s --edge-strength %s --edge-end %s"
                    % (r.get("shot"), r.get("seed"), v.get("width"), v.get("height"), v.get("steps"), v.get("guidance"),
                       v.get("cn_strength"), v.get("cn_end"), v.get("edge_strength", 0), v.get("edge_end", 0)),
                    "# model: %s  server: %s" % (r.get("model"), r.get("server")),
                    "# conditioning: %s" % json.dumps(r.get("conditioning"))]
        elif r["kind"] == "edit":
            if r.get("prompt"):
                out += ["# edit preset %s on %s" % (r.get("preset"), [p.get("path") for p in r.get("parents", [])]),
                        "python backlot/generation/edit_keyframe.py %s <parent> --out <out>   # prompt recorded:" % r.get("preset"),
                        "#   " + (r.get("prompt") or "")[:400]]
            else:
                out += ["# %s: no sidecar - %s" % (os.path.basename(r["path"]), r.get("note", "")),
                        "# reproduction is NOT possible from the ledger; the fal edit chain is recorded in FINDINGS.md"]
        elif r["kind"] in ("gate", "install"):
            out += ["# %s: %s verdict %s (world %s)" % (r["kind"], os.path.basename(r["path"]), r.get("verdict"), r.get("world_version"))]
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backfill"); b.add_argument("--renders", nargs="+", default=[os.path.join(PKG, "renders")])
    s = sub.add_parser("show"); s.add_argument("ref")
    r = sub.add_parser("reproduce"); r.add_argument("ref")
    sub.add_parser("rebuild")
    a = ap.parse_args()
    if a.cmd == "backfill":
        n = backfill(a.renders); rebuild(); print("ledger: %d rows added (%d total)" % (n, len(rows())))
    elif a.cmd == "show":
        for row in find(a.ref):
            print(json.dumps(row, indent=1))
    elif a.cmd == "reproduce":
        print("\n".join(reproduce(a.ref)))
    elif a.cmd == "rebuild":
        rebuild(); print("indexed %d rows" % len(rows()))


if __name__ == "__main__":
    main()
