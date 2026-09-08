"""backlot.world.nh.geometry - the New Harnomy world, authored as ASSETS with STATES.

This is build_backlot.py made honest about what it is: not one scene, but a set of reusable assets, each tagged with
an asset id and (where it changes over the story) a build state, so the exporter can write one USD layer per asset
per state and the composer can wire the states into USD variant sets.

Coordinate contract (unchanged): origin = centre of City Hall's portico semicircle at pavement level; +X along the
facade to the viewer's right, +Y out into the square, +Z up. Assets are authored IN WORLD SPACE for this production;
the reference prim that places each one carries an identity transform, which readback.py can override later.

Every mesh object gets two custom properties: backlot_asset (the asset id) and backlot_state ("*" = present in every
state of that asset). The exporter selects by them. Nothing here renders; nothing here knows about cameras.
"""
import math

import bpy

# ------------------------------------------------------------------ tagging
_CUR = {"asset": None, "state": "*"}


class asset:
    """with asset("RallyStage", state="finished"): ... - everything built inside is tagged."""
    def __init__(self, asset_id, state="*"):
        self.a, self.s = asset_id, state

    def __enter__(self):
        self.prev = dict(_CUR); _CUR["asset"], _CUR["state"] = self.a, self.s
        return self

    def __exit__(self, *exc):
        _CUR.update(self.prev)


def _tag(o):
    o["backlot_asset"] = _CUR["asset"] or "Untagged"
    o["backlot_state"] = _CUR["state"]
    return o


# ------------------------------------------------------------------ materials (clay tints so parts read apart)
_MATS = {}


def mat(name):
    if name in _MATS and _MATS[name].name in bpy.data.materials:
        return _MATS[name]
    rgb = dict(stone=(0.70, 0.68, 0.62), pave=(0.45, 0.45, 0.47), road=(0.30, 0.30, 0.32),
               timber=(0.85, 0.65, 0.35), banner=(0.55, 0.30, 0.42), brick=(0.55, 0.34, 0.28),
               brick_pale=(0.66, 0.50, 0.42), shop=(0.35, 0.42, 0.44), glass=(0.30, 0.40, 0.50),
               veh=(0.80, 0.80, 0.82), green=(0.42, 0.50, 0.36), man=(0.95, 0.75, 0.10))[name]
    m = bpy.data.materials.new(name); m.diffuse_color = (*rgb, 1.0)
    m.use_nodes = True                                      # a node tree, so the USD exporter writes a PreviewSurface
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.9
    _MATS[name] = m
    return m


def box(name, cx, cy, cz, sx, sy, sz, m="stone", rot=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    o = bpy.context.object; o.name = name; o.scale = (sx, sy, sz); o.rotation_euler = (0, 0, rot)
    o.data.materials.append(mat(m)); return _tag(o)


def chair(name, cx, cy, z0):
    """A folding chair (seat, back, four legs) facing +Y (the square). Phase 1 found box chairs read as crates in
    depth-conditioned keys; a chair-shaped silhouette fixes every shot at the source."""
    box(name + "_seat", cx, cy, z0 + 0.45, 0.45, 0.45, 0.04, "timber")
    box(name + "_back", cx, cy - 0.2, z0 + 0.72, 0.45, 0.04, 0.5, "timber")
    for i, (dx, dy) in enumerate(((-0.2, -0.2), (0.2, -0.2), (-0.2, 0.2), (0.2, 0.2))):
        box(name + "_leg%d" % i, cx + dx, cy + dy, z0 + 0.22, 0.03, 0.03, 0.44, "timber")


def cyl(name, cx, cy, z0, z1, r, m="stone", verts=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=z1 - z0, location=(cx, cy, (z0 + z1) / 2))
    o = bpy.context.object; o.name = name; o.data.materials.append(mat(m)); return _tag(o)


def sphere(name, cx, cy, cz, r, m="stone"):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(cx, cy, cz))
    o = bpy.context.object; o.name = name; o.data.materials.append(mat(m)); return _tag(o)


def cone(name, cx, cy, cz, r, h, m="stone"):
    bpy.ops.mesh.primitive_cone_add(radius1=r, depth=h, location=(cx, cy, cz))
    o = bpy.context.object; o.name = name; o.data.materials.append(mat(m)); return _tag(o)


def _boolean(o, cutter, op="DIFFERENCE"):
    mod = o.modifiers.new("b", "BOOLEAN"); mod.operation = op; mod.object = cutter
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier="b")
    bpy.data.objects.remove(cutter)


def half_cyl(name, r, z0, z1, m="stone", verts=48):
    o = cyl(name, 0, 0, z0, z1, r, m, verts)
    _boolean(o, box(name + "_cut", 0, -r, (z0 + z1) / 2, 2 * r + 2, 2 * r, (z1 - z0) + 2))
    return o


def storefront(tag, x, y, w, depth, floors, m="brick", face=-1, axis="y"):
    h = 4.2 + 3.4 * (floors - 1)
    if axis == "y":
        cx, cy, sx, sy, fx, fy = x, y - face * depth / 2.0, w, depth, x, y + face * 0.15
    else:
        cx, cy, sx, sy, fx, fy = x - face * depth / 2.0, y, depth, w, x + face * 0.15, y
    box("%s_block" % tag, cx, cy, h / 2, sx, sy, h, m)
    box("%s_parapet" % tag, cx, cy, h + 0.5, sx + 0.3, sy + 0.3, 1.0, m)
    if axis == "y":
        box("%s_shopfront" % tag, fx, fy, 1.9, w * 0.82, 0.4, 3.4, "shop")
        box("%s_fascia" % tag, fx, fy, 4.05, w * 0.86, 0.35, 0.9, "shop")
    else:
        box("%s_shopfront" % tag, fx, fy, 1.9, 0.4, w * 0.82, 3.4, "shop")
        box("%s_fascia" % tag, fx, fy, 4.05, 0.35, w * 0.86, 0.9, "shop")
    step = w / 3.2
    for f in range(1, floors):
        for k in (-1, 0, 1):
            z = 4.2 + 3.4 * (f - 1) + 1.7
            if axis == "y":
                box("%s_win_%d_%d" % (tag, f, k), x + k * step, y + face * 0.12, z, w / 6.0, 0.3, 1.9, "glass")
            else:
                box("%s_win_%d_%d" % (tag, f, k), x + face * 0.12, y + k * step, z, 0.3, w / 6.0, 1.9, "glass")
    return h


# ------------------------------------------------------------------ dimensions (SET_BIBLE §4, fitted by overlay)
R_COL, R_WALL = 10.0, 8.5
SQ_D, SQ_W = 60.0, 96.0
STAGE_Y = 42.0
ST_W, ST_D, ST_H = 24.0, 6.0, 1.2
Y_BACK = STAGE_Y - ST_D / 2
NORTH_Y, UNI_Y = 74.0, 120.0

STAGE_STATES = ["joists", "half_decked", "beam_seated", "swept", "finished", "feast"]


# =================================================================== ASSETS
def build_CityHall():
    with asset("CityHall"):
        box("main_block", 0, -8, 12, 64, 16, 24); box("main_cornice", 0, -8, 24.4, 65, 17, 0.8)
        box("roof", 0, -8, 25.8, 58, 12, 2.0)
        for fl, z in ((0, 2.8), (1, 10.0), (2, 17.5)):
            for k in range(-7, 8):
                x = k * 4.2
                if abs(x) >= 11.5:
                    box("win_%d_%d" % (fl, k), x, 0.05, z, 1.5, 0.3, 3.6 if fl else 3.0, "glass")
        half_cyl("podium", R_COL + 0.8, 0, 5.0)
        for k in range(9):
            a = math.pi * (k + 0.5) / 9
            box("arch_%d" % k, (R_COL + 0.8) * math.cos(a), (R_COL + 0.8) * math.sin(a), 2.4, 2.2, 0.6, 3.8,
                "glass", a + math.pi / 2)
        half_cyl("veranda_floor", R_COL + 0.8, 5.0, 5.4)
        od = half_cyl("office_drum", R_WALL, 5.4, 16.0)
        _boolean(od, half_cyl("office_drum_inner", R_WALL - 0.4, 5.3, 16.1))
        bal = half_cyl("balustrade", R_COL - 0.9, 5.4, 6.4)
        _boolean(bal, box("balustrade_hollow", 0, 0, 5.9, 2 * (R_COL - 1.15), 2 * (R_COL - 1.15), 1.2))
        for k in range(12):
            a = math.pi * k / 11
            x, y = R_COL * math.cos(a), R_COL * math.sin(a)
            box("col_plinth_%02d" % k, x, y, 5.6, 1.9, 1.9, 0.4); cyl("col_%02d" % k, x, y, 5.8, 15.6, 0.7)
            box("col_cap_%02d" % k, x, y, 15.8, 1.9, 1.9, 0.4)
        half_cyl("entablature", R_COL + 1.0, 16.0, 18.2); half_cyl("attic", R_COL + 0.4, 18.2, 24.4)
        cyl("drum", 0, -3, 24.4, 29.0, 3.6); cyl("cupola", 0, -3, 29.0, 31.5, 2.0, verts=16)
        sphere("dome", 0, -3, 31.5, 2.2)
        for k in (-1, 0, 1):
            a = math.pi / 2 + k * 0.30
            _boolean(od, box("office_win_%d" % k, R_WALL * math.cos(a), R_WALL * math.sin(a), 7.7, 2.4, 1.2, 4.6,
                             "glass", a + math.pi / 2))
        for k in range(6):
            box("step_%d" % k, 0, R_COL + 0.8 + 0.4 * (k + 1), 5.0 - 0.83 * (k + 1) + 0.4, 12.0, 0.8, 0.83)


def build_Banner():
    """The banner is a TEXT PLANE: a tracked quad the lettering tool receives from the camera projection."""
    with asset("Banner"):
        o = box("banner_cloth", 0, R_COL + 0.2, 13.5, 14.0, 0.05, 2.6, "banner")
        o["backlot_text_plane"] = True


def build_Square():
    with asset("Square"):
        box("paving", 0, R_COL + SQ_D / 2, -0.05, SQ_W + 40, SQ_D + 40, 0.1, "pave")
        box("north_kerb", 0, NORTH_Y - 2.0, 0.08, 130, 1.0, 0.16, "stone")
        box("north_road", 0, NORTH_Y - 6.0, 0.02, 130, 9.0, 0.04, "road")
        for sx in (-1, 1):
            for k in range(6):
                y = R_COL + 8 + k * 9
                cyl("tree_%d_%d" % (sx > 0, k), sx * (SQ_W / 2 - 3), y, 0, 4.5, 0.25, "green", 8)
                sphere("crown_%d_%d" % (sx > 0, k), sx * (SQ_W / 2 - 3), y, 6.5, 2.8, "green")


def build_RallyStage():
    """One asset, six states. Objects tagged '*' are in every state; the rest name the states they belong to."""
    with asset("RallyStage"):
        # the frame of joists is there from the first state; the deck grows over it
        for k in range(-11, 12):
            box("joist_%d" % (k + 11), k * 1.05, STAGE_Y, ST_H - 0.12, 0.12, ST_D - 0.2, 0.24, "timber")
        box("rim_front", 0, STAGE_Y + ST_D / 2, ST_H - 0.12, ST_W, 0.12, 0.24, "timber")
        box("rim_back", 0, STAGE_Y - ST_D / 2, ST_H - 0.12, ST_W, 0.12, 0.24, "timber")
        for sx in (-1, 1):
            for k in range(-2, 3):
                cyl("pier_%d_%d" % (sx > 0, k + 2), sx * (ST_W / 2 - 1.0), STAGE_Y + k * 1.4, 0, ST_H - 0.24, 0.12, "timber", 8)
            box("truss_post_%s" % ("R" if sx > 0 else "L"), sx * (ST_W / 2 - 0.4), Y_BACK + 0.3, ST_H + 2.5, 0.3, 0.3, 5.0, "timber")
    with asset("RallyStage", "half_decked"):
        box("deck_left_half", -ST_W / 4, STAGE_Y, ST_H + 0.02, ST_W / 2, ST_D, 0.04, "timber")
    for st in ("beam_seated", "swept", "finished", "feast"):
        with asset("RallyStage", st):
            box("deck_full_%s" % st, 0, STAGE_Y, ST_H + 0.02, ST_W, ST_D, 0.04, "timber")
            box("truss_beam_%s" % st, 0, Y_BACK + 0.3, ST_H + 5.15, ST_W - 0.5, 0.3, 0.3, "timber")
            for sx in (-1, 1):
                for k in range(4):
                    box("steps_%s_%d_%d" % (st, sx > 0, k), sx * (ST_W / 2 + 0.45 + 0.3 * k), STAGE_Y + 0.5,
                        ST_H - 0.3 * (k + 1) + 0.15, 0.3, 1.2, 0.3, "timber")
    for st in ("finished", "feast"):
        with asset("RallyStage", st):
            box("podium_%s" % st, 0, STAGE_Y + 1.6, ST_H + 0.6, 0.6, 0.5, 1.2, "timber")
            for k in range(-9, 10):
                if k:
                    chair("chair_%s_%d" % (st, k + 9), k * 1.1, STAGE_Y - 0.8, ST_H)
    with asset("RallyStage", "feast"):
        box("portrait_rig", 0, Y_BACK + 0.6, ST_H + 3.0, 6.0, 0.2, 4.0, "banner")     # Summer's portrait, Act III


def build_BuildSiteDressing():
    """Lumber stacks and the two vehicles: present during the build states, gone when finished."""
    for st in ("joists", "half_decked", "beam_seated", "swept"):
        with asset("BuildSite", st):
            for k, (lx, ly) in enumerate(((-20, STAGE_Y + 7), (4, STAGE_Y + 7), (16, STAGE_Y + 5.5))):
                box("lumber_%s_%d" % (st, k), lx, ly, 0.4, 5.0, 1.2, 0.8, "timber")
    with asset("Vehicles"):
        box("flatbed", -38, STAGE_Y + 4, 1.0, 2.5, 8.0, 1.2, "veh"); box("flatbed_cab", -38, STAGE_Y + 0.7, 1.9, 2.4, 2.2, 2.4, "veh")
        box("box_van", -38, STAGE_Y - 6, 1.4, 2.4, 6.0, 2.8, "veh")


def build_NorthRow():
    row = [("shop_w3", -44, 11, 3, "brick"), ("shop_w2", -32, 11, 4, "brick_pale"),
           ("restaurant", -20, 12, 3, "brick"), ("shop_w1", -8, 10, 3, "brick_pale"),
           ("bodega", 10, 10, 2, "brick"), ("shop_e1", 21, 11, 3, "brick_pale"),
           ("shop_e2", 33, 12, 4, "brick"), ("shop_e3", 45, 11, 3, "brick_pale")]
    for tag, x, w, floors, m in row:
        aid = {"restaurant": "Restaurant", "bodega": "Bodega"}.get(tag, "NorthRow")
        with asset(aid):
            storefront(tag, x, NORTH_Y, w, 16.0, floors, m)
    with asset("Bodega"):
        box("bodega_awning", 10, NORTH_Y - 1.6, 3.5, 9.0, 3.0, 0.2, "banner")
        for k in range(3):
            box("bodega_crate_%d" % k, 6.0 + 1.2 * k, NORTH_Y - 1.2, 0.4, 1.0, 0.8, 0.8, "timber")
    with asset("NorthRow"):
        for k in range(-5, 6):
            if abs(k) > 1:
                cyl("north_tree_%d" % (k + 5), k * 11.0, NORTH_Y - 3.5, 0, 4.5, 0.22, "green", 8)


def build_EastSide():
    X = 58.0
    with asset("ParishChurch"):
        box("parish_nave", X, 34.0, 8.0, 18, 30, 16, "brick"); box("parish_roof", X, 34.0, 17.5, 19, 31, 3.0, "brick")
        box("parish_tower", X - 6.0, 20.0, 14.0, 7, 7, 28, "stone"); box("parish_belfry", X - 6.0, 20.0, 29.0, 5.5, 5.5, 4.0, "stone")
        cone("parish_steeple", X - 6.0, 20.0, 37.0, 3.6, 12.0, "brick")
    with asset("EastBlocks"):
        for k in range(3):
            box("east_block_%d" % k, X + 4, 52.0 + k * 18, 8.0, 22, 16, 16, "brick_pale")


def build_WestSide():
    X = -58.0
    with asset("BlackChurch"):
        box("bc_nave", X, 30.0, 7.5, 16, 26, 15, "brick_pale"); box("bc_roof", X, 30.0, 16.0, 17, 27, 2.6, "brick_pale")
        box("bc_tower", X + 5.0, 18.0, 11.0, 6, 6, 22, "brick_pale"); box("bc_cross", X + 5.0, 18.0, 24.0, 0.4, 0.4, 4.0, "stone")
    with asset("PILFOffice"):
        storefront("pilf", X + 6, 52.0, 12, 15.0, 3, "brick", axis="x", face=1)
        o = box("pilf_sign", X + 6.35, 52.0, 8.0, 0.2, 6.0, 1.2, "banner"); o["backlot_text_plane"] = True
    with asset("WestShops"):
        for k in range(2):
            storefront("west_shop_%d" % k, X + 6, 70.0 + k * 14, 12, 15.0, 3, "brick_pale", axis="x", face=1)


def build_AxisStreet():
    with asset("AxisStreet"):
        box("axis_road", 0, (NORTH_Y + UNI_Y) / 2, 0.02, 14.0, UNI_Y - NORTH_Y + 8, 0.04, "road")
        for side in (-1, 1):
            box("axis_kerb_%d" % (side > 0), side * 7.5, (NORTH_Y + UNI_Y) / 2, 0.1, 1.0, UNI_Y - NORTH_Y + 8, 0.2, "stone")
            for k in range(4):
                storefront("axis_%d_%d" % (side > 0, k), side * 9.0, NORTH_Y + 8 + k * 12, 11, 16.0, 3,
                           "brick" if k % 2 else "brick_pale", axis="x", face=-side)
            for k in range(5):
                cyl("axis_lamp_%d_%d" % (side > 0, k), side * 7.0, NORTH_Y + 4 + k * 11, 0, 5.0, 0.14, "stone", 8)


def build_University():
    with asset("University"):
        box("uni_wall_w", -22, UNI_Y, 1.6, 30, 1.0, 3.2, "brick"); box("uni_wall_e", 22, UNI_Y, 1.6, 30, 1.0, 3.2, "brick")
        for sx in (-1, 1):
            box("uni_gate_pier_%d" % (sx > 0), sx * 6.0, UNI_Y, 3.0, 2.0, 2.0, 6.0, "stone")
            sphere("uni_gate_ball_%d" % (sx > 0), sx * 6.0, UNI_Y, 6.4, 0.9)
        box("uni_gate_arch", 0, UNI_Y, 6.6, 14.0, 1.6, 1.2, "stone")
        box("uni_quad", 0, UNI_Y + 26, -0.03, 60, 50, 0.1, "green")
        box("uni_hall", 0, UNI_Y + 54, 9.0, 46, 18, 18, "stone"); box("uni_hall_portico", 0, UNI_Y + 44.6, 6.0, 18, 1.2, 12, "stone")
        for k in range(6):
            cyl("uni_col_%d" % k, -7.5 + 3.0 * k, UNI_Y + 44.0, 0, 11.0, 0.55, "stone")
        for sx in (-1, 1):
            box("uni_range_%d" % (sx > 0), sx * 36, UNI_Y + 26, 7.0, 14, 46, 14, "brick")
        for k in range(6):
            cyl("uni_tree_%d" % k, -20 + 8 * k, UNI_Y + 14, 0, 5.5, 0.26, "green", 8)


def build_Ground():
    with asset("Ground"):
        box("ground", 0, 90, -0.2, 400, 400, 0.2, "road")


BUILDERS = [build_CityHall, build_Banner, build_Square, build_RallyStage, build_BuildSiteDressing, build_NorthRow,
            build_EastSide, build_WestSide, build_AxisStreet, build_University, build_Ground]

# asset id -> the states it has (assets absent from this table are stateless)
STATEFUL = {"RallyStage": STAGE_STATES, "BuildSite": ["joists", "half_decked", "beam_seated", "swept"]}

# ------------------------------------------------------------------ control points (world space) for the gate
CONTROL_POINTS = {
 "posts": [
   {"name": "post_L", "base": [-(ST_W / 2 - 0.4), Y_BACK + 0.3, ST_H], "top": [-(ST_W / 2 - 0.4), Y_BACK + 0.3, ST_H + 5.0]},
   {"name": "post_R", "base": [ST_W / 2 - 0.4, Y_BACK + 0.3, ST_H], "top": [ST_W / 2 - 0.4, Y_BACK + 0.3, ST_H + 5.0]},
 ],
 "deck_front": {"left": [-ST_W / 2, STAGE_Y + ST_D / 2, ST_H], "right": [ST_W / 2, STAGE_Y + ST_D / 2, ST_H]},
 "chair_band": {"top_left": [-ST_W / 2, STAGE_Y - 0.8, ST_H + 0.9], "bottom_right": [ST_W / 2, STAGE_Y - 0.8, ST_H]},
 "truss_beam": {"left": [-(ST_W / 2 - 0.4), Y_BACK + 0.3, ST_H + 5.0], "right": [ST_W / 2 - 0.4, Y_BACK + 0.3, ST_H + 5.0]},
}


BANNER_TEXT = ["WELCOME TO TWEEEDS' ERSATZGIVING GATHERING!",
               "NEW HARNOMY'S CELEBRATION OF CONTRITION, ATONEMENT AND REPENTANCE"]
BANNER_CONTROL = {
 "text_planes": [
   # the cloth's front face (toward the square, +Y), corners clockwise from top-left AS THE CAMERA SEES IT: a
   # camera in the square looks along -Y, so world +X is frame-left
   {"name": "banner", "text": BANNER_TEXT,
    "corners": [[7.0, R_COL + 0.225, 14.8], [-7.0, R_COL + 0.225, 14.8], [-7.0, R_COL + 0.225, 12.2], [7.0, R_COL + 0.225, 12.2]]},
 ],
}

CONTROL_POINTS_BY_ASSET = {"RallyStage": CONTROL_POINTS, "Banner": BANNER_CONTROL}


def build_all(only=None):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    for fn in BUILDERS:
        name = fn.__name__[6:]
        if only and name not in only:
            continue
        fn()
