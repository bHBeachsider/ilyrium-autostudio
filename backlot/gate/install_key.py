#!/usr/bin/env python3
r"""install_key.py - put a key into the production's keyframes folder, with its receipt and sheet beside it.

Refuses without a fresh PASS (require.py). Copies KEY -> <keyframes>/<SEQ>-<SHOT>_key.png, plus _gate.json and
_sheet.png under the same stem, and appends the install to the provenance ledger so `reproduce` can find its way
back to the stage, camera, state, prompt, seed and model that made it.

usage: install_key.py KEY.png --shot SH009 --keyframes DIR [--seq NH-S901]
"""
import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from backlot.gate.require import require_pass, GateRefused  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key"); ap.add_argument("--shot", required=True); ap.add_argument("--keyframes", required=True)
    ap.add_argument("--seq", default="NH-S901")
    a = ap.parse_args()
    try:
        rep = require_pass(a.key)
    except GateRefused as e:
        sys.exit("[REFUSED] " + str(e))
    stem = os.path.join(a.keyframes, "%s-%s_key" % (a.seq, a.shot))
    os.makedirs(a.keyframes, exist_ok=True)
    shutil.copy2(a.key, stem + ".png")
    shutil.copy2(a.key[:-4] + "_gate.json", stem + "_gate.json")
    if os.path.exists(rep.get("sheet", "")):
        shutil.copy2(rep["sheet"], stem + "_sheet.png")
    side = a.key[:-4] + ".json"
    if os.path.exists(side):
        shutil.copy2(side, stem + "_take.json")
    try:
        from backlot.provenance import ledger
        ledger.record_install(stem + ".png", a.seq, a.shot, a.key, rep)
    except Exception as e:
        print("[warn] ledger not updated: %s" % e)
    print("[OK] installed %s (+ _gate.json, _sheet.png)" % (stem + ".png"))


if __name__ == "__main__":
    main()
