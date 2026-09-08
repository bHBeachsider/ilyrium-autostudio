#!/usr/bin/env python3
r"""regression.py - the gate's own test: does each check agree with the eye? (Phase 2 check)

Runs the geometry check and the seg check on every key in regression_manifest.json and compares to the verdict a
human gave it. Reports, per check: false rejects (eye PASS, check FAIL/WARN) and misses (eye FAIL, check PASS), with
rates. This is what decides whether an advisory check may become blocking (rule: false-reject rate under 5% on this
suite) - run it on every change to a threshold or a prompt in the gate.

usage: regression.py [--manifest regression_manifest.json] [--report OUT.json]
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=os.path.join(HERE, "regression_manifest.json"))
    ap.add_argument("--report")
    a = ap.parse_args()
    man = json.load(open(a.manifest))
    derived = os.path.join(PKG, "usd", "nh", "derived"); passes = os.path.join(PKG, "usd", "nh", "passes")
    rows = []
    for e in man["entries"]:
        key = os.path.join(PKG, e["path"]); shot = e["shot"]
        rc_g, out_g = run([sys.executable, os.path.join(HERE, "check_keyframe_geometry.py"), key, "--shot", shot,
                           "--cameras", os.path.join(derived, "cameras.json"), "--points", os.path.join(derived, "control_points.json")])
        rc_s, out_s = run([sys.executable, os.path.join(HERE, "seg_iou.py"), key, "--passes", os.path.join(passes, shot)])
        seg_v = "WARN" if "WARN stage" in out_s else ("PASS" if rc_s == 0 else "FAIL")
        rows.append(dict(path=e["path"], shot=shot, expect=e["expect"], geometry="PASS" if rc_g == 0 else "FAIL", seg=seg_v, note=e["note"]))
        print("%-45s eye %-4s geometry %-4s seg %-4s" % (e["path"], e["expect"], rows[-1]["geometry"], seg_v), flush=True)
    summary = {}
    for chk in ("geometry", "seg"):
        good = [r for r in rows if r["expect"] == "PASS"]; bad = [r for r in rows if r["expect"] == "FAIL"]
        fr = [r["path"] for r in good if r[chk] != "PASS"]
        miss = [r["path"] for r in bad if r[chk] == "PASS"]
        summary[chk] = dict(false_reject=len(fr), false_reject_rate=round(len(fr) / max(1, len(good)), 3), false_rejects=fr,
                            misses=len(miss), miss_rate=round(len(miss) / max(1, len(bad)), 3), missed=miss,
                            may_block=len(fr) / max(1, len(good)) < 0.05)
        print("== %-8s false-reject %d/%d (%.0f%%)  misses %d/%d  -> %s" % (chk, len(fr), len(good), 100 * summary[chk]["false_reject_rate"],
              len(miss), len(bad), "may block" if summary[chk]["may_block"] else "advisory only"))
    if a.report:
        json.dump(dict(rows=rows, summary=summary), open(a.report, "w"), indent=1)


if __name__ == "__main__":
    main()
