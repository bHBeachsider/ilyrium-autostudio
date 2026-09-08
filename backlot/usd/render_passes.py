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
}
PREFIX = [("truss_post", "post"), ("truss_beam", "beam"), ("deck", "deck"), ("joist", "deck"), ("rim_", "deck"),
          ("pier_", "deck"), ("chair", "chair"), ("podium", "podium"), ("steps_", "steps"), ("step_", "building"),
          ("portrait", "prop"), ("banner", "text_plane"), ("pilf_sign", "text_plane"), ("tree", "vegetation"),
          ("crown", "vegetation"), ("uni_tree", "vegetation"), ("uni_quad", "vegetation"), ("flatbed", "vehicle"),
          ("box_van", "vehicle"), ("lumber", "prop"), ("bodega_crate", "prop"), ("bodega_awning", "prop"),
          ("paving", "paving"), ("north_road", "paving"), ("axis_road", "paving"), ("north_kerb", "paving"),
          ("axis_kerb", "paving"), ("ground", "ground")]


def classify(name):
    n = name.lower()
    for p, c in PREFIX:
        if n.startswith(p):
            return c
    return "building"


def git_hash():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              cwd=os.path.join(HERE, "..", "..")).stdout.strip() or "unversioned"
    except Exception:
        return "unversioned"


def render_shot(shot, stage_path, out, near, far):
    cams = json.load(open(os.path.join(os.path.dirname(stage_path), "derived", "cameras.json")))["cameras"]
    cam = cams[shot]
    st = Usd.Stage.Open(stage_path)
    st.GetPrimAtPath("/World").GetVariantSets().GetVariantSet("build").SetVariantSelection(cam.get("set_state", "finished"))
    st.GetRootLayer().Save()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.usd_import(filepath=stage_path, import_cameras=True, import_meshes=True, import_materials=True,
                          read_mesh_colors=True, import_usd_preview=True, set_frame_range=False)
    scene = bpy.context.scene
    scene.camera = bpy.data.objects[shot]
    scene.render.resolution_x, scene.render.resolution_y = cam["res"]; scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    d = os.path.join(out, shot); os.makedirs(d, exist_ok=True)

    # ---- clay + lineart (Workbench)
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading; sh.light = "STUDIO"; sh.color_type = "MATERIAL"; sh.show_shadows = True; sh.show_cavity = True
    scene.world = bpy.data.worlds.new("w"); scene.world.color = (0.75, 0.80, 0.86)
    scene.render.image_settings.file_format = "PNG"; scene.render.image_settings.color_depth = "8"
    scene.render.filepath = os.path.join(d, "clay.png"); bpy.ops.render.render(write_still=True)
    sh.light = "FLAT"; sh.color_type = "SINGLE"; sh.single_color = (1, 1, 1); sh.show_shadows = False; sh.show_cavity = False
    sh.show_object_outline = True; sh.object_outline_color = (0, 0, 0)
    scene.world.color = (1, 1, 1)
    scene.render.filepath = os.path.join(d, "lineart.png"); bpy.ops.render.render(write_still=True)

    # ---- segmentation-ID (Workbench, flat, one emission-free colour per class via object colour)
    sh.color_type = "OBJECT"
    seg_counts = {}
    for o in bpy.data.objects:
        if o.type == "MESH":
            c = classify(o.name); seg_counts[c] = seg_counts.get(c, 0) + 1
            r, g, b = SEG_CLASSES[c]; o.color = (r / 255.0, g / 255.0, b / 255.0, 1.0)
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

    for fname, fmt, depth, mode, build in (("depth.png", "PNG", "16", "BW", depth_nodes),
                                           ("depth.exr", "OPEN_EXR", "32", "BW", depthraw_nodes),
                                           ("normal.png", "PNG", "8", "RGB", normal_nodes)):
        vl.material_override = override(fname, build)
        ims = scene.render.image_settings; ims.file_format = fmt; ims.color_depth = depth; ims.color_mode = mode
        if fmt == "OPEN_EXR":
            ims.exr_codec = "ZIP"
        scene.render.filepath = os.path.join(d, fname); bpy.ops.render.render(write_still=True)
    vl.material_override = None
    meta = dict(shot=shot, camera=cam, set_state=cam.get("set_state", "finished"), near_m=near, far_m=far,
                seg_classes=SEG_CLASSES, seg_counts=seg_counts, world_version=git_hash(),
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
    skip = set(); [skip.update([a[i + 1]]) for i, t in enumerate(a) if t in ("--stage", "--out", "--near", "--far")]
    shots = [s for s in a if not s.startswith("--") and s not in skip]
    for s in shots:
        print("passes for %s -> %s" % (s, render_shot(s, stage_path, out, near, far)), flush=True)


if __name__ == "__main__":
    main()
