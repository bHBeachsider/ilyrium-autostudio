#!/usr/bin/env python3
"""backlot.open_in_blender - import the USD stage into a .blend Brad can open, walk and edit by hand.

The import keeps the USD hierarchy: /World/<AssetId> becomes an Empty with the asset's meshes under it. Move THAT
Empty to move an asset; readback.py harvests the Empties' transforms into overrides/readback.usda, which the stage
sublayers as its strongest opinion. Moving individual meshes is not read back (the asset is the unit of edit).

usage: python3 -m backlot.open_in_blender [--stage PATH] [--build finished] [--out nh_backlot.blend]
"""
import os
import sys

import bpy
from pxr import Usd

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]   # `blender -b --python X.py -- args`
    stage_path = a[a.index("--stage") + 1] if "--stage" in a else os.path.join(HERE, "usd", "nh", "NewHarnomy_square.usda")
    build = a[a.index("--build") + 1] if "--build" in a else None
    out = a[a.index("--out") + 1] if "--out" in a else os.path.join(HERE, "usd", "nh", "nh_backlot.blend")
    if build:      # select the state on the stage's session-independent root layer before importing
        st = Usd.Stage.Open(stage_path)
        st.GetPrimAtPath("/World").GetVariantSets().GetVariantSet("build").SetVariantSelection(build)
        st.GetRootLayer().Save()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.ops.wm.usd_import(filepath=stage_path, import_cameras=True, import_meshes=True, import_materials=True,
                          read_mesh_colors=True, import_usd_preview=True, set_frame_range=False)
    # stamp every asset root Empty so readback can find it whatever Brad renames
    n = 0
    for o in bpy.data.objects:
        if o.type == "EMPTY" and o.parent is not None and o.parent.name == "World":
            o["backlot_asset_root"] = o.name; n += 1
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("wrote %s  (%d asset roots; build=%s)" % (out, n, build or "as authored"))


if __name__ == "__main__":
    main()
