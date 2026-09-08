#!/usr/bin/env python3
r"""require.py - no motion render, no install, without a fresh PASS (Phase 2, task 16).

    from backlot.gate.require import require_pass
    require_pass(key_path)          # raises GateRefused unless <key>_gate.json says PASS for THIS file's sha256

Entry points call this before spending: fal_veo_render.py before uploading a key to Veo, install_key.py before
copying a key into 04_preproduction/keyframes. A key edited after its gate run has a new sha and is refused until
run_gate.py is run again - the JSON is a receipt for one exact file, not a blessing on a filename.
"""
import hashlib
import json
import os
import sys


class GateRefused(Exception):
    pass


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gate_status(key_path):
    gj = key_path[:-4] + "_gate.json"
    if not os.path.exists(gj):
        return None, "no gate receipt (%s) - run backlot/gate/run_gate.py first" % os.path.basename(gj)
    rep = json.load(open(gj))
    if rep.get("sha256") != sha256(key_path):
        return None, "gate receipt is for a different version of this file - re-run run_gate.py"
    if rep.get("verdict") != "PASS":
        return rep, "gate verdict %s (failed: %s)" % (rep.get("verdict"), ", ".join(rep.get("failed", [])))
    return rep, None


def require_pass(key_path):
    rep, why = gate_status(key_path)
    if why:
        raise GateRefused("%s: %s" % (os.path.basename(key_path), why))
    return rep


if __name__ == "__main__":
    for k in sys.argv[1:]:
        rep, why = gate_status(k)
        print("%s %s%s" % ("PASS" if not why else "REFUSED", os.path.basename(k), "" if not why else " - " + why))
