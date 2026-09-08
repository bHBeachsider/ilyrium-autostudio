#!/usr/bin/env python3
"""backlot.usd.derive - DERIVE cameras.json and control_points.json from the USD stage.

These two files are what the geometry gate and the conditioning renderer consume. From Phase 0 on they are outputs
of the stage, never inputs: edit the stage (or the camera table that authors it), rerun this, commit both.

usage: python3 -m backlot.usd.derive [--stage PATH] [--out DIR]
"""
import json
import os
import sys

from pxr import Gf, Usd, UsdGeom

HERE = os.path.dirname(os.path.abspath(__file__))


def derive(stage_path, out):
    st = Usd.Stage.Open(stage_path)
    cams, survey = {}, {}
    for p in Usd.PrimRange(st.GetPrimAtPath("/World/Cameras")):
        if not p.IsA(UsdGeom.Camera):
            continue
        c = UsdGeom.Camera(p)
        ops = {o.GetOpName(): o.Get() for o in c.GetOrderedXformOps()}
        loc = ops["xformOp:translate"]; rot = ops["xformOp:rotateXYZ"]
        res = p.GetAttribute("backlot:resolution").Get()
        rec = dict(location=[round(float(v), 3) for v in loc],
                   rotation_deg=[round(float(v), 2) for v in rot],
                   lens_mm=float(c.GetFocalLengthAttr().Get()),
                   sensor_mm=float(c.GetHorizontalApertureAttr().Get()),
                   res=[int(res[0]), int(res[1])])
        vv = p.GetAttribute("backlot:variants")
        if vv and vv.Get():
            rec["variants"] = dict(kv.split("=") for kv in str(vv.Get()).split(";"))
        ss = p.GetAttribute("backlot:set_state")
        if ss and ss.Get():
            rec["set_state"] = str(ss.Get())
        (cams if p.GetAttribute("backlot:role").Get() == "shot" else survey)[p.GetName()] = rec
    control = {"posts": [], "text_planes": [], "marks": []}
    xc = UsdGeom.XformCache()
    def W(prim, v):                                   # a point authored in the asset, carried by the asset's world xform
        m = xc.GetLocalToWorldTransform(prim)
        r = m.Transform(Gf.Vec3d(*v))
        return [round(float(x), 4) for x in r]
    for p in st.Traverse():
        kind = p.GetAttribute("backlot:kind")
        if not kind or not kind.Get():
            continue
        if kind.Get() == "post":
            control["posts"].append({"name": p.GetName(), "base": W(p, p.GetAttribute("backlot:base").Get()),
                                     "top": W(p, p.GetAttribute("backlot:top").Get())})
        elif kind.Get() == "mark":
            control["marks"].append({"name": p.GetName()[5:], "asset": p.GetPath().pathString.split("/")[1],
                                     "pos": W(p, p.GetAttribute("backlot:pos").Get()),
                                     "facing_deg": float(p.GetAttribute("backlot:facing_deg").Get()),
                                     "posture": str(p.GetAttribute("backlot:posture").Get())})
        elif kind.Get() == "text_plane":
            control["text_planes"].append({"name": p.GetName(),
                                           "corners": [W(p, c) for c in p.GetAttribute("backlot:corners").Get()],
                                           "text": [str(t) for t in p.GetAttribute("backlot:text").Get()]})
        elif kind.Get() == "segment":
            control[p.GetName()] = {str(p.GetAttribute("backlot:a_name").Get()): W(p, p.GetAttribute("backlot:a").Get()),
                                    str(p.GetAttribute("backlot:b_name").Get()): W(p, p.GetAttribute("backlot:b").Get())}
    w = st.GetPrimAtPath("/World")
    meta = {"stage": os.path.relpath(stage_path, out) if out else stage_path,
            "build": w.GetVariantSets().GetVariantSet("build").GetVariantSelection(),
            "weather": w.GetVariantSets().GetVariantSet("weather").GetVariantSelection(),
            "cameras": cams}
    os.makedirs(out, exist_ok=True)
    json.dump(meta, open(os.path.join(out, "cameras.json"), "w"), indent=1)
    json.dump({"cameras": survey}, open(os.path.join(out, "survey_cameras.json"), "w"), indent=1)
    json.dump(control, open(os.path.join(out, "control_points.json"), "w"), indent=1)
    return meta, control


def main():
    args = sys.argv[1:]
    stage = args[args.index("--stage") + 1] if "--stage" in args else os.path.join(HERE, "nh", "NewHarnomy_square.usda")
    out = args[args.index("--out") + 1] if "--out" in args else os.path.join(HERE, "nh", "derived")
    meta, control = derive(stage, out)
    print("derived %d shot cameras, %d posts, %d text planes -> %s" % (len(meta["cameras"]), len(control["posts"]), len(control["text_planes"]), out))


if __name__ == "__main__":
    main()
