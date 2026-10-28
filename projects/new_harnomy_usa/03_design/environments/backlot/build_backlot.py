#!/usr/bin/env python3
r"""build_backlot.py - the NEW HARNOMY, U.S.A. backlot: one world, one origin, every exterior location in it.

WHY THIS EXISTS
---------------
Brad, 2026-09-06: make the piazza, stage, City Hall and the rest of the world "a Hollywood style stage set that will
establish continuity across all scenes." The City Hall square blockout (build_city_hall.py) proved the method on one
location; this file is that method applied to the town. Every exterior the opera visits is placed in ONE coordinate
system, so a camera anywhere in the town sees the same buildings in the same places from every angle, and any two
shots that overlap agree by construction rather than by luck.

WHAT IT IS AND IS NOT
  IS:     a greybox backlot at true scale - correct footprints, heights, frontages, street widths and sight lines,
          with named control points and one camera per shot. It exists to CONSTRAIN the image models: clay, depth and
          normal passes from these cameras are what a keyframe is generated against, and check_keyframe_geometry.py
          projects its control points to refuse a keyframe that has moved the set.
  IS NOT: a render. Nothing here is meant to be photographed. Materials are flat clay tints so parts read apart.
          The look still comes from nano-banana/Veo; this decides only WHERE things are.

THE TOWN (01_development/bible/world/setting.md)
  Origin (0,0,0) = centre of City Hall's portico semicircle, at pavement level. +Y runs out into the square, away
  from the building; +X runs along the facade to the (viewer's) right; +Z up. Every location below is placed
  relative to that one point, so "across the square from City Hall" is a coordinate, not an adjective.

    CITY HALL + THE SQUARE ...... y 0 .. 70      the built blockout: portico, office, rally stage at y=42
    NORTH SIDE (shakedown row) .. y ~74, x -46..+46   bodega, independent restaurant, storefronts - Dick's targets
    EAST SIDE ................... x ~+58          the parish church and its steeple (already a landmark in the plates)
    WEST SIDE ................... x ~-58          the Black church, and the PILF storefront office above it
    UNIVERSITY .................. y ~120          gate, quad and the lecture hall, four blocks up the axis street
    THE AXIS STREET ............. x 0, y 70..120  the street that leaves the square on the building's axis and
                                                  arrives at the university gate: the one long sight line in town

usage: python3 build_backlot.py OUT_DIR [--only LOCATION ...] [--state build|finished] [--blend] [--no-render]
       locations: city_hall_square  north_row  west_side  east_side  university  axis_street
"""
import json
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
OUT = args[0] if args and not args[0].startswith("--") else "out_backlot"
os.makedirs(OUT, exist_ok=True)


def flag(name):
    return name in args


def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default


STATE = opt("--state", "finished")
ONLY = None
if "--only" in args:
    i = args.index("--only")
    ONLY = set(a for a in args[i + 1:] if not a.startswith("--"))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"

# ------------------------------------------------------------------ materials
def mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1.0)
    return m


M = dict(
    stone=mat("stone", (0.70, 0.68, 0.62)),
    pave=mat("paving", (0.45, 0.45, 0.47)),
    road=mat("road", (0.30, 0.30, 0.32)),
    timber=mat("timber", (0.85, 0.65, 0.35)),
    banner=mat("banner", (0.55, 0.30, 0.42)),
    brick=mat("brick", (0.55, 0.34, 0.28)),
    brick_pale=mat("brick_pale", (0.66, 0.50, 0.42)),
    shop=mat("shopfront", (0.35, 0.42, 0.44)),
    glass=mat("glass", (0.30, 0.40, 0.50)),
    veh=mat("vehicle", (0.80, 0.80, 0.82)),
    green=mat("green", (0.42, 0.50, 0.36)),
    man=mat("man", (0.95, 0.75, 0.10)),
)

CONTROL = {"posts": [], "landmarks": {}}


def box(name, cx, cy, cz, sx, sy, sz, m="stone", rot=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    o = bpy.context.object
    o.name = name
    o.scale = (sx, sy, sz)
    o.rotation_euler = (0, 0, rot)
    o.data.materials.append(M[m] if isinstance(m, str) else m)
    return o


def cyl(name, cx, cy, z0, z1, r, m="stone", verts=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=z1 - z0, location=(cx, cy, (z0 + z1) / 2))
    o = bpy.context.object
    o.name = name
    o.data.materials.append(M[m] if isinstance(m, str) else m)
    return o


def half_cyl(name, r, z0, z1, m="stone", verts=48):
    o = cyl(name, 0, 0, z0, z1, r, m, verts)
    cutter = box(name + "_cut", 0, -r, (z0 + z1) / 2, 2 * r + 2, 2 * r, (z1 - z0) + 2)
    mod = o.modifiers.new("cut", "BOOLEAN"); mod.operation = "DIFFERENCE"; mod.object = cutter
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier="cut")
    bpy.data.objects.remove(cutter)
    return o


def storefront(tag, x, y, w, depth, floors, m="brick", shop_name=None, face=-1, axis="y"):
    """A party-wall building on a street: glazed ground floor, floors above, parapet.

    (x, y) is the CENTRE of the street frontage. axis="y" means the frontage faces along Y (a shop on the north or
    south side of a street that runs left-right); axis="x" means it faces along X (a shop lining the axis street).
    face is -1 or +1: which way along that axis the shopfront looks. The building extends the other way."""
    h = 4.2 + 3.4 * (floors - 1)
    if axis == "y":
        cx, cy = x, y - face * depth / 2.0
        sx, sy = w, depth
        fx, fy = x, y + face * 0.15                 # the glazed front, just proud of the frontage line
        wstep = w / 3.2
        rot = 0.0
    else:
        cx, cy = x - face * depth / 2.0, y
        sx, sy = depth, w
        fx, fy = x + face * 0.15, y
        wstep = w / 3.2
        rot = 0.0
    box("%s_block" % tag, cx, cy, h / 2, sx, sy, h, m)
    box("%s_parapet" % tag, cx, cy, h + 0.5, sx + 0.3, sy + 0.3, 1.0, m)
    if axis == "y":
        box("%s_shopfront" % tag, fx, fy, 1.9, w * 0.82, 0.4, 3.4, "shop")
        box("%s_fascia" % tag, fx, fy, 4.05, w * 0.86, 0.35, 0.9, "shop")
    else:
        box("%s_shopfront" % tag, fx, fy, 1.9, 0.4, w * 0.82, 3.4, "shop")
        box("%s_fascia" % tag, fx, fy, 4.05, 0.35, w * 0.86, 0.9, "shop")
    for f in range(1, floors):
        for k in (-1, 0, 1):
            z = 4.2 + 3.4 * (f - 1) + 1.7
            if axis == "y":
                box("%s_win_%d_%d" % (tag, f, k), x + k * wstep, y + face * 0.12, z, w / 6.0, 0.3, 1.9, "glass")
            else:
                box("%s_win_%d_%d" % (tag, f, k), x + face * 0.12, y + k * wstep, z, 0.3, w / 6.0, 1.9, "glass")
    if shop_name:
        CONTROL["landmarks"][shop_name] = [x, y, 4.05]
    return h


# =================================================================== CITY HALL + THE SQUARE
R_COL, R_WALL = 10.0, 8.5
SQ_D, SQ_W = 60.0, 96.0
STAGE_Y = 42.0
ST_W, ST_D, ST_H = 24.0, 6.0, 1.2
y_back = STAGE_Y - ST_D / 2


def build_city_hall_square():
    box("main_block", 0, -8, 12, 64, 16, 24)
    box("main_cornice", 0, -8, 24.4, 65, 17, 0.8)
    box("roof", 0, -8, 25.8, 58, 12, 2.0)
    for fl, z in ((0, 2.8), (1, 10.0), (2, 17.5)):
        for k in range(-7, 8):
            x = k * 4.2
            if abs(x) < 11.5:
                continue
            box("win_%d_%d" % (fl, k), x, 0.05, z, 1.5, 0.3, 3.6 if fl else 3.0, "glass")
    half_cyl("podium", R_COL + 0.8, 0, 5.0)
    for k in range(9):
        a = math.pi * (k + 0.5) / 9
        box("arch_%d" % k, (R_COL + 0.8) * math.cos(a), (R_COL + 0.8) * math.sin(a), 2.4, 2.2, 0.6, 3.8,
            "glass", a + math.pi / 2)
    half_cyl("veranda_floor", R_COL + 0.8, 5.0, 5.4)
    od = half_cyl("office_drum", R_WALL, 5.4, 16.0)
    inner = half_cyl("office_drum_inner", R_WALL - 0.4, 5.3, 16.1)
    mod = od.modifiers.new("shell", "BOOLEAN"); mod.operation = "DIFFERENCE"; mod.object = inner
    bpy.context.view_layer.objects.active = od
    bpy.ops.object.modifier_apply(modifier="shell"); bpy.data.objects.remove(inner)
    half_cyl("balustrade", R_COL - 0.9, 5.4, 6.4)
    cut = box("balustrade_hollow", 0, 0, 5.9, 2 * (R_COL - 1.15), 2 * (R_COL - 1.15), 1.2)
    bo = bpy.data.objects["balustrade"]
    mod = bo.modifiers.new("h", "BOOLEAN"); mod.operation = "DIFFERENCE"; mod.object = cut
    bpy.context.view_layer.objects.active = bo
    bpy.ops.object.modifier_apply(modifier="h"); bpy.data.objects.remove(cut)
    for k in range(12):
        a = math.pi * k / 11
        x, y = R_COL * math.cos(a), R_COL * math.sin(a)
        box("col_plinth_%02d" % k, x, y, 5.6, 1.9, 1.9, 0.4)
        cyl("col_%02d" % k, x, y, 5.8, 15.6, 0.7)
        box("col_cap_%02d" % k, x, y, 15.8, 1.9, 1.9, 0.4)
    half_cyl("entablature", R_COL + 1.0, 16.0, 18.2)
    half_cyl("attic", R_COL + 0.4, 18.2, 24.4)
    cyl("drum", 0, -3, 24.4, 29.0, 3.6)
    cyl("cupola", 0, -3, 29.0, 31.5, 2.0, verts=16)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=2.2, location=(0, -3, 31.5))
    bpy.context.object.name = "dome"; bpy.context.object.data.materials.append(M["stone"])
    for k in (-1, 0, 1):
        a = math.pi / 2 + k * 0.30
        wb = box("office_win_%d" % k, R_WALL * math.cos(a), R_WALL * math.sin(a), 7.7, 2.4, 1.2, 4.6,
                 "glass", a + math.pi / 2)
        mod = od.modifiers.new("w%d" % k, "BOOLEAN"); mod.operation = "DIFFERENCE"; mod.object = wb
        bpy.context.view_layer.objects.active = od
        bpy.ops.object.modifier_apply(modifier="w%d" % k); bpy.data.objects.remove(wb)
    box("banner", 0, R_COL + 0.2, 13.5, 14.0, 0.05, 2.6, "banner")
    for k in range(6):
        box("step_%d" % k, 0, R_COL + 0.8 + 0.4 * (k + 1), 5.0 - 0.83 * (k + 1) + 0.4, 12.0, 0.8, 0.83)
    box("paving", 0, R_COL + SQ_D / 2, -0.05, SQ_W + 40, SQ_D + 40, 0.1, "pave")
    CONTROL["landmarks"]["city_hall_door"] = [0, R_COL + 0.8, 0]
    CONTROL["landmarks"]["square_centre"] = [0, R_COL + SQ_D / 2, 0]
    # the rally stage
    box("stage_deck", 0, STAGE_Y, ST_H / 2, ST_W, ST_D, ST_H, "timber")
    for sx in (-1, 1):
        box("truss_post_%d" % (sx > 0), sx * (ST_W / 2 - 0.4), y_back + 0.3, ST_H + 2.5, 0.3, 0.3, 5.0, "timber")
        for k in range(4):
            box("steps_%d_%d" % (sx > 0, k), sx * (ST_W / 2 + 0.45 + 0.3 * k), STAGE_Y + 0.5,
                ST_H - 0.3 * (k + 1) + 0.15, 0.3, 1.2, 0.3, "timber")
        CONTROL["posts"].append({
            "name": "post_%s" % ("R" if sx > 0 else "L"),
            "base": [sx * (ST_W / 2 - 0.4), y_back + 0.3, ST_H],
            "top": [sx * (ST_W / 2 - 0.4), y_back + 0.3, ST_H + 5.0]})
    if STATE == "finished":
        box("truss_beam", 0, y_back + 0.3, ST_H + 5.15, ST_W - 0.5, 0.3, 0.3, "timber")
        box("podium", 0, STAGE_Y + 1.6, ST_H + 0.6, 0.6, 0.5, 1.2, "timber")
        for k in range(-9, 10):
            if k:
                box("chair_%d" % k, k * 1.1, STAGE_Y - 0.8, ST_H + 0.45, 0.45, 0.45, 0.9, "timber")
    else:
        for k, (lx, ly) in enumerate(((-20, STAGE_Y + 7), (4, STAGE_Y + 7), (16, STAGE_Y + 5.5))):
            box("lumber_%d" % k, lx, ly, 0.4, 5.0, 1.2, 0.8, "timber")
    box("flatbed", -38, STAGE_Y + 4, 1.0, 2.5, 8.0, 1.2, "veh")
    box("box_van", -38, STAGE_Y - 6, 1.4, 2.4, 6.0, 2.8, "veh")
    CONTROL["deck_front"] = {"left": [-ST_W / 2, STAGE_Y + ST_D / 2, ST_H], "right": [ST_W / 2, STAGE_Y + ST_D / 2, ST_H]}
    CONTROL["chair_band"] = {"top_left": [-ST_W / 2, STAGE_Y - 0.8, ST_H + 0.9],
                             "bottom_right": [ST_W / 2, STAGE_Y - 0.8, ST_H]}


# =================================================================== THE NORTH SIDE - the shakedown row
NORTH_Y = 74.0


def build_north_row():
    """The far side of the square: the row of small businesses Dick shakes down (setting.md, festival grounds).
    Frontages face the square, i.e. they look back toward City Hall down -Y."""
    box("north_kerb", 0, NORTH_Y - 2.0, 0.08, 130, 1.0, 0.16, "stone")
    box("north_road", 0, NORTH_Y - 6.0, 0.02, 130, 9.0, 0.04, "road")
    row = [
        # (tag, centre x, width, floors, material, landmark name)
        ("shop_w3", -44, 11, 3, "brick", None),
        ("shop_w2", -32, 11, 4, "brick_pale", None),
        ("restaurant", -20, 12, 3, "brick", "independent_restaurant"),   # Dick's target: the family restaurant
        ("shop_w1", -8, 10, 3, "brick_pale", None),
        # the axis street opening runs through x = 0 (see build_axis_street)
        ("bodega", 10, 10, 2, "brick", "bodega"),                        # Dick's target: the corner bodega
        ("shop_e1", 21, 11, 3, "brick_pale", None),
        ("shop_e2", 33, 12, 4, "brick", None),
        ("shop_e3", 45, 11, 3, "brick_pale", None),
    ]
    for tag, x, w, floors, m, name in row:
        storefront(tag, x, NORTH_Y, w, 16.0, floors, m, name)
    # the bodega's awning and stacked crates - the one shopfront the camera goes close to
    box("bodega_awning", 10, NORTH_Y - 1.6, 3.5, 9.0, 3.0, 0.2, "banner")
    for k in range(3):
        box("bodega_crate_%d" % k, 6.0 + 1.2 * k, NORTH_Y - 1.2, 0.4, 1.0, 0.8, 0.8, "timber")
    for k in range(-5, 6):
        if abs(k) > 1:
            cyl("north_tree_%d" % k, k * 11.0, NORTH_Y - 3.5, 0, 4.5, 0.22, "green", 8)


# =================================================================== EAST AND WEST SIDES
def build_east_side():
    """The parish church with the steeple that stands to the right of City Hall in both LOCKED plates."""
    X = 58.0
    box("parish_nave", X, 34.0, 8.0, 18, 30, 16, "brick")
    box("parish_roof", X, 34.0, 17.5, 19, 31, 3.0, "brick")
    box("parish_tower", X - 6.0, 20.0, 14.0, 7, 7, 28, "stone")
    box("parish_belfry", X - 6.0, 20.0, 29.0, 5.5, 5.5, 4.0, "stone")
    bpy.ops.mesh.primitive_cone_add(radius1=3.6, depth=12.0, location=(X - 6.0, 20.0, 37.0))
    bpy.context.object.name = "parish_steeple"; bpy.context.object.data.materials.append(M["brick"])
    CONTROL["landmarks"]["parish_steeple"] = [X - 6.0, 20.0, 43.0]
    for k in range(3):
        box("east_block_%d" % k, X + 4, 52.0 + k * 18, 8.0, 22, 16, 16, "brick_pale")


def build_west_side():
    """The west side: the Black church (setting.md) and, over the shop below it, the PILF office - Dick's base."""
    X = -58.0
    box("black_church_nave", X, 30.0, 7.5, 16, 26, 15, "brick_pale")
    box("black_church_roof", X, 30.0, 16.0, 17, 27, 2.6, "brick_pale")
    box("black_church_tower", X + 5.0, 18.0, 11.0, 6, 6, 22, "brick_pale")
    box("black_church_cross", X + 5.0, 18.0, 24.0, 0.4, 0.4, 4.0, "stone")
    CONTROL["landmarks"]["black_church"] = [X, 18.0, 0]
    storefront("pilf", X + 6, 52.0, 12, 15.0, 3, "brick", "pilf_office", axis="x", face=1)     # PILF: a storefront with two floors over
    box("pilf_sign", X + 6.35, 52.0, 8.0, 0.2, 6.0, 1.2, "banner")
    for k in range(2):
        storefront("west_shop_%d" % k, X + 6, 70.0 + k * 14, 12, 15.0, 3, "brick_pale", axis="x", face=1)


# =================================================================== THE AXIS STREET AND THE UNIVERSITY
UNI_Y = 120.0


def build_axis_street():
    """The one long sight line in town: out of the square on City Hall's axis, four blocks to the university gate.
    Every shot that looks up this street sees the gate at the end of it - that is the continuity this buys."""
    box("axis_road", 0, (NORTH_Y + UNI_Y) / 2, 0.02, 14.0, UNI_Y - NORTH_Y + 8, 0.04, "road")
    for side in (-1, 1):
        box("axis_kerb_%d" % (side > 0), side * 7.5, (NORTH_Y + UNI_Y) / 2, 0.1, 1.0, UNI_Y - NORTH_Y + 8, 0.2, "stone")
        for k in range(4):
            storefront("axis_%d_%d" % (side > 0, k), side * 9.0, NORTH_Y + 8 + k * 12, 11, 16.0, 3,
                       "brick" if k % 2 else "brick_pale", axis="x", face=-side)
        for k in range(5):
            cyl("axis_lamp_%d_%d" % (side > 0, k), side * 7.0, NORTH_Y + 4 + k * 11, 0, 5.0, 0.14, "stone", 8)


def build_university():
    """The university Dick shakes down: a gate on the axis, a quad behind it, the lecture hall across the quad."""
    box("uni_wall_w", -22, UNI_Y, 1.6, 30, 1.0, 3.2, "brick")
    box("uni_wall_e", 22, UNI_Y, 1.6, 30, 1.0, 3.2, "brick")
    for sx in (-1, 1):
        box("uni_gate_pier_%d" % (sx > 0), sx * 6.0, UNI_Y, 3.0, 2.0, 2.0, 6.0, "stone")
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.9, location=(sx * 6.0, UNI_Y, 6.4))
        bpy.context.object.name = "uni_gate_ball_%d" % (sx > 0)
        bpy.context.object.data.materials.append(M["stone"])
    box("uni_gate_arch", 0, UNI_Y, 6.6, 14.0, 1.6, 1.2, "stone")
    CONTROL["landmarks"]["university_gate"] = [0, UNI_Y, 0]
    box("uni_quad", 0, UNI_Y + 26, -0.03, 60, 50, 0.1, "green")
    box("uni_hall", 0, UNI_Y + 54, 9.0, 46, 18, 18, "stone")               # the lecture hall closing the quad
    box("uni_hall_portico", 0, UNI_Y + 44.6, 6.0, 18, 1.2, 12, "stone")
    for k in range(6):
        cyl("uni_col_%d" % k, -7.5 + 3.0 * k, UNI_Y + 44.0, 0, 11.0, 0.55, "stone")
    for sx in (-1, 1):                                                      # the two ranges down the sides
        box("uni_range_%d" % (sx > 0), sx * 36, UNI_Y + 26, 7.0, 14, 46, 14, "brick")
    for k in range(6):
        cyl("uni_tree_%d" % k, -20 + 8 * k, UNI_Y + 14, 0, 5.5, 0.26, "green", 8)


LOCATIONS = {
    "city_hall_square": build_city_hall_square,
    "north_row": build_north_row,
    "east_side": build_east_side,
    "west_side": build_west_side,
    "axis_street": build_axis_street,
    "university": build_university,
}

for name, fn in LOCATIONS.items():
    if ONLY and name not in ONLY:
        continue
    fn()
    print("built", name, flush=True)

# ------------------------------------------------------------------ ground plane under the whole town
box("ground", 0, 90, -0.2, 400, 400, 0.2, "road")

# ------------------------------------------------------------------ render settings + survey cameras
scene.render.engine = "BLENDER_WORKBENCH"
sh = scene.display.shading
sh.light = "STUDIO"; sh.color_type = "MATERIAL"; sh.show_shadows = True; sh.show_cavity = True
sh.shadow_intensity = 0.3
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.file_format = "PNG"
scene.world = bpy.data.worlds.new("w"); scene.world.color = (0.75, 0.80, 0.86)

from mathutils import Vector       # noqa: E402


def camera(name, loc, target, lens, res=(1920, 1080)):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36.0
    cd.sensor_fit = "HORIZONTAL"; cd.clip_end = 2000
    c = bpy.data.objects.new(name, cd); scene.collection.objects.link(c)
    c.location = loc
    c.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return c, res


SURVEY = {
    "PLAN":        camera("PLAN", (0, 95, 260), (0, 95, 0), 40),                    # straight down: the town plan
    "AERIAL":      camera("AERIAL", (-120, -60, 90), (0, 70, 8), 35),               # the establishing three-quarter
    "AXIS_UP":     camera("AXIS_UP", (0, 30, 2.0), (0, UNI_Y + 40, 8), 40),         # square -> university gate
    "AXIS_DOWN":   camera("AXIS_DOWN", (0, UNI_Y - 6, 2.0), (0, 0, 14), 40),        # university gate -> City Hall
    "BODEGA":      camera("BODEGA", (16, 58, 1.7), (10, NORTH_Y, 4.0), 30),      # the shakedown target, close
    "PILF":        camera("PILF", (-40, 46, 1.7), (-52, 53, 5.0), 35),
    "CHURCH_E":    camera("CHURCH_E", (14, 62, 2.0), (50, 24, 20), 30),
}

if not flag("--no-render"):
    for name, (cam, res) in SURVEY.items():
        scene.camera = cam
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.resolution_percentage = 100
        scene.render.filepath = os.path.join(OUT, "backlot_%s.png" % name)
        bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath, flush=True)

meta = {"origin": "centre of City Hall's portico semicircle, pavement level",
        "axes": "+X along the facade to the right, +Y out into the square, +Z up",
        "locations": {k: True for k in (ONLY or LOCATIONS)},
        "state": STATE,
        "cameras": {}}
for name, (cam, res) in SURVEY.items():
    meta["cameras"][name] = dict(location=[round(v, 3) for v in cam.location],
                                 rotation_deg=[round(math.degrees(v), 2) for v in cam.rotation_euler],
                                 lens_mm=cam.data.lens, sensor_mm=cam.data.sensor_width, res=list(res))
json.dump(meta, open(os.path.join(OUT, "backlot_cameras.json"), "w"), indent=1)
json.dump(CONTROL, open(os.path.join(OUT, "backlot_control_points.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "new_harnomy_backlot.blend"))
print("saved", os.path.join(OUT, "new_harnomy_backlot.blend"))
