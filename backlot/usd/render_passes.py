#!/usr/bin/env python3
"""backlot.usd.render_passes - conditioning passes for one shot camera, FROM THE STAGE.

Per shot (at the camera's set state) writes:
    passes/<SHOT>/clay.png      Workbench clay - the human reference and the gate's comparison sheet
    passes/<SHOT>/depth.png     16-bit, near=white far=black, normalised over [--near, --far] metres - the ControlNet input
    passes/<SHOT>/depth.exr     raw metric depth (Z) for anything that wants numbers
    passes/<SHOT>/normal.png    camera-space normals encoded RGB
    passes/<SHOT>/seg.png       segmentation-ID: one flat colour per class (deck, post, beam, chair, building, paving,
                                text_plane, vegetation, vehicle, prop, ground) - the gate's IoU reference
    passes/<SHOT>/lineart.png   Workbench outline pass (Freestyle-free) for canny-type conditioning
    passes/<SHOT>/passes.json   the camera, state, class colours and the world version these came from

Classes are assigned from the object name prefix and asset id, so a new object is classified by naming it; anything
unknown is 'prop'. Depth/normal are emitted by override materials under Cycles CPU (1 sample), so nothing needs a GPU or the compositor.

usage: python3 -m backlot.usd.render_passes SHOT [SHOT ...] [--stage PATH] [--out DIR] [--near 2] [--far 120]
"""
import json
import os
import subprocess
import sys

import bpy
from pxr import Usd

HERE = os.path.dirname(os.path.abspath(__file__))

SEG_CLASSES = {                      # class -> flat colour (sRGB 0-255); order matters for prefix matching
    "post":       (255, 40, 40),
    "beam":       (255, 140, 0),
    "deck":       (255, 220, 0),
    "chair":      (0, 200, 255),
    "podium":     (0, 120, 255),
    "steps":      (200, 0, 255),
    "text_plane": (255, 0, 160),
    "building":   (140, 140, 140),
    "paving":     (60, 60, 70),
    "vegetation": (40, 160, 60),
    "vehicle":    (230, 230, 230),
    "prop":       (120, 80, 40),
    "ground":     (20, 20, 25),
    "person":     (255, 255, 255),
    "dressing":   (0, 255, 120),
    "furniture":  (170, 110, 60),
}
PREFIX = [("man_", "person"), ("dress_", "dressing"), ("lyst_chair", "chair"), ("po_drape", "prop"), ("po_book", "prop"), ("po_lamp", "prop"),
          ("po_cup", "prop"), ("po_newspaper", "prop"), ("po_portrait", "text_plane"), ("po_desk", "furniture"),
          ("po_credenza", "furniture"), ("po_door", "furniture"), ("po_", "building"), ("pilf_table", "furniture"),
          ("pilf_petition", "furniture"), ("pilf_wall_board", "text_plane"), ("pilf_in", "building"), ("lyst_desk", "furniture"),
          ("lyst_conf", "furniture"), ("lyst_mission", "text_plane"), ("lyst_wordmark", "text_plane"), ("lyst_nameplate", "text_plane"),
          ("lyst_mbc_board", "text_plane"), ("lyst_glass", "building"), ("lyst_reception", "furniture"), ("lyst_bench", "furniture"),
          ("lyst_sofa", "furniture"), ("lyst_coffee", "furniture"), ("lyst_staff_chair", "chair"), ("lyst_reception_chair", "chair"),
          ("lyst_photo", "prop"), ("lyst_gallery", "prop"), ("lyst_pendant", "prop"), ("lyst_sash", "text_plane"),
          ("lyst_board_table", "furniture"), ("lyst_board_credenza", "furniture"), ("lyst_board_chair", "chair"),
          ("lyst_board_banner", "text_plane"), ("lyst_board_pendant", "prop"), ("lyst_board", "building"),
          ("lyst_banner_cloth", "text_plane"), ("lyst_plaque", "text_plane"), ("lyst_sash", "text_plane"),
          ("lyst_credenza", "furniture"), ("lyst_shelf", "furniture"), ("lyst_visitor", "chair"),
          ("lyst_book", "prop"), ("lyst_lamp", "prop"), ("lyst_cup", "prop"), ("lyst_bottle", "prop"),
          ("lyst_docbox", "prop"), ("lyst_papers", "prop"), ("lyst_tote", "prop"), ("lyst_mbc_carton", "prop"),
          ("lyst_ghost", "prop"), ("lyst_easel", "prop"), ("lyst_banner_frame", "prop"), ("lyst_in", "building"),
          ("truss_post", "post"), ("truss_beam", "beam"), ("deck", "deck"), ("joist", "deck"), ("rim_", "deck"),
          ("pier_", "deck"), ("chair", "chair"), ("podium", "podium"), ("steps_", "steps"), ("step_", "building"),
          ("portrait", "prop"), ("banner", "text_plane"), ("pilf_sign", "text_plane"), ("tree", "vegetation"),
          ("crown", "vegetation"), ("uni_tree", "vegetation"), ("uni_quad", "vegetation"), ("flatbed", "vehicle"),
          ("box_van", "vehicle"), ("lumber", "prop"), ("bodega_crate", "prop"), ("bodega_awning", "prop"),
          ("paving", "paving"), ("north_road", "paving"), ("axis_road", "paving"), ("north_kerb", "paving"),
          ("axis_kerb", "paving"), ("ground", "ground")]


def _srgb_to_linear(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def classify(name):
    n = name.lower()
    for p, c in PREFIX:
        if n.startswith(p):
            return c
    return "building"


def git_hash(stage_path=None):
    """The world's version: the repo's commit when there is one, else a content hash of the composed stage - so a
    take made outside the repo (a scratch checkout, the box) still names the exact world it came from."""
    try:
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                           cwd=os.path.join(HERE, "..", "..")).stdout.strip()
        if h:
            return h
    except Exception:
        pass
    if stage_path and os.path.exists(stage_path):
        import hashlib
        return "usda:" + hashlib.sha256(open(stage_path, "rb").read()).hexdigest()[:12]
    return "unversioned"


def render_shot(shot, stage_path, out, near, far, variants=None, depth_mode=None):
    cams = json.load(open(os.path.join(os.path.dirname(stage_path), "derived", "cameras.json")))["cameras"]
    cam = cams[shot]
    depth_mode = depth_mode or cam.get("depth_mode", "linear")      # per camera (world/nh/cameras.py DEPTH_MODE)
    st = Usd.Stage.Open(stage_path)
    vsets = st.GetPrimAtPath("/World").GetVariantSets()
    vsets.GetVariantSet("build").SetVariantSelection(cam.get("set_state", "finished"))
    from backlot.world.nh import geometry as G
    sel = dict(cam.get("variants", {})); sel.update(variants or {})       # the agent's resolved request wins over the camera's default
    if "build" in sel:
        vsets.GetVariantSet("build").SetVariantSelection(sel["build"])
    for fam in vsets.GetNames():
        if fam in G.STATE_FAMILIES and fam != "build":
            vsets.GetVariantSet(fam).SetVariantSelection(sel.get(fam) or G.STATE_FAMILIES[fam]["default"])
    if "weather" in sel and vsets.HasVariantSet("weather"):
        vsets.GetVariantSet("weather").SetVariantSelection(sel["weather"])
    st.GetRootLayer().Save()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.usd_import(filepath=stage_path, import_cameras=True, import_meshes=True, import_materials=True,
                          read_mesh_colors=True, import_usd_preview=True, set_frame_range=False)
    scene = bpy.context.scene
    scene.camera = bpy.data.objects[shot]
    scene.render.resolution_x, scene.render.resolution_y = cam["res"]; scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    d = os.path.join(out, shot); os.makedirs(d, exist_ok=True)

    # glass: the clay sees through it (viewport alpha); lineart, seg, depth and normal do not see it at all - a pane is
    # not a wall, a depth pass that stops at LYSTERIA's glass wall would condition a solid partition, and the outline
    # pass cannot draw what is behind it (2026-09-09)
    glass = [o for o in bpy.data.objects if o.type == "MESH" and any(sl.material and sl.material.name.lower().startswith("glass") for sl in o.material_slots)]
    for m in bpy.data.materials:
        if m.name.lower().startswith("glass"):
            m.diffuse_color = (*m.diffuse_color[:3], 0.22)

    # ---- clay + lineart (Workbench)
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading; sh.light = "STUDIO"; sh.color_type = "MATERIAL"; sh.show_shadows = True; sh.show_cavity = True
    scene.world = bpy.data.worlds.new("w"); scene.world.color = (0.75, 0.80, 0.86)
    scene.render.image_settings.file_format = "PNG"; scene.render.image_settings.color_depth = "8"
    scene.render.filepath = os.path.join(d, "clay.png"); bpy.ops.render.render(write_still=True)
    # lineart: Workbench's outline pass loses every object BEHIND a transparent surface (LYSTERIA's glass wall blanked the
    # whole office, 2026-09-09) - and the edge control is this image inverted. Glass is hidden from here on; the mullions,
    # head and sill still draw the wall's line.
    for o in glass:
        o.hide_render = True
    sh.light = "FLAT"; sh.color_type = "SINGLE"; sh.single_color = (1, 1, 1); sh.show_shadows = False; sh.show_cavity = False
    sh.show_object_outline = True; sh.object_outline_color = (0, 0, 0)
    scene.world.color = (1, 1, 1)
    scene.render.filepath = os.path.join(d, "lineart.png"); bpy.ops.render.render(write_still=True)

    # ---- segmentation-ID (Workbench, flat, one emission-free colour per class via object colour); glass stays hidden
    sh.color_type = "OBJECT"
    seg_counts = {}
    for o in bpy.data.objects:
        if o.type == "MESH":
            c = classify(o.name); seg_counts[c] = seg_counts.get(c, 0) + 1
            # object colour is linear; the PNG goes through the Standard (sRGB) view, so pre-invert the transfer
            # function and the file holds exactly the SEG_CLASSES value the verifiers match on
            o.color = tuple(_srgb_to_linear(v / 255.0) for v in SEG_CLASSES[c]) + (1.0,)
    scene.world.color = (0, 0, 0)
    scene.render.filepath = os.path.join(d, "seg.png"); bpy.ops.render.render(write_still=True)

    # ---- depth + normal (Cycles CPU, 1 sample, material override; no compositor - Blender 5 moved it to a
    #      node-group datablock and Eevee needs a GPU headless, so shader-emitted passes are the robust path)
    scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"; scene.cycles.samples = 1
    scene.cycles.use_denoising = False; scene.cycles.use_adaptive_sampling = False
    scene.cycles.max_bounces = 0; scene.render.film_transparent = False
    scene.view_settings.view_transform = "Raw"; scene.view_settings.look = "None"
    scene.world.color = (0, 0, 0)
    vl = scene.view_layers[0]

    def override(name, build):
        m = bpy.data.materials.new(name); m.use_nodes = True
        nt = m.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        outn = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Strength"].default_value = 1.0
        nt.links.new(build(nt), em.inputs["Color"]); nt.links.new(em.outputs[0], outn.inputs["Surface"])
        return m

    # depth: (far - z) / (far - near) clamped 0..1 -> near white, far black, 16-bit PNG; raw z in EXR
    def depth_nodes(nt):
        cd = nt.nodes.new("ShaderNodeCameraData")  # outputs: View Vector, View Z Depth, View Distance
        sub = nt.nodes.new("ShaderNodeMath"); sub.operation = "SUBTRACT"; sub.inputs[0].default_value = float(far)
        nt.links.new(cd.outputs["View Z Depth"], sub.inputs[1])
        div = nt.nodes.new("ShaderNodeMath"); div.operation = "DIVIDE"; div.inputs[1].default_value = float(far - near)
        nt.links.new(sub.outputs[0], div.inputs[0])
        cl = nt.nodes.new("ShaderNodeClamp"); nt.links.new(div.outputs[0], cl.inputs["Value"])
        return cl.outputs[0]

    def depthraw_nodes(nt):
        cd = nt.nodes.new("ShaderNodeCameraData"); return cd.outputs["View Z Depth"]

    # normal: camera-space shading normal remapped -1..1 -> 0..1 (x right, y up, z toward camera = blue; Cycles'
    # camera space points +Z away from the camera, so Z is flipped to the ControlNet/Bae convention)
    def normal_nodes(nt):
        g = nt.nodes.new("ShaderNodeNewGeometry")
        vt = nt.nodes.new("ShaderNodeVectorTransform"); vt.vector_type = "NORMAL"
        vt.convert_from = "WORLD"; vt.convert_to = "CAMERA"
        nt.links.new(g.outputs["Normal"], vt.inputs[0])
        vm = nt.nodes.new("ShaderNodeVectorMath"); vm.operation = "MULTIPLY_ADD"
        vm.inputs[1].default_value = (0.5, 0.5, -0.5); vm.inputs[2].default_value = (0.5, 0.5, 0.5)
        nt.links.new(vt.outputs[0], vm.inputs[0])
        return vm.outputs[0]

    for fname, fmt, depth, mode, build in (("depth.exr", "OPEN_EXR", "32", "BW", depthraw_nodes),
                                           ("normal.png", "PNG", "8", "RGB", normal_nodes)):
        vl.material_override = override(fname, build)
        ims = scene.render.image_settings; ims.file_format = fmt; ims.color_depth = depth; ims.color_mode = mode
        if fmt == "OPEN_EXR":
            ims.exr_codec = "ZIP"
        scene.render.filepath = os.path.join(d, fname); bpy.ops.render.render(write_still=True)
    # depth.png: the raw metres from the EXR, normalised to THIS frame's range (1st..99th percentile of what is in
    # view) as INVERSE depth, so an interior (1-8 m) and the square (5-120 m) both fill the 16-bit range - a fixed
    # linear near/far made every office depth pass near-white (2026-09-08). near_m/far_m in passes.json record the range.
    import numpy as np
    from PIL import Image
    img = bpy.data.images.load(os.path.join(d, "depth.exr"))
    px = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], img.channels)[::-1, :, 0]
    bpy.data.images.remove(img)
    clip0 = float(scene.camera.data.clip_start)
    valid = np.isfinite(px) & (px < 1e6) & (px > clip0 * 1.05)     # Cycles returns clip_start for background rays: that is "far"
    finite = px[valid]
    if finite.size:
        near, far = float(np.percentile(finite, 1.0)), float(np.percentile(finite, 99.0))
        if far - near < 0.5:
            far = near + 0.5
    z = np.where(valid, px, far)
    # inverse depth (disparity), the convention the depth ControlNets were trained on (MiDaS / Depth-Anything):
    # near white, far black, with the room's metres given most of the range even when a window shows the square
    if depth_mode == "linear":                                        # Phase 1a/1b were validated with this
        norm = np.clip((far - z) / (far - near), 0.0, 1.0)
    else:
        inv = 1.0 / np.clip(z, max(near, 0.05), None)
        norm = np.clip((inv - 1.0 / far) / (1.0 / max(near, 0.05) - 1.0 / far), 0.0, 1.0)
    Image.fromarray((norm * 65535.0).astype(np.uint16)).save(os.path.join(d, "depth.png"))
    vl.material_override = None
    meta = dict(shot=shot, camera=cam, set_state=sel.get("build", cam.get("set_state", "finished")), variants=sel, near_m=near, far_m=far,
                depth_mode=depth_mode,
                seg_classes=SEG_CLASSES, seg_counts=seg_counts, world_version=git_hash(stage_path),
                stage=os.path.relpath(stage_path, out))
    json.dump(meta, open(os.path.join(d, "passes.json"), "w"), indent=1)
    return d


def main():
    a = sys.argv[1:]
    def opt(k, default):
        return a[a.index(k) + 1] if k in a else default
    stage_path = opt("--stage", os.path.join(HERE, "nh", "NewHarnomy_square.usda"))
    out = opt("--out", os.path.join(HERE, "nh", "passes"))
    near, far = float(opt("--near", 2.0)), float(opt("--far", 120.0))
    variants = dict(kv.split("=") for kv in opt("--variants", "").split(",") if "=" in kv)
    depth_mode = opt("--depth-mode", None)
    skip = set(); [skip.update([a[i + 1]]) for i, t in enumerate(a) if t in ("--stage", "--out", "--near", "--far", "--variants", "--depth-mode")]
    shots = [s for s in a if not s.startswith("--") and s not in skip]
    for s in shots:
        print("passes for %s -> %s" % (s, render_shot(s, stage_path, out, near, far, variants, depth_mode)), flush=True)


if __name__ == "__main__":
    main()
