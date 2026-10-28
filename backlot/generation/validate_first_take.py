#!/usr/bin/env python3
r"""validate_first_take.py - the Phase 1 exit gate: how often does a world-conditioned keyframe pass FIRST time?

Plan target: >= 90% first-take gate pass on NH-S901 SH003, SH006, SH009 (docs/ows/OWS_PLATFORM_PLAN.md, task 12).
For every take_*.png under --keys/<SHOT>/ this runs gate/check_keyframe_geometry.py with the stage's derived
cameras.json and control_points.json, writes a clay|key comparison sheet next to it, and reports per-shot and
overall pass rates. A take PASSES only if the gate exits 0 (no post FAIL); WARNs are listed but count as passes,
exactly as the gate treats them.

usage: validate_first_take.py [--keys DIR] [--derived DIR] [--passes DIR] [--report report.json]
"""
import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
GATE = os.path.join(PKG, "gate", "check_keyframe_geometry.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", default=os.path.join(PKG, "renders", "keyframes"))
    ap.add_argument("--derived", default=os.path.join(PKG, "usd", "nh", "derived"))
    ap.add_argument("--passes", default=os.path.join(PKG, "usd", "nh", "passes"))
    ap.add_argument("--report", default=None)
    a = ap.parse_args()
    cams = os.path.join(a.derived, "cameras.json"); pts = os.path.join(a.derived, "control_points.json")
    report = {"shots": {}, "target": 0.90}
    tot = ok = 0
    for sdir in sorted(glob.glob(os.path.join(a.keys, "SH*"))):
        shot = os.path.basename(sdir)
        clay = os.path.join(a.passes, shot, "clay.png")
        takes = []
        for key in sorted(glob.glob(os.path.join(sdir, "take_*.png"))):
            sheet = key[:-4] + "_sheet.png"
            cmd = [sys.executable, GATE, key, "--shot", shot, "--cameras", cams, "--points", pts]
            if os.path.exists(clay):
                cmd += ["--clay", clay, "--sheet", sheet]
            r = subprocess.run(cmd, capture_output=True, text=True)
            passed = r.returncode == 0
            warn = "WARN" in r.stdout
            takes.append(dict(take=os.path.basename(key), passed=passed, warn=warn,
                              lines=[l for l in r.stdout.splitlines() if l.strip()][:12]))
            tot += 1; ok += passed
            print("%s %s %s%s" % ("PASS" if passed else "FAIL", shot, os.path.basename(key), " (warn)" if warn else ""), flush=True)
            for l in takes[-1]["lines"]:
                if "FAIL" in l or "WARN" in l:
                    print("      " + l.strip())
        n = len(takes); p = sum(t["passed"] for t in takes)
        report["shots"][shot] = dict(takes=n, passed=p, rate=(p / n) if n else None, detail=takes)
        print("-- %s: %d/%d first-take pass" % (shot, p, n), flush=True)
    report["total"] = dict(takes=tot, passed=ok, rate=(ok / tot) if tot else None)
    verdict = "MET" if tot and ok / tot >= 0.90 else "NOT MET"
    print("== overall %d/%d = %.0f%%  (target >= 90%%: %s)" % (ok, tot, 100.0 * ok / max(tot, 1), verdict))
    report["verdict"] = verdict
    if a.report:
        json.dump(report, open(a.report, "w"), indent=1)
    return 0 if verdict == "MET" else 1


if __name__ == "__main__":
    sys.exit(main())
