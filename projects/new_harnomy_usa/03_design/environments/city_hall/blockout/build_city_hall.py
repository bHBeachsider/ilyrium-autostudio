#!/usr/bin/env python3
r"""build_city_hall.py - greybox blockout of the City Hall square (SET_BIBLE §4) with one camera per NH-S901 shot.

Runs with the `bpy` pip module (Blender 5.x) headless. Axes: X along the facade (stage runs left-right), +Y away
from the building into the square, Z up. Origin = centre of the portico's semicircle at ground level.

Fixed dimensions (SET_BIBLE §4 + the two LOCKED plates):
  podium / ground-floor arcade   z 0-5          giant-order columns z 5-16 (11 m), r 0.7, twelve on a semicircle r 10
  entablature z 16-18, attic + drum + cupola above; office window wall = curved wall r 8.5 (columns "a metre or two
  beyond the glass"), office floor z 5, eye z 6.6
  main block 64 m wide, 16 m deep (y -16..0), 24 m tall to the cornice (fitted to the dusk plate by overlay)
  square: granite paving, ~60 m deep from the portico, ringed by 4-5 storey blocks (15-18 m)
  STAGE: 24 m wide x 6 m deep x 1.2 m high, centre STAGE_Y in front of the portico centre, back (truss edge) toward
  the building; truss = two square posts 0.3 m at the stage ends on the near edge, one solid beam, top 5 m above deck (the plate: beam level with the ground-floor arches);
  podium at centre; a row of folding chairs; steps at each end; lumber flatbed + box van parked as boxes.

Cameras are written to cameras.json (position, rotation, lens, sensor) so the shot specs can carry them.
usage: python3 build_city_hall.py OUT_DIR [--stage-y 42] [--only CAM ...] [--no-render]
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

args = sys.argv[1:]
OUT = args[0]
os.makedirs(OUT, exist_ok=True)
STAGE_Y = 42.0
if "--stage-y" in args:
    STAGE_Y = float(args[args.index("--stage-y") + 1])
ONLY = None
if "--only" in args:
    i = args.index("--only"); ONLY = set(a for a in args[i + 1:] if not a.startswith("--"))
RENDER = "--no-render" not in args

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"

# ------------------------------------------------------------------ materials (clay tints so parts read apart)
def mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1.0)
    return m

M_STONE = mat("stone", (0.70, 0.68, 0.62))
M_PAVE = mat("paving", (0.45, 0.45, 0.47))
M_TIMBER = mat("timber", (0.85, 0.65, 0.35))
M_BANNER = mat("banner", (0.55, 0.30, 0.42))
M_CITY = mat("city", (0.55, 0.42, 0.36))
M_VEH = mat("vehicle", (0.80, 0.80, 0.82))
M_GLASS = mat("glass", (0.30, 0.40, 0.50))
M_MAN = mat("man", (0.95, 0.75, 0.10))


def box(name, cx, cy, cz, sx, sy, sz, m=M_STONE):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    o = bpy.context.object; o.name = name; o.scale = (sx, sy, sz); o.data.materials.append(m)
    return o


def cyl(name, cx, cy, z0, z1, r, m=M_STONE, verts=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=z1 - z0, location=(cx, cy, (z0 + z1) / 2))
    o = bpy.context.object; o.name = name; o.data.materials.append(m)
    return o


def half_cyl(name, r, z0, z1, m=M_STONE, verts=48):
    """Semicircle (y >= 0 half) drum: cylinder cut by a box on the -y side via a boolean."""
    o = cyl(name, 0, 0, z0, z1, r, m, verts)
    cutter = box(name + "_cut", 0, -r, (z0 + z1) / 2, 2 * r + 2, 2 * r, (z1 - z0) + 2)
    mod = o.modifiers.new("cut", "BOOLEAN"); mod.operation = "DIFFERENCE"; mod.object = cutter
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier="cut")
    bpy.data.objects.remove(cutter)
    return o


# ------------------------------------------------------------------ the building
R_COL = 10.0            # column circle
R_WALL = 8.5            # office's curved window wall
box("main_block", 0, -8, 12, 64, 16, 24)
box("main_cornice", 0, -8, 24.4, 65, 17, 0.8)
box("roof", 0, -8, 25.8, 58, 12, 2.0)
# wings' window slots (upper floor + ground floor) as shallow dark boxes
for fl, z in ((0, 2.8), (1, 10.0), (2, 17.5)):
    for k in range(-7, 8):
        x = k * 4.2
        if abs(x) < 11.5:
            continue
        box("win_%d_%d" % (fl, k), x, 0.05, z, 1.5, 0.3, 3.6 if fl else 3.0, M_GLASS)
# portico: podium (ground floor arcade), column ring, entablature, attic, drum, cupola
half_cyl("podium", R_COL + 0.8, 0, 5.0)
for k in range(9):                                   # nine arch openings on the podium
    a = math.pi * (k + 0.5) / 9
    x, y = (R_COL + 0.8) * math.cos(a), (R_COL + 0.8) * math.sin(a)
    o = box("arch_%d" % k, x, y, 2.4, 2.2, 0.6, 3.8, M_GLASS)
    o.rotation_euler = (0, 0, a + math.pi / 2)
half_cyl("veranda_floor", R_COL + 0.8, 5.0, 5.4)
od = half_cyl("office_drum", R_WALL, 5.4, 16.0)      # the curved window wall the office sits behind (a shell)
inner = half_cyl("office_drum_inner", R_WALL - 0.4, 5.3, 16.1)
mod = od.modifiers.new("shell", "BOOLEAN"); mod.operation = "DIFFERENCE"; mod.object = inner
bpy.context.view_layer.objects.active = od; bpy.ops.object.modifier_apply(modifier="shell"); bpy.data.objects.remove(inner)
half_cyl("balustrade", R_COL - 0.9, 5.4, 6.4)
cut = box("balustrade_hollow", 0, 0, 5.9, 2 * (R_COL - 1.15), 2 * (R_COL - 1.15), 1.2)
bo = bpy.data.objects["balustrade"]; mod = bo.modifiers.new("h", "BOOLEAN"); mod.operation = "DIFFERENCE"; mod.object = cut
bpy.context.view_layer.objects.active = bo; bpy.ops.object.modifier_apply(modifier="h"); bpy.data.objects.remove(cut)
for k in range(12):                                  # twelve columns on the semicircle, ends at the facade
    a = math.pi * k / 11
    x, y = R_COL * math.cos(a), R_COL * math.sin(a)
    box("col_plinth_%02d" % k, x, y, 5.6, 1.9, 1.9, 0.4)
    cyl("col_%02d" % k, x, y, 5.8, 15.6, 0.7)
    box("col_cap_%02d" % k, x, y, 15.8, 1.9, 1.9, 0.4)
half_cyl("entablature", R_COL + 1.0, 16.0, 18.2)
half_cyl("attic", R_COL + 0.4, 18.2, 24.4)
cyl("drum", 0, -3, 24.4, 29.0, 3.6)
cyl("cupola", 0, -3, 29.0, 31.5, 2.0, verts=16)
bpy.ops.mesh.primitive_uv_sphere_add(radius=2.2, location=(0, -3, 31.5)); bpy.context.object.name = "dome"
bpy.context.object.data.materials.append(M_STONE)
# the office's three French windows (dark slots in the drum wall, upper floor), centred on the axis
for k in (-1, 0, 1):                                 # cut as openings so the POV camera can sit in the glass line
    a = math.pi / 2 + k * 0.30
    wb = box("office_win_%d" % k, R_WALL * math.cos(a), R_WALL * math.sin(a), 7.7, 2.4, 1.2, 4.6, M_GLASS)
    wb.rotation_euler = (0, 0, a + math.pi / 2)
    mod = od.modifiers.new("w%d" % k, "BOOLEAN"); mod.operation = "DIFFERENCE"; mod.object = wb
    bpy.context.view_layer.objects.active = od; bpy.ops.object.modifier_apply(modifier="w%d" % k); bpy.data.objects.remove(wb)
# banner: hangs from the entablature between the columns, across the front of the portico (chord y ~ R_COL)
o = box("banner", 0, R_COL + 0.2, 13.5, 14.0, 0.05, 2.6, M_BANNER)
# steps down from the podium to the square, centred
for k in range(6):
    box("step_%d" % k, 0, R_COL + 0.8 + 0.4 * (k + 1), 5.0 - 0.83 * (k + 1) + 0.4, 12.0 - k * 0.0, 0.8, 0.83)

# ------------------------------------------------------------------ the square and the city ring
SQ_D, SQ_W = 60.0, 96.0
box("paving", 0, R_COL + SQ_D / 2, -0.05, SQ_W + 40, SQ_D + 40, 0.1, M_PAVE)
box("kerb_far", 0, R_COL + SQ_D + 0.5, 0.08, SQ_W, 1.0, 0.15, M_STONE)
# far-side buildings with a gap for the street on the axis
for sx, w in ((-27.0, 46.0), (27.0, 46.0)):
    box("far_block_%d" % (sx > 0), sx, R_COL + SQ_D + 14, 8.0, w, 24, 16, M_CITY)
box("steeple", 33.0, R_COL + SQ_D + 24, 20, 5, 5, 40, M_CITY)
for sx in (-1, 1):                                   # flanking blocks along the sides of the square
    for k in range(3):
        box("side_block_%d_%d" % (sx > 0, k), sx * (SQ_W / 2 + 11), R_COL + 12 + k * 20, 8.0, 22, 18, 16 - 2 * (k % 2), M_CITY)
    for k in range(6):                               # bare trees along the sides as posts+balls
        y = R_COL + 8 + k * 9
        cyl("tree_%d_%d" % (sx > 0, k), sx * (SQ_W / 2 - 3), y, 0, 4.5, 0.25, M_CITY, 8)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=2.8, location=(sx * (SQ_W / 2 - 3), y, 6.5)); bpy.context.object.data.materials.append(M_CITY)

# ------------------------------------------------------------------ the stage
ST_W, ST_D, ST_H = 24.0, 6.0, 1.2
y_back = STAGE_Y - ST_D / 2                          # edge toward the building carries the truss
box("stage_deck", 0, STAGE_Y, ST_H / 2, ST_W, ST_D, ST_H, M_TIMBER)
for sx in (-1, 1):
    box("truss_post_%d" % (sx > 0), sx * (ST_W / 2 - 0.4), y_back + 0.3, ST_H + 2.5, 0.3, 0.3, 5.0, M_TIMBER)
    box("truss_brace_%d" % (sx > 0), sx * (ST_W / 2 - 1.2), y_back + 0.3, ST_H + 4.4, 1.6, 0.25, 0.25, M_TIMBER)
    # steps at each end, descending away from the stage along X
    for k in range(4):
        box("steps_%d_%d" % (sx > 0, k), sx * (ST_W / 2 + 0.3 + 0.3 * k + 0.15), STAGE_Y + 0.5, (ST_H - 0.3 * (k + 1)) + 0.15 - 0.0, 0.3, 1.2, 0.3, M_TIMBER)
box("truss_beam", 0, y_back + 0.3, ST_H + 5.0 + 0.15, ST_W - 0.5, 0.3, 0.3, M_TIMBER)
box("podium", 0, STAGE_Y + 1.6, ST_H + 0.6, 0.6, 0.5, 1.2, M_TIMBER)
for k in range(-9, 10):                              # a row of folding chairs behind the podium
    if k == 0:
        continue
    box("chair_%d" % k, k * 1.1, STAGE_Y - 0.8, ST_H + 0.45, 0.45, 0.45, 0.9, M_TIMBER)
# vehicles: lumber flatbed and white box van parked nose-in at the left kerb of the square (plate: far left of the stage)
box("flatbed", -38, STAGE_Y + 4, 1.0, 2.5, 8.0, 1.2, M_VEH); box("flatbed_cab", -38, STAGE_Y + 0.7, 1.9, 2.4, 2.2, 2.4, M_VEH)
box("box_van", -38, STAGE_Y - 6, 1.4, 2.4, 6.0, 2.8, M_VEH)
# a 1.8 m man at the podium and one at the left steps: the scale reference
box("man_podium", 0, STAGE_Y + 1.0, ST_H + 0.9, 0.5, 0.3, 1.8, M_MAN)
box("man_steps", -(ST_W / 2 + 1.5), STAGE_Y + 0.5, 0.9, 0.5, 0.3, 1.8, M_MAN)

# ------------------------------------------------------------------ light + render settings (Workbench clay)
scene.render.engine = "BLENDER_WORKBENCH"
sh = scene.display.shading
sh.light = "STUDIO"; sh.color_type = "MATERIAL"; sh.show_shadows = True; sh.show_cavity = True
sh.shadow_intensity = 0.35
scene.display.shading.studiolight_rotate_z = math.radians(-35)
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new("w"); scene.world.color = (0.75, 0.80, 0.86)


def look_at(cam, target):
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(name, loc, target, lens, sensor=36.0, res=(1920, 1080), roll=0.0):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = sensor; cd.sensor_fit = "HORIZONTAL"
    cd.clip_end = 1000
    c = bpy.data.objects.new(name, cd); scene.collection.objects.link(c)
    c.location = loc; look_at(c, target)
    if roll:
        c.rotation_euler.rotate_axis("Z", math.radians(roll))
    return c, res


Y0 = R_COL                                           # the column line; "out" distances below are from it
CAMS = {
 # the two LOCKED plates and the shots derived from them: 21:9, elevated across the square
 "PLATE":  camera("PLATE", (0.0, Y0 + 66.0, 9.0), (0.0, 0.0, 12.0), 22, res=(1584, 672)),
 # SH002 first-light wide (16:9 crop of the plate's view)
 "SH002":  camera("SH002", (0.0, Y0 + 66.0, 9.0), (0.0, 0.0, 12.0), 26),
 # SH003 low angle from the paving near the left upright, looking back at the building
 "SH003":  camera("SH003", (-8.0, STAGE_Y + 8.0, 0.9), (-11.0, y_back, 5.0), 24),
 # SH006 Pengold's POV: inside the office, eye at the middle window, looking down through the columns at the stage
 "SH006":  camera("SH006", (0.0, R_WALL - 0.2, 7.2), (0.0, STAGE_Y - 4.0, 0.0), 20),
 # SH007 medium-wide from the paving in front of the stage, the crossbeam seating
 "SH007":  camera("SH007", (2.0, STAGE_Y + 18.0, 1.7), (0.0, y_back, 7.5), 28),
 # SH009 beside the left end of the finished stage, the steps in profile
 "SH009":  camera("SH009", (-17.0, STAGE_Y + 7.0, 1.5), (-12.0, STAGE_Y - 1.0, 1.6), 32),
 # SH010/011 dusk wide = the plate camera at 16:9
 "SH010":  camera("SH010", (0.0, Y0 + 66.0, 9.0), (0.0, 0.0, 12.0), 26),
}

meta = {"stage_centre_y_from_column_line_m": STAGE_Y - Y0, "stage": dict(w=ST_W, d=ST_D, h=ST_H, truss_h=5.0),
        "cameras": {}}
for name, (cam, res) in CAMS.items():
    e = cam.rotation_euler
    meta["cameras"][name] = dict(location=[round(v, 3) for v in cam.location],
                                 rotation_deg=[round(math.degrees(v), 2) for v in e],
                                 lens_mm=cam.data.lens, sensor_mm=cam.data.sensor_width, res=list(res))
    if not RENDER or (ONLY and name not in ONLY):
        continue
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.filepath = os.path.join(OUT, "clay_%s.png" % name)
    bpy.ops.render.render(write_still=True)
    print("rendered", scene.render.filepath, flush=True)

json.dump(meta, open(os.path.join(OUT, "cameras.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "city_hall_blockout.blend"))
print("saved blockout; stage centre %.1f m in front of the column line" % (STAGE_Y - Y0))
