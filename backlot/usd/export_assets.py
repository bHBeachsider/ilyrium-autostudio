#!/usr/bin/env python3
"""backlot.usd.export_assets - author every asset in Blender and write one USD geometry layer per asset per state.

Output layout (under --out, default backlot/usd/nh):
    assets/<AssetId>/geo.usda                  stateless asset
    assets/<AssetId>/geo_<state>.usda          one layer per state of a stateful asset ('*' objects go in every one)

Geometry is exported with Blender's USD exporter, selected objects only, materials as display colour. Everything is
in world space (see geometry.py's coordinate contract). compose.py turns these layers into referenced, variant-bearing
asset prims and a stage; nothing here composes anything.

usage: python3 -m backlot.usd.export_assets [--out DIR] [--only AssetId ...]
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from backlot.world.nh import geometry as G     # noqa: E402


def _select(asset_id, state):
    bpy.ops.object.select_all(action="DESELECT")
    n = 0
    for o in bpy.data.objects:
        if o.get("backlot_asset") != asset_id:
            continue
        st = o.get("backlot_state", "*")
        if st == "*" or st == state:
            o.select_set(True); n += 1
    return n


def _export(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # the Mesh prim under each Xform is named after the mesh datablock; Blender's importer then names the merged
    # object after the Mesh prim ("Cube_041"), which strips the semantic name the passes renderer classifies on.
    # Name the datablock after the object so the name survives the USD round trip.
    for o in bpy.context.selected_objects:
        if o.type == "MESH" and o.data.name != o.name:
            o.data.name = o.name
    bpy.ops.wm.usd_export(filepath=path, selected_objects_only=True, export_materials=True,
                          export_uvmaps=False, export_normals=True, export_animation=False,
                          root_prim_path="/geo", convert_orientation=False)


def main():
    args = sys.argv[1:]
    out = args[args.index("--out") + 1] if "--out" in args else os.path.join(HERE, "nh")
    only = None
    if "--only" in args:
        i = args.index("--only"); only = set(a for a in args[i + 1:] if not a.startswith("--"))
    G.build_all()
    assets = sorted(set(o.get("backlot_asset") for o in bpy.data.objects if o.get("backlot_asset")))
    written = []
    for aid in assets:
        if only and aid not in only:
            continue
        states = G.STATEFUL.get(aid)
        if not states:
            n = _select(aid, "*")
            p = os.path.join(out, "assets", aid, "geo.usda"); _export(p); written.append((aid, "-", n, p))
        else:
            for st in states:
                n = _select(aid, st)
                p = os.path.join(out, "assets", aid, "geo_%s.usda" % st); _export(p); written.append((aid, st, n, p))
    for aid, st, n, p in written:
        print("%-16s %-12s %4d objects -> %s" % (aid, st, n, os.path.relpath(p, out)))


if __name__ == "__main__":
    main()
