#!/usr/bin/env python3
r"""stage_scene.py - the Backlot Agent, step two: a resolved request -> the stage in the right state -> passes.

Takes resolve_scene.py's JSON, refuses if anything is still queued for build (the world must be able to stand the
scene before a frame is spent), then renders the conditioning passes for the suggested camera with the request's
variants applied. The generation step (generation/generate_keyframe.py on the box) and the gate follow unchanged.

usage: stage_scene.py RESOLVED.json [--allow-queued] [--camera SHOT]
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("resolved"); ap.add_argument("--allow-queued", action="store_true"); ap.add_argument("--camera")
    ap.add_argument("--people-in-passes", action="store_true", help="keep mannequins in the conditioning passes")
    a = ap.parse_args()
    r = json.load(open(a.resolved))
    if r.get("build_queue") and not a.allow_queued:
        sys.exit("[REFUSED] scene %s has %d build request(s) outstanding: %s" % (
            r["scene"], len(r["build_queue"]), "; ".join(b["noun"] for b in r["build_queue"])))
    if not r.get("world"):
        sys.exit("[REFUSED] scene %s resolves to no set (black slug or unresolved location)" % r["scene"])
    cam = a.camera or r["camera"].get("suggest")
    if not cam:
        sys.exit("[REFUSED] no camera for scene %s - add one to world/nh/cameras.py" % r["scene"])
    v = dict(r["world"]["variants"])
    # 2026-09-08: a box-and-sphere mannequin in the depth/edge passes is drawn literally (a bust on the credenza,
    # 0/10 takes with a man). Until the mannequin is human-shaped (build queue: hero-grade Mannequins), the passes
    # condition the SET only and the person is the generation layer's, judged against the mark by the judge.
    if not a.people_in_passes:
        v["people"] = "none"
    variants = ",".join("%s=%s" % kv for kv in v.items())
    cmd = [sys.executable, "-m", "backlot.usd.render_passes", cam, "--variants", variants]
    print("scene %s: %s in %s -> passes for %s" % (r["scene"], r["world"]["set"], r["world"]["variants"], cam), flush=True)
    rc = subprocess.run(cmd, cwd=os.path.dirname(PKG)).returncode
    if rc == 0:
        side = os.path.join(PKG, "usd", "nh", "passes", cam, "request.json")
        json.dump(r, open(side, "w"), indent=1)
        print("[OK] passes/%s carry the resolved request (request.json)" % cam)
    sys.exit(rc)


if __name__ == "__main__":
    main()
