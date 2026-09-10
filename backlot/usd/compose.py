#!/usr/bin/env python3
"""backlot.usd.compose - turn the exported geometry layers into referenced, variant-bearing assets and a stage.

Writes (under --out, default backlot/usd/nh):
    assets/<AssetId>/<AssetId>.usda   the asset: an Xform prim referencing geo.usda, or carrying a variantSet
                                      "build" whose variants each reference one geo_<state>.usda
    cameras.usda                      /World/Cameras/<SHOT>: UsdGeomCamera prims with custom backlot:* attrs
    NewHarnomy_square.usda            THE STAGE: /World referencing every asset, a "build" variantSet on /World
                                      that selects the same state on every stateful asset, a "weather" variantSet,
                                      control points inside the assets that own them, /World/Cameras via a sublayer,
                                      overrides/readback.usda as the strongest sublayer when Blender edits exist

The stage is the source of truth from here on. cameras.json and control_points.json are DERIVED from it
(derive.py) and must never be edited by hand again.
usage: python3 -m backlot.usd.compose [--out DIR]
"""
import os
import sys

from pxr import Gf, Sdf, Usd, UsdGeom, Vt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from backlot.world.nh import geometry as G                      # noqa: E402
from backlot.world.nh import cameras as C                       # noqa: E402

WEATHER_STATES = ["first_light", "overcast_drizzle", "dusk"]


def author_asset(out, aid):
    adir = os.path.join(out, "assets", aid)
    path = os.path.join(adir, aid + ".usda")
    stage = Usd.Stage.CreateNew(path)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/" + aid)
    stage.SetDefaultPrim(root.GetPrim())
    root.GetPrim().SetMetadata("kind", "component")
    root.GetPrim().CreateAttribute("backlot:asset_id", Sdf.ValueTypeNames.String).Set(aid)
    root.GetPrim().CreateAttribute("backlot:grade", Sdf.ValueTypeNames.Token).Set("conditioning")
    states = G.STATEFUL.get(aid)
    if not states:
        root.GetPrim().GetReferences().AddReference("./geo.usda", "/geo")
    else:
        vs = root.GetPrim().GetVariantSets().AddVariantSet("build")
        for st in states:
            vs.AddVariant(st)
            vs.SetVariantSelection(st)
            with vs.GetVariantEditContext():
                root.GetPrim().GetReferences().AddReference("./geo_%s.usda" % st, "/geo")
        vs.SetVariantSelection(states[-1])
    # control points for the geometry gate belong to the asset (RallyStage owns the posts and the deck line), so a
    # transform override on the asset prim moves the geometry AND the points the gate projects
    if aid in G.CONTROL_POINTS_BY_ASSET:
        cp = G.CONTROL_POINTS_BY_ASSET[aid]
        UsdGeom.Scope.Define(stage, "/%s/ControlPoints" % aid)
        for post in cp.get("posts", []):
            p = UsdGeom.Xform.Define(stage, "/%s/ControlPoints/%s" % (aid, post["name"])).GetPrim()
            p.CreateAttribute("backlot:kind", Sdf.ValueTypeNames.Token).Set("post")
            p.CreateAttribute("backlot:base", Sdf.ValueTypeNames.Double3).Set(Gf.Vec3d(*post["base"]))
            p.CreateAttribute("backlot:top", Sdf.ValueTypeNames.Double3).Set(Gf.Vec3d(*post["top"]))
        for name, key in (("deck_front", ("left", "right")), ("chair_band", ("top_left", "bottom_right")),
                          ("truss_beam", ("left", "right"))):
            if name not in cp:
                continue
            p = UsdGeom.Xform.Define(stage, "/%s/ControlPoints/%s" % (aid, name)).GetPrim()
            p.CreateAttribute("backlot:kind", Sdf.ValueTypeNames.Token).Set("segment")
            p.CreateAttribute("backlot:a", Sdf.ValueTypeNames.Double3).Set(Gf.Vec3d(*cp[name][key[0]]))
            p.CreateAttribute("backlot:b", Sdf.ValueTypeNames.Double3).Set(Gf.Vec3d(*cp[name][key[1]]))
            p.CreateAttribute("backlot:a_name", Sdf.ValueTypeNames.String).Set(key[0])
            p.CreateAttribute("backlot:b_name", Sdf.ValueTypeNames.String).Set(key[1])
        for mk in cp.get("marks", []):
            p = UsdGeom.Xform.Define(stage, "/%s/ControlPoints/mark_%s" % (aid, mk["name"])).GetPrim()
            p.CreateAttribute("backlot:kind", Sdf.ValueTypeNames.Token).Set("mark")
            p.CreateAttribute("backlot:pos", Sdf.ValueTypeNames.Double3).Set(Gf.Vec3d(*mk["pos"]))
            p.CreateAttribute("backlot:facing_deg", Sdf.ValueTypeNames.Double).Set(float(mk["facing_deg"]))
            p.CreateAttribute("backlot:posture", Sdf.ValueTypeNames.Token).Set(mk.get("posture", "standing"))
        for tp in cp.get("text_planes", []):
            p = UsdGeom.Xform.Define(stage, "/%s/ControlPoints/%s" % (aid, tp["name"])).GetPrim()
            p.CreateAttribute("backlot:kind", Sdf.ValueTypeNames.Token).Set("text_plane")
            p.CreateAttribute("backlot:corners", Sdf.ValueTypeNames.Double3Array).Set([Gf.Vec3d(*c) for c in tp["corners"]])
            p.CreateAttribute("backlot:text", Sdf.ValueTypeNames.StringArray).Set(list(tp["text"]))
    stage.GetRootLayer().Save()
    return path


def author_cameras(out):
    path = os.path.join(out, "cameras.usda")
    stage = Usd.Stage.CreateNew(path)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.Xform.Define(stage, "/World")
    UsdGeom.Scope.Define(stage, "/World/Cameras")
    for group, table in (("shot", C.SHOT_CAMERAS), ("survey", C.SURVEY_CAMERAS)):
        for name, cam in table.items():
            c = UsdGeom.Camera.Define(stage, "/World/Cameras/" + name)
            rot = C.rotation_deg(cam["loc"], cam["target"])
            xf = c.AddTranslateOp(); xf.Set(Gf.Vec3d(*cam["loc"]))
            r = c.AddRotateXYZOp(); r.Set(Gf.Vec3f(*rot))
            c.GetFocalLengthAttr().Set(float(cam["lens"]))
            c.GetHorizontalApertureAttr().Set(36.0)
            c.GetVerticalApertureAttr().Set(36.0 * cam["res"][1] / cam["res"][0])
            c.GetClippingRangeAttr().Set(Gf.Vec2f(0.1, 2000.0))
            p = c.GetPrim()
            p.CreateAttribute("backlot:role", Sdf.ValueTypeNames.Token).Set(group)
            p.CreateAttribute("backlot:resolution", Sdf.ValueTypeNames.Int2).Set(Gf.Vec2i(*cam["res"]))
            p.CreateAttribute("backlot:target", Sdf.ValueTypeNames.Double3).Set(Gf.Vec3d(*cam["target"]))
            if name in C.SHOT_STATES:
                p.CreateAttribute("backlot:set_state", Sdf.ValueTypeNames.Token).Set(C.SHOT_STATES[name])
            p.CreateAttribute("backlot:depth_mode", Sdf.ValueTypeNames.Token).Set(getattr(C, "DEPTH_MODE", {}).get(name, "linear"))
            p.CreateAttribute("backlot:interior", Sdf.ValueTypeNames.Bool).Set(name in getattr(C, "INTERIOR_SHOTS", set()))
            if name in getattr(C, "SHOT_VARIANTS", {}):
                p.CreateAttribute("backlot:variants", Sdf.ValueTypeNames.String).Set(
                    ";".join("%s=%s" % kv for kv in sorted(C.SHOT_VARIANTS[name].items())))
    stage.GetRootLayer().Save()
    return path


def author_stage(out, assets):
    path = os.path.join(out, "NewHarnomy_square.usda")
    stage = Usd.Stage.CreateNew(path)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    world.GetPrim().SetMetadata("kind", "assembly")
    wp = world.GetPrim()
    wp.CreateAttribute("backlot:production", Sdf.ValueTypeNames.String).Set("NEW HARNOMY, U.S.A.")
    wp.CreateAttribute("backlot:origin", Sdf.ValueTypeNames.String).Set(
        "centre of City Hall's portico semicircle at pavement level; +X along the facade to the right, +Y into the square, +Z up")
    # every asset, referenced at identity (authored in world space for this production)
    for aid in assets:
        prim = UsdGeom.Xform.Define(stage, "/World/" + aid)
        prim.GetPrim().GetReferences().AddReference("./assets/%s/%s.usda" % (aid, aid))
    # one variantSet per state family on /World; each drives only its own assets (geometry.STATE_FAMILIES)
    for fam, spec in G.STATE_FAMILIES.items():
        vs = wp.GetVariantSets().AddVariantSet(fam)
        for st in spec["states"]:
            vs.AddVariant(st)
            vs.SetVariantSelection(st)
            with vs.GetVariantEditContext():
                for aid in spec["assets"]:
                    child = stage.GetPrimAtPath("/World/" + aid)
                    if not child:
                        continue
                    if st in G.STATEFUL.get(aid, []):
                        child.SetActive(True)
                        child.GetVariantSets().GetVariantSet("build").SetVariantSelection(st)
                    else:
                        child.SetActive(False)        # "none", or a state this asset has no geometry for
        vs.SetVariantSelection(spec["default"])
    # weather / time of day: a state that lighting and generation read; geometry does not change
    wv = wp.GetVariantSets().AddVariantSet("weather")
    for w in WEATHER_STATES:
        wv.AddVariant(w)
        wv.SetVariantSelection(w)
        with wv.GetVariantEditContext():
            wp.CreateAttribute("backlot:weather", Sdf.ValueTypeNames.Token).Set(w)
    wv.SetVariantSelection("overcast_drizzle")
    # cameras ride in as a sublayer so they can be edited without touching the world
    stage.GetRootLayer().subLayerPaths.append("./cameras.usda")
    # hand edits from Blender (readback.py) come in as the STRONGEST sublayer, so a moved asset wins over the code
    if os.path.exists(os.path.join(out, "overrides", "readback.usda")):
        stage.GetRootLayer().subLayerPaths.insert(0, "./overrides/readback.usda")
    stage.GetRootLayer().Save()
    return path


def main():
    args = sys.argv[1:]
    out = args[args.index("--out") + 1] if "--out" in args else os.path.join(HERE, "nh")
    assets = sorted(d for d in os.listdir(os.path.join(out, "assets")) if os.path.isdir(os.path.join(out, "assets", d)))
    for aid in assets:
        author_asset(out, aid)
    author_cameras(out)
    author_stage(out, assets)
    # prove it composes
    st = Usd.Stage.Open(os.path.join(out, "NewHarnomy_square.usda"))
    n = sum(1 for _ in st.Traverse())
    vs = st.GetPrimAtPath("/World").GetVariantSets()
    print("stage composes: %d prims; %s weather=%s; assets: %s" % (
        n, " ".join("%s=%s" % (f, vs.GetVariantSet(f).GetVariantSelection()) for f in G.STATE_FAMILIES),
        vs.GetVariantSet("weather").GetVariantSelection(), ", ".join(assets)))


if __name__ == "__main__":
    main()
