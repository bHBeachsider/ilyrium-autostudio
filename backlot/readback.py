#!/usr/bin/env python3
"""backlot.readback - harvest hand edits from a .blend into a USD override layer.

Reads the asset-root Empties that open_in_blender.py stamped (backlot_asset_root) and, for each whose transform is
no longer identity, writes an `over` on /World/<AssetId> in overrides/readback.usda with that transform. Rerun
compose.py afterwards and the override is the stage's strongest opinion; derive.py then moves the control points
with the asset, and the gate projects the moved set. The code stays the truth for what an asset IS; the override
is the truth for where Brad put it.

usage: python3 -m backlot.readback BLEND [--out backlot/usd/nh/overrides/readback.usda]
"""
import math
import os
import sys

import bpy
from pxr import Gf, Sdf, Usd, UsdGeom

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    a = sys.argv[1:]
    blend = a[0]
    out = a[a.index("--out") + 1] if "--out" in a else os.path.join(HERE, "usd", "nh", "overrides", "readback.usda")
    bpy.ops.wm.open_mainfile(filepath=blend)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    stage = Usd.Stage.CreateNew(out) if not os.path.exists(out) else Usd.Stage.Open(out)
    layer = stage.GetRootLayer(); layer.Clear()
    moved = []
    for o in bpy.data.objects:
        aid = o.get("backlot_asset_root")
        if not aid:
            continue
        m = o.matrix_world
        loc, rot, scale = m.decompose()
        rot = rot.to_euler("XYZ")
        if max(abs(v) for v in loc) < 1e-4 and max(abs(v) for v in rot) < 1e-5 and all(abs(s - 1) < 1e-5 for s in scale):
            continue
        over = stage.OverridePrim("/World/" + aid)
        xf = UsdGeom.Xformable(over)
        xf.ClearXformOpOrder()
        xf.AddTranslateOp().Set(Gf.Vec3d(*[round(v, 4) for v in loc]))
        xf.AddRotateXYZOp().Set(Gf.Vec3f(*[round(math.degrees(v), 3) for v in rot]))
        if any(abs(s - 1) > 1e-5 for s in scale):
            xf.AddScaleOp().Set(Gf.Vec3f(*[round(v, 4) for v in scale]))
        moved.append((aid, [round(v, 2) for v in loc], [round(math.degrees(v), 1) for v in rot]))
    layer.comment = "hand edits read back from %s - the strongest sublayer of the stage" % os.path.basename(blend)
    layer.Save()
    for aid, loc, rot in moved:
        print("  %-14s moved to %s rot %s" % (aid, loc, rot))
    print("wrote %s (%d asset%s overridden)" % (out, len(moved), "" if len(moved) == 1 else "s"))


if __name__ == "__main__":
    main()
