#!/usr/bin/env python3
r"""run_gate.py - the QA station: every check on one key, one verdict, one sheet, one JSON (Phase 2, tasks 13-16).

    geometry   check_keyframe_geometry.py   BLOCKING   posts on their columns, deck line, chair band, clay comparison
    seg        seg_iou.py                    advisory   the stage's extent and axis vs the seg pass (CLIPSeg)
    text       ocr_text.py                   BLOCKING   every text plane reads the spec (auto-fix: --autoletter)
    judge      judge.py                      advisory   a vision model rules on the shot's invariants (--judge)

The verdict is PASS only when every blocking check passes. Beside the key it writes <key>_gate.json (every line of
every check, the key's sha256, the world version) and <key>_sheet.png (clay | key). Nothing downstream - installing
a key, rendering motion - accepts a key without a fresh PASS in that JSON (require.py).

usage: run_gate.py KEY.png --shot SH009 [--passes-root DIR] [--derived DIR] [--autoletter] [--judge] [--seq NH-S901]
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = [l for l in (r.stdout + r.stderr).splitlines() if l.strip() and "Loading weights" not in l and "Warning" not in l]
    return r.returncode, out


def gate(key, shot, passes_root, derived, autoletter=False, judge=False, seq="NH-S901", py=sys.executable):
    cams = os.path.join(derived, "cameras.json"); pts = os.path.join(derived, "control_points.json")
    pdir = os.path.join(passes_root, shot)
    sheet = key[:-4] + "_sheet.png"
    report = dict(key=key, shot=shot, sha256=sha256(key), checks={}, sheet=sheet)
    try:
        report["world_version"] = json.load(open(os.path.join(pdir, "passes.json"))).get("world_version")
    except Exception:
        report["world_version"] = None

    cmd = [py, os.path.join(HERE, "check_keyframe_geometry.py"), key, "--shot", shot, "--cameras", cams, "--points", pts]
    if os.path.exists(os.path.join(pdir, "clay.png")):
        cmd += ["--clay", os.path.join(pdir, "clay.png"), "--sheet", sheet]
    rc, lines = run(cmd)
    report["checks"]["geometry"] = dict(blocking=True, passed=rc == 0, lines=lines)

    if os.path.exists(os.path.join(pdir, "seg.png")):
        rc, lines = run([py, os.path.join(HERE, "seg_iou.py"), key, "--passes", pdir])
        report["checks"]["seg"] = dict(blocking=False, passed=rc == 0, lines=lines)

    rc, lines = run([py, os.path.join(HERE, "ocr_text.py"), key, "--shot", shot, "--cameras", cams, "--points", pts])
    if rc != 0 and autoletter:
        cmds = [l.split("letter_from_plate: ", 1)[1] for l in lines if "letter_from_plate: " in l]
        for c in cmds:
            subprocess.run(c, shell=True, capture_output=True)
        lettered = key[:-4] + "_lettered.png"
        if os.path.exists(lettered):
            os.replace(lettered, key)
            report["sha256"] = sha256(key); report["autolettered"] = True
            rc, lines2 = run([py, os.path.join(HERE, "ocr_text.py"), key, "--shot", shot, "--cameras", cams, "--points", pts])
            lines = lines + ["  -- auto-lettered from the world's text plane, re-read:"] + lines2
    report["checks"]["text"] = dict(blocking=True, passed=rc == 0, lines=lines)

    if judge and os.path.exists(sheet):
        rc, lines = run([py, os.path.join(HERE, "judge.py"), sheet, "--shot", shot, "--seq", seq,
                         "--json", key[:-4] + "_judge.json"])
        report["checks"]["judge"] = dict(blocking=False, passed=rc == 0, lines=lines)

    blocking_fail = [n for n, c in report["checks"].items() if c["blocking"] and not c["passed"]]
    advisory_warn = [n for n, c in report["checks"].items() if not c["blocking"] and not c["passed"]]
    report["verdict"] = "FAIL" if blocking_fail else "PASS"
    report["failed"] = blocking_fail; report["advisory"] = advisory_warn
    json.dump(report, open(key[:-4] + "_gate.json", "w"), indent=1)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key"); ap.add_argument("--shot", required=True); ap.add_argument("--seq", default="NH-S901")
    ap.add_argument("--passes-root", default=os.path.join(PKG, "usd", "nh", "passes"))
    ap.add_argument("--derived", default=os.path.join(PKG, "usd", "nh", "derived"))
    ap.add_argument("--autoletter", action="store_true"); ap.add_argument("--judge", action="store_true")
    a = ap.parse_args()
    rep = gate(a.key, a.shot, a.passes_root, a.derived, a.autoletter, a.judge, a.seq)
    for name, c in rep["checks"].items():
        print("%s %-8s %s" % ("PASS" if c["passed"] else ("FAIL" if c["blocking"] else "WARN"), name,
                               "(blocking)" if c["blocking"] else "(advisory)"))
        for l in c["lines"]:
            if any(t in l for t in ("FAIL", "WARN", "PASS", "ok ", "n/a", "info", "letter_from_plate", "auto-lettered")):
                print("      " + l.strip())
    print("== %s %s  (%s)" % (rep["verdict"], os.path.basename(a.key),
                              "blocking failures: " + ", ".join(rep["failed"]) if rep["failed"] else "all blocking checks pass"
                              + ("; advisory warnings: " + ", ".join(rep["advisory"]) if rep["advisory"] else "")))
    sys.exit(0 if rep["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
