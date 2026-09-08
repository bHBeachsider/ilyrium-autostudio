#!/usr/bin/env python3
"""Add the backlot block to NH-S901's shot specs from the derived cameras (Phase 0, task 6).
usage: python3 -m backlot.schema.migrate_nh_s901 SHOTS_DIR CAMERAS_JSON
"""
import glob
import json
import os
import sys

INVARIANTS = [
    {"id": "posts_at_stage_ends", "check": "post_projection", "blocking": True},
    {"id": "deck_parallel_to_facade", "check": "deck_orientation", "blocking": False},
    {"id": "banner_reads_spec", "check": "ocr", "blocking": False, "args": {"text_plane": "Banner"}},
]
# shots that have no camera in the world yet (inserts, the office interior) keep their legacy form
WEATHER = "overcast_drizzle"


def main():
    shots_dir, cams_path = sys.argv[1], sys.argv[2]
    cams = json.load(open(cams_path))["cameras"]
    for f in sorted(glob.glob(os.path.join(shots_dir, "NH-S901-*.json"))):
        spec = json.load(open(f))
        sh = spec["shot_id"].split("-")[-1]
        if sh not in cams:
            print("  %-16s legacy (no world camera)" % spec["shot_id"]); continue
        spec["backlot"] = {
            "stage": "backlot/usd/nh/NewHarnomy_square.usda",
            "camera": "/World/Cameras/" + sh,
            "set_state": cams[sh].get("set_state", "finished"),
            "weather": WEATHER,
            "dressing": ["harvest"],
            "invariants": INVARIANTS if sh not in ("SH006",) else INVARIANTS[:2],
            "conditioning": ["clay", "depth", "seg"],
            "references": {"plate": "projects/new_harnomy_usa/03_design/environments/city_hall/plate_exterior_%s_LOCKED.png"
                           % ("dusk" if sh == "SH010" else "firstlight")},
            "budget_usd": 3.0,
        }
        spec.setdefault("render", {})["renderer"] = "fal-veo3.1"
        json.dump(spec, open(f, "w"), indent=2)
        print("  %-16s -> camera %s state %s" % (spec["shot_id"], sh, spec["backlot"]["set_state"]))


if __name__ == "__main__":
    main()
