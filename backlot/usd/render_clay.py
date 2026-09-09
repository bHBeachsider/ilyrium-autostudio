#!/usr/bin/env python3
"""backlot.usd.render_clay - render a shot camera's clay view FROM THE USD STAGE (the "rebuilds from USD alone" check).

Imports the stage at the camera's set state, selects the camera prim by name, renders Workbench clay. This is the
first half of Phase 1's conditioning renderer (depth / normal / segmentation-ID passes are added there); today it
proves the stage, not the builder, is what a shot is rendered from.

usage: python3 -m backlot.usd.render_clay SHOT [SHOT ...] [--stage PATH] [--out DIR] [--variants fam=state,...]
"""
import json
import math
import os
import sys

import bpy
from pxr import Usd

HERE = os.path.dirname(os.path.abspath(__file__))


def _default(fam):
    from backlot.world.nh import geometry as G
    return G.STATE_FAMILIES[fam]["default"]


def main():
    a = sys.argv[1:]
    shots = [s for s in a if not s.startswith("--") and s not in a[a.index("--stage") + 1:a.index("--stage") + 2] if "--stage" in a] if "--stage" in a else [s for s in a if not s.startswith("--")]
    shots = [s for s in shots if s not in (a[a.index("--out") + 1:a.index("--out") + 2] if "--out" in a else [])]
    stage_path = a[a.index("--stage") + 1] if "--stage" in a else os.path.join(HERE, "nh", "NewHarnomy_square.usda")
    out = a[a.index("--out") + 1] if "--out" in a else os.path.join(HERE, "nh", "renders")
    os.makedirs(out, exist_ok=True)
    cams = json.load(open(os.path.join(os.path.dirname(stage_path), "derived", "cameras.json")))["cameras"]
    sv = os.path.join(os.path.dirname(stage_path), "derived", "survey_cameras.json")      # survey cameras render too
    if os.path.exists(sv):
        cams = dict(json.load(open(sv))["cameras"], **cams)
    # --variants fam=state,... overrides what the camera asks for. Survey cameras carry no variants at all, so this is
    # the only way to look at a stateful asset in a state other than its default (added 2026-09-09 for LysteriaInterior).
    override = dict(kv.split("=", 1) for kv in a[a.index("--variants") + 1].split(",")) if "--variants" in a else {}
    shots = [s for s in shots if s not in override.values() and "=" not in s]
    st = Usd.Stage.Open(stage_path)
    for shot in shots:
        cam = cams[shot]
        vsets = st.GetPrimAtPath("/World").GetVariantSets()
        vsets.GetVariantSet("build").SetVariantSelection(override.get("build") or cam.get("set_state", "finished"))
        for fam, spec in [(f, None) for f in vsets.GetNames() if f not in ("build", "weather")]:
            vsets.GetVariantSet(fam).SetVariantSelection(override.get(fam) or cam.get("variants", {}).get(fam) or _default(fam))
        st.GetRootLayer().Save()
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.wm.usd_import(filepath=stage_path, import_cameras=True, import_meshes=True, import_materials=True,
                              read_mesh_colors=True, import_usd_preview=True, set_frame_range=False)
        scene = bpy.context.scene
        camobj = bpy.data.objects.get(shot)
        if camobj is None or camobj.type != "CAMERA":
            sys.exit("camera %s not found after import" % shot)
        scene.camera = camobj
        scene.render.engine = "BLENDER_WORKBENCH"
        sh = scene.display.shading; sh.light = "STUDIO"; sh.color_type = "MATERIAL"; sh.show_shadows = True; sh.show_cavity = True
        scene.view_settings.view_transform = "Standard"
        scene.world = bpy.data.worlds.new("w"); scene.world.color = (0.75, 0.80, 0.86)
        scene.render.resolution_x, scene.render.resolution_y = cam["res"]; scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = os.path.join(out, "clay_%s.png" % shot)
        bpy.ops.render.render(write_still=True)
        print("rendered %s from the USD stage (state=%s)" % (scene.render.filepath, cam.get("set_state", "finished")))


if __name__ == "__main__":
    main()
