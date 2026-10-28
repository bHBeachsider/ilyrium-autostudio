#!/usr/bin/env python3
"""backlot.schema.shot_spec_v2 - extend ilyrium-shots/shot_spec.schema.json to v2, additively.

v2 adds ONE optional top-level block, "backlot", so every existing consumer keeps validating, and raises the render
caps that blocked 1080p/2K (NH-USA-038). A shot that carries a backlot block is a shot the world can render, gate and
reproduce; a shot without one is a legacy shot.

usage: python3 -m backlot.schema.shot_spec_v2 PATH/TO/shot_spec.schema.json   (rewrites in place, keeps a .v1 copy)
"""
import json
import os
import shutil
import sys

BACKLOT_BLOCK = {
    "type": "object",
    "additionalProperties": False,
    "required": ["stage", "camera", "set_state"],
    "description": "One World Set: where this shot lives in the world. See docs/ows/OWS_PLATFORM_PLAN.md.",
    "properties": {
        "stage": {"type": "string", "description": "USD stage path relative to repo root"},
        "camera": {"type": "string", "pattern": "^/World/Cameras/[A-Za-z0-9_]+$", "description": "camera prim in the stage"},
        "set_state": {"type": "string", "description": "the 'build' variant selection on /World for this shot"},
        "weather": {"type": "string"},
        "dressing": {"type": "array", "items": {"type": "string"}},
        "invariants": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["id", "check"],
            "properties": {"id": {"type": "string"}, "check": {"enum": ["post_projection", "deck_orientation", "seg_iou", "ocr", "judge"]},
                           "blocking": {"type": "boolean", "default": False}, "args": {"type": "object"}}}},
        "conditioning": {"type": "array", "items": {"enum": ["clay", "depth", "normal", "seg", "lineart"]}},
        "references": {"type": "object", "additionalProperties": {"type": "string"},
                       "description": "named reference images (plate, anchor) - the camera never comes from these (NH-USA-043)"},
        "budget_usd": {"type": "number", "minimum": 0},
        "world_version": {"type": "string", "description": "git hash of backlot/ the stage was composed at; filled by generate"},
    },
}


def patch(path):
    s = json.load(open(path))
    if "backlot" in s["properties"]:
        print("already v2"); return
    shutil.copy(path, path + ".v1")
    s["properties"]["backlot"] = BACKLOT_BLOCK
    r = s["properties"]["render"]["properties"]
    r["width"]["maximum"] = 4096; r["height"]["maximum"] = 4096
    r["renderer"] = {"enum": ["comfyui-wan22", "fal-veo3.1", "fal-veo3.1-fast", "comfyui-flux-controlnet"]}
    s["description"] = (s.get("description", "") + " v2 (2026-09-08): optional 'backlot' block binds a shot to the USD stage, camera "
                        "prim, set state and gate invariants; render caps raised for 1080p/2K.").strip()
    json.dump(s, open(path, "w"), indent=2)
    print("patched to v2:", path)


if __name__ == "__main__":
    patch(sys.argv[1])
