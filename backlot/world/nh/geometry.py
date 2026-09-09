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
               timber=(0.85, 0.65, 0.35), banner=(0.55, 0.30, 0.42), brick=(0.55, 0.34, 0.28), mannequin=(0.80, 0.55, 0.50), hay=(0.78, 0.66, 0.36), pumpkin=(0.85, 0.45, 0.12), garland=(0.55, 0.40, 0.18),
               brick_pale=(0.66, 0.50, 0.42), shop=(0.35, 0.42, 0.44), glass=(0.30, 0.40, 0.50),
               rose=(0.64, 0.44, 0.48), paper=(0.86, 0.84, 0.79), felt=(0.52, 0.34, 0.38),
               white=(0.90, 0.89, 0.86), oak=(0.78, 0.68, 0.52), photo=(0.32, 0.30, 0.29), steel=(0.55, 0.56, 0.58),
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


def chair(name, cx, cy, z0, facing_deg=0.0, m="timber"):
    """A folding chair (seat, back, four legs). facing_deg 0 = facing +Y (the square); the back is behind the sitter.
    Phase 1 found box chairs read as crates in depth-conditioned keys; a chair-shaped silhouette fixes every shot at
    the source. The facing was added 2026-09-09 - chairs round a table must address the table, not all face north."""
    a = math.radians(facing_deg)
    ca, sa = math.cos(a), math.sin(a)

    def at(dx, dy):                       # rotate an offset in the chair's own frame into the world
        return cx + dx * ca - dy * sa, cy + dx * sa + dy * ca
    x, y = at(0, 0); box(name + "_seat", x, y, z0 + 0.45, 0.45, 0.45, 0.04, m, rot=a)
    x, y = at(0, -0.2); box(name + "_back", x, y, z0 + 0.72, 0.45, 0.04, 0.5, m, rot=a)
    for i, (dx, dy) in enumerate(((-0.2, -0.2), (0.2, -0.2), (-0.2, 0.2), (0.2, 0.2))):
        x, y = at(dx, dy); box(name + "_leg%d" % i, x, y, z0 + 0.22, 0.03, 0.03, 0.44, m)


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


def storefront(tag, x, y, w, depth, floors, m="brick", face=-1, axis="y", band=None):
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
        if band and band[0] == f:               # (floor, width, height, centre-above-floor): a glazed band, not three windows
            _, bw, bh, bzc = band
            z = 4.2 + 3.4 * (f - 1) + bzc
            if axis == "y":
                box("%s_band_%d" % (tag, f), x, y + face * 0.12, z, bw, 0.3, bh, "glass")
            else:
                box("%s_band_%d" % (tag, f), x + face * 0.12, y, z, 0.3, bw, bh, "glass")
            continue
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
NORTH_Y, UNI_Y = 74.0, 144.0        # the university gate closes the axis; UNI_Y set 2026-09-09 so FOUR
                                    # blocks of street fit between the row's back and the gate (the design
                                    # note in build_backlot.py: "four blocks up the axis street"). At the
                                    # old 120 only two fitted once the street stopped overlapping the row.

STAGE_STATES = ["joists", "half_decked", "beam_seated", "swept", "finished", "feast"]


# =================================================================== ASSETS
def build_CityHall():
    with asset("CityHall"):
        mb = box("main_block", 0, -8, 12, 64, 16, 24); box("main_cornice", 0, -8, 24.4, 65, 17, 0.8)
        # the Mayor's office cavity: the room runs from the drum back into the main block (build_PengoldOffice owns
        # its floor, ceiling, walls and furniture; the building only stops being solid there)
        _boolean(mb, box("office_cavity", 0, -3.0, (OFFICE_FLOOR + OFFICE_CEIL) / 2, 2 * (R_WALL - 0.4), 6.6, OFFICE_CEIL - OFFICE_FLOOR))
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
    # harvest dressing as DATA (the judge kept finding it missing when it lived only in adjectives): hay bales and
    # pumpkins along the stage front and beside the steps, garlands on the crossbeam; sheaves at the columns and
    # pumpkins on the granite steps belong to the building and live in build_HarvestDressing
    for st in ("finished", "feast"):
        with asset("RallyStage", st):
            rng = 901
            for k in range(-5, 6):
                if k % 2:
                    box("dress_hay_%s_%d" % (st, k + 5), k * 2.1, STAGE_Y + ST_D / 2 + 0.5, 0.22, 0.9, 0.45, 0.44, "hay")
                for j in range(2):
                    rng = (rng * 1103515245 + 12345) % 2 ** 31
                    r = 0.16 + 0.12 * ((rng >> 8) % 100) / 100.0
                    sphere("dress_pumpkin_%s_%d_%d" % (st, k + 5, j), k * 2.1 + (j - 0.5) * 0.6, STAGE_Y + ST_D / 2 + 0.25 + 0.4 * j, r, r, "pumpkin")
            for sx in (-1, 1):                                                          # beside the steps
                for j in range(3):
                    sphere("dress_pumpkin_steps_%s_%d_%d" % (st, sx > 0, j), sx * (ST_W / 2 + 1.6 + 0.35 * j), STAGE_Y + 1.2 - 0.3 * j, 0.22, 0.22, "pumpkin")
            _limb("dress_garland_%s" % st, (-(ST_W / 2 - 0.4), Y_BACK + 0.3 + 0.35, ST_H + 5.0 - 0.15), (ST_W / 2 - 0.4, Y_BACK + 0.3 + 0.35, ST_H + 5.0 - 0.15), 0.12, "garland")


def build_BuildSiteDressing():
    """Lumber stacks and the two vehicles: present during the build states, gone when finished."""
    for st in ("joists", "half_decked", "beam_seated", "swept"):
        with asset("BuildSite", st):
            for k, (lx, ly) in enumerate(((-20, STAGE_Y + 7), (4, STAGE_Y + 7), (16, STAGE_Y + 5.5))):
                box("lumber_%s_%d" % (st, k), lx, ly, 0.4, 5.0, 1.2, 0.8, "timber")
    with asset("Vehicles"):
        box("flatbed", -38, STAGE_Y + 4, 1.0, 2.5, 8.0, 1.2, "veh"); box("flatbed_cab", -38, STAGE_Y + 0.7, 1.9, 2.4, 2.2, 2.4, "veh")
        box("box_van", -38, STAGE_Y - 6, 1.4, 2.4, 6.0, 2.8, "veh")


# The north row is packed OUTWARD from the street mouth (2026-09-09): Axis Street's road is 14 m wide with kerbs to
# x = +-8, and the row used to run straight through it (shop_w1 -13..-3, bodega 5..15 - an 8 m mouth for a 14 m road).
# Lots are 1 m narrower than before so the row's ends stay where they were (-49.7 .. 49.7); 0.4 m party gaps.
MOUTH = 8.5
NORTH_ROW_WEST = [("shop_w1", 9, 3, "brick_pale"), ("restaurant", 11, 3, "brick"), ("shop_w2", 10, 4, "brick_pale"), ("shop_w3", 10, 3, "brick")]
NORTH_ROW_EAST = [("bodega", 9, 2, "brick"), ("shop_e1", 10, 3, "brick_pale"), ("shop_e2", 11, 4, "brick"), ("shop_e3", 10, 3, "brick_pale")]


def _pack_row():
    lots = {}
    for side, spec in ((-1, NORTH_ROW_WEST), (1, NORTH_ROW_EAST)):
        edge = MOUTH
        for tag, w, floors, m in spec:
            lots[tag] = (side * (edge + w / 2.0), w, floors, m); edge += w + 0.4
    return lots


NORTH_ROW = _pack_row()             # tag -> (x, w, floors, material)
BODEGA_X = NORTH_ROW["bodega"][0]


def build_NorthRow():
    for tag, (x, w, floors, m) in NORTH_ROW.items():
        aid = {"restaurant": "Restaurant", "bodega": "Bodega"}.get(tag, "NorthRow")
        with asset(aid):
            # LYSTERIA re-fronted shop_e1's upper floor as one glazed band when it moved in - the one shop on the row
            # with a modern glass first floor is the one with money (POV contract: the room's window IS this band)
            storefront(tag, x, NORTH_Y, w, 16.0, floors, m,
                       band=(1, LYST_BAND_W, LYST_BAND_H, LYST_BAND_ZC) if tag == "shop_e1" else None)
            if tag == "shop_e1":     # the block stops being solid where the room is (as City Hall does for the office)
                _boolean(bpy.data.objects["shop_e1_block"], box("lyst_cavity", LYST_X, LYST_Y, 4.2 + 1.6, LYST_W - 0.2, LYST_D - 0.2, 3.3))
                _boolean(bpy.data.objects["shop_e1_block"], box("lyst_band_punch", LYST_X, NORTH_Y + 0.55, 4.2 + LYST_BAND_ZC, LYST_BAND_W, 1.3, LYST_BAND_H))
    with asset("Bodega"):           # the awning and crates ride with the lot
        box("bodega_awning", BODEGA_X, NORTH_Y - 1.6, 3.5, 8.0, 3.0, 0.2, "banner")
        for k in range(3):
            box("bodega_crate_%d" % k, BODEGA_X - 4.0 + 1.2 * k, NORTH_Y - 1.2, 0.4, 1.0, 0.8, 0.8, "timber")
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
        _boolean(bpy.data.objects["pilf_block"], box("pilf_cavity", PILF_X, PILF_Y, 1.8, 13.0 - 0.2, 11.0 - 0.2, 3.7))   # the PILF room
        _boolean(bpy.data.objects["pilf_block"], box("pilf_win_punch", PILF_X + 6.9, PILF_Y, 1.6, 1.2, 6.0, 1.8))          # ...and its shopfront glass through the skin
        o = box("pilf_sign", X + 6.35, 52.0, 8.0, 0.2, 6.0, 1.2, "banner"); o["backlot_text_plane"] = True
    with asset("WestShops"):
        for k in range(2):
            storefront("west_shop_%d" % k, X + 6, 70.0 + k * 14, 12, 15.0, 3, "brick_pale", axis="x", face=1)


# Axis Street's lots: 11 m frontages on a 12 m pitch, from a metre behind the north row (NORTH_Y + 16) up to the
# university wall. AXIS_LOTS is how many whole lots that gap holds - move UNI_Y and the street re-lots itself.
AXIS_Y0, AXIS_W, AXIS_PITCH = NORTH_Y + 17.0, 11.0, 12.0
AXIS_LOTS = max(0, int((UNI_Y - 1.0 - AXIS_Y0 - AXIS_W) // AXIS_PITCH) + 1)


def build_AxisStreet():
    with asset("AxisStreet"):
        box("axis_road", 0, (NORTH_Y + UNI_Y) / 2, 0.02, 14.0, UNI_Y - NORTH_Y + 8, 0.04, "road")
        for side in (-1, 1):
            box("axis_kerb_%d" % (side > 0), side * 7.5, (NORTH_Y + UNI_Y) / 2, 0.1, 1.0, UNI_Y - NORTH_Y + 8, 0.2, "stone")
            # the street's own blocks start BEYOND the north row's depth (NORTH_Y + 16): the row is the square's frontage
            # and the street cuts through it; before 2026-09-09 the first block sat at y 76.5..87.5, inside shop_e1.
            # How many lots fit is DERIVED from the gap to the university wall, so moving UNI_Y re-lots the street.
            for k in range(AXIS_LOTS):
                storefront("axis_%d_%d" % (side > 0, k), side * 9.0, AXIS_Y0 + AXIS_W / 2.0 + k * AXIS_PITCH, AXIS_W, 16.0, 3,
                           "brick" if k % 2 else "brick_pale", axis="x", face=-side)
            for k in range(int((UNI_Y - NORTH_Y - 8) // 11) + 1):        # lamps the length of the street, 11 m apart
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



# ----------------------------------------------------------------------------- interiors (Phase 3, task 20)
# Interior sets are registered to the world at their true position: Pengold's office IS the inside of the drum
# behind the SH006 window, so a POV out of it and a wide of the square agree by construction (the POV contract).
# Blockout grade: walls, floor, ceiling, windows, the furniture the libretto names, and MARKS for the mannequins.
OFFICE_FLOOR, OFFICE_CEIL = 5.4, 10.4          # 1962 renovation inside the 1910 drum: a dropped ceiling at 5 m
PILF_X, PILF_Y = -59.5, 52.0                    # centre of the PILF storefront block (build_WestSide)
LYST_X, LYST_Y = NORTH_ROW["shop_e1"][0], NORTH_Y + 8.0     # LYSTERIA: the upper floor of shop_e1 on the north row (follows the lot)
LYST_W, LYST_D = NORTH_ROW["shop_e1"][1] - 1.0, 14.0        # the room fills the lot less a 0.5 m party wall each side
LYST_BAND_W, LYST_BAND_H, LYST_BAND_ZC = NORTH_ROW["shop_e1"][1] - 2.4, 2.3, 1.85   # the glazed band: sill 0.7, head 3.0 above her floor
LYST_GLASS_Y = NORTH_Y + 8.0 - 14.0 / 2 + 5.6                # the glass wall between Summer's office (south, the band) and the floor


def build_PengoldOffice():
    """The Mayor's office: the half-disc room behind the colonnade plus a rectangle into the main block.
    Windows are the drum's three French windows (already cut in build_CityHall); this asset owns the floor,
    ceiling, back wall, door and furniture, in two states: "dawn" (opening) and "meeting" (Act II Betrayal, door ajar)."""
    z0, zc = OFFICE_FLOOR, OFFICE_CEIL
    with asset("PengoldOffice"):
        box("po_floor", 0, 1.0, z0 - 0.05, 2 * (R_WALL - 0.4), 2 * (R_WALL - 0.4) + 12.0, 0.1, "timber")
        box("po_ceiling", 0, 1.0, zc + 0.1, 2 * (R_WALL - 0.4), 2 * (R_WALL - 0.4) + 12.0, 0.2, "stone")
        box("po_back_wall", 0, -6.0, (z0 + zc) / 2, 2 * (R_WALL - 0.4), 0.3, zc - z0, "stone")
        for sx in (-1, 1):
            box("po_side_wall_%d" % (sx > 0), sx * (R_WALL - 0.55), -3.0, (z0 + zc) / 2, 0.3, 6.0, zc - z0, "stone")
        # drapes flanking each French window (heavy - "Tammany Hall echoed by an ornate office with heavy drapes")
        for k in range(3):
            a = math.radians(50 + 40 * k)
            for da in (-0.14, 0.14):
                box("po_drape_%d_%d" % (k, da > 0), (R_WALL - 0.7) * math.cos(a + da), (R_WALL - 0.7) * math.sin(a + da),
                    (z0 + zc) / 2, 0.5, 0.25, zc - z0 - 0.4, "banner", rot=a + da)
        box("po_desk", 0, -2.0, z0 + 0.72, 2.0, 0.9, 0.06, "timber"); box("po_desk_body", 0, -2.0, z0 + 0.36, 1.9, 0.8, 0.7, "timber")
        box("po_desk_chair", 0, -3.0, z0 + 0.45, 0.6, 0.6, 0.9, "timber")
        box("po_credenza", 0, -5.6, z0 + 0.4, 2.4, 0.5, 0.8, "timber")
        for k in range(3):                                     # three mauve books, stacked, on the credenza
            box("po_book_%d" % k, 0.6, -5.6, z0 + 0.8 + 0.035 + 0.07 * k, 0.16, 0.24, 0.07, "banner")
        box("po_book_desk", 0.55, -1.85, z0 + 0.78, 0.16, 0.24, 0.04, "banner")     # the pristine copy, squared
        box("po_lamp_base", -0.7, -1.7, z0 + 0.77, 0.16, 0.16, 0.04, "stone"); cyl("po_lamp_stem", -0.7, -1.7, z0 + 0.79, z0 + 1.25, 0.015, "stone")
        cone("po_lamp_shade", -0.7, -1.7, z0 + 1.25, 0.18, 0.16, "banner")
        cyl("po_cup", 0.45, -2.25, z0 + 0.75, z0 + 0.84, 0.04, "stone")
        box("po_newspaper", -0.1, -2.05, z0 + 0.76, 0.3, 0.2, 0.02, "stone")
        box("po_portrait", -5.0, -5.85, z0 + 2.2, 0.5, 0.04, 0.65, "banner")       # Summer's portrait, small, background
    with asset("PengoldOffice", "dawn"):
        box("po_door_closed", -6.5, -5.85, z0 + 1.05, 1.0, 0.1, 2.1, "timber")
    with asset("PengoldOffice", "meeting"):
        box("po_door_ajar", -6.85, -5.5, z0 + 1.05, 1.0, 0.1, 2.1, "timber", rot=math.radians(-35))


def _interior_room(tag, cx, cy, w, d, z0, h, m="stone", door=None, windows=(), floor_m="timber", win_h=1.8, win_zc=None,
                   door_m="timber"):
    """A room as walls, floor, ceiling, a door and window cuts (with glass). windows: (x, y, width) on any wall; the
    cut is win_h tall centred win_zc above the floor (default 1.6 - a domestic window; LYSTERIA's glazed band is
    2.3 tall at 1.85)."""
    zc = z0 + (1.6 if win_zc is None else win_zc)
    box("%s_floor" % tag, cx, cy, z0 - 0.05, w, d, 0.1, floor_m)
    box("%s_ceiling" % tag, cx, cy, z0 + h + 0.1, w, d, 0.2, m)
    for name, x, y, sx, sy in (("n", cx, cy + d / 2, w, 0.25), ("s", cx, cy - d / 2, w, 0.25),
                               ("e", cx + w / 2, cy, 0.25, d), ("w", cx - w / 2, cy, 0.25, d)):
        wall = box("%s_wall_%s" % (tag, name), x, y, z0 + h / 2, sx, sy, h, m)
        for k, (wx, wy, ww) in enumerate(windows):
            if abs(wx - x) < 0.3 or abs(wy - y) < 0.3:
                # the cut runs ALONG the wall: a wall long in x gets a cut wide in x (fixed 2026-09-09: the axes were
                # swapped and a 6 m shopfront came out as a 0.6 m slit)
                along_x = sx > sy
                _boolean(wall, box("%s_win_cut_%d" % (tag, k), wx, wy, zc, ww if along_x else 0.6, 0.6 if along_x else ww, win_h))
                box("%s_win_%d" % (tag, k), wx, wy, zc, ww if along_x else 0.06, 0.06 if along_x else ww, win_h, "glass")
    if door:
        box("%s_door" % tag, door[0], door[1], z0 + 1.05, 1.0 if abs(door[1] - cy) > abs(door[0] - cx) else 0.1,
            0.1 if abs(door[1] - cy) > abs(door[0] - cx) else 1.0, 2.1, door_m)


def build_HarvestDressing():
    """Corn-stalk sheaves tied to the columns and pumpkins on the granite steps: present in the finished and feast
    states of the square (the RallyStage's own dressing rides with the stage; this rides with the building)."""
    for st in ("finished", "feast"):
        with asset("HarvestDressing", st):
            for k in range(8):
                a = math.radians(20 + 20 * k)
                x, y = R_COL * math.cos(a), R_COL * math.sin(a)
                cone("dress_sheaf_%s_%d" % (st, k), x + 0.9 * math.cos(a), y + 0.9 * math.sin(a), 5.4, 0.45, 2.6, "hay")
            for k in range(7):
                sphere("dress_pumpkin_step_%s_%d" % (st, k), -5.0 + 1.7 * k, R_COL + 1.4 + 0.4 * (k % 3), 5.0 - 0.83 * (k % 3 + 1) + 0.6, 0.24, "pumpkin")


def build_PILFInterior():
    """The PILF office: the ground floor of the storefront on the west side - a campaign office, folding tables,
    a petition table by the door, the sign's back visible through the shopfront glass."""
    with asset("PILFInterior"):
        _interior_room("pilf_in", PILF_X, PILF_Y, 13.0, 11.0, 0.0, 3.6, "brick", door=(PILF_X + 6.4, PILF_Y - 4.0),
                       windows=((PILF_X + 6.5, PILF_Y, 6.0),))
        for k in range(3):
            box("pilf_table_%d" % k, PILF_X - 3.0 + 3.0 * k, PILF_Y + 2.0, 0.74, 1.8, 0.8, 0.05, "timber")
            box("pilf_table_legs_%d" % k, PILF_X - 3.0 + 3.0 * k, PILF_Y + 2.0, 0.36, 1.6, 0.6, 0.7, "timber")
        box("pilf_petition_table", PILF_X + 4.5, PILF_Y - 3.0, 0.74, 1.2, 0.6, 0.05, "timber")
        box("pilf_petition_table_legs", PILF_X + 4.5, PILF_Y - 3.0, 0.36, 1.0, 0.45, 0.7, "timber")
        for k in range(3):                                                          # a folding chair behind each table
            chair("pilf_chair_%d" % k, PILF_X - 3.0 + 3.0 * k, PILF_Y + 2.9, 0.0, 180.0)
        box("pilf_wall_board", PILF_X - 6.3, PILF_Y, 1.8, 0.05, 6.0, 1.6, "banner")


def build_LysteriaInterior():
    """LYSTERIA Coalition for Reproductive Justice - Summer's office, the upper floor of shop_e1, re-fronted in glass.

    DESIGN (Brad, 2026-09-09, evaluated against the bible before building - see 03_design/environments/lysteria_office.md):
    all white, walls and floor, the brand rose as the only accent; the aesthetic of a high-end London PR company.
    A glass wall divides the floor (north, the door end) from Summer's own office (south, the glazed band onto the
    square): status and surveillance in one wall - she sees the floor, the floor sees her. LYSTERIA is spelled on the
    wall behind reception in the rose (a text plane, lettered by the gate; a wordmark in type, never a logo mark - kernel
    negative). The causes are instruments: campaign banners framed, photographs hung museum-spaced with her in every
    one. THE LAW: the set never states the reading. Everything here is beautiful and certain; nothing in the room
    knows it is a joke (THE_CASTE: "a smug face is a wink", and a set is a face).

    The void where Philip was, twice, neither of them aged paint (there is none in a white room): her nameplate on the
    glass door reads SUMMER WINTERS - his name, kept, the bible's own pun - and the gallery grid has one gap with the
    hook still in the wall.

    States (variantSet "lysteria"): working (default) | launch (the Man Bun Collective rollout staged, cartons still
    shrink-wrapped). People: build_Mannequins state "lysteria" - Summer at her desk, the staff on the floor.
    """
    z0, H = 4.2, 3.2
    W, D = LYST_W, LYST_D
    xw, xe = LYST_X - W / 2 + 0.14, LYST_X + W / 2 - 0.14          # interior faces of the west and east walls
    ys, yn = LYST_Y - D / 2, LYST_Y + D / 2                        # south = the glazed band onto the square, north = door
    yg = LYST_GLASS_Y                                              # the glass wall
    dx, dy = LYST_X + 1.2, ys + 1.9                                # Summer's desk, backed by the band
    bx = LYST_X - 0.7                                              # the staff benches' centre line

    with asset("LysteriaInterior"):
        _interior_room("lyst_in", LYST_X, LYST_Y, W, D, z0, H, "white", floor_m="white", door_m="white",
                       door=(LYST_X - W / 2 + 1.0, yn - 0.1), windows=((LYST_X, ys, LYST_BAND_W),),
                       win_h=LYST_BAND_H, win_zc=LYST_BAND_ZC)

        # --- the glass wall, with her door in it at the west end and a slim white frame
        box("lyst_glass_wall", LYST_X + 0.55, yg, z0 + H / 2, W - 0.28 - 1.1, 0.03, H, "glass")
        box("lyst_glass_door", xw + 0.55, yg, z0 + 1.05, 1.0, 0.03, 2.1, "glass")
        box("lyst_glass_transom", xw + 0.55, yg, z0 + 2.65, 1.1, 0.03, 1.1, "glass")
        box("lyst_glass_head", LYST_X, yg, z0 + H - 0.04, W - 0.28, 0.08, 0.08, "white")
        box("lyst_glass_sill", LYST_X, yg, z0 + 0.03, W - 0.28, 0.08, 0.06, "white")
        for k, mx in enumerate((xw + 1.1, LYST_X + 0.55, xe)):
            box("lyst_glass_mullion_%d" % k, mx - (0.02 if k == 2 else 0.0), yg, z0 + H / 2, 0.05, 0.06, H, "white")
        # her name on the door: a frosted strip at eye height, the letters go on by the gate ("SUMMER WINTERS")
        box("lyst_nameplate", xw + 0.55, yg - 0.025, z0 + 1.52, 0.46, 0.012, 0.075, "paper")

        # --- FLOOR: reception against the east wall by the door, the wordmark on the wall behind it
        box("lyst_reception", xe - 1.05, yn - 2.2, z0 + 0.52, 0.62, 2.1, 1.04, "white")
        box("lyst_reception_top", xe - 1.05, yn - 2.2, z0 + 1.06, 0.70, 2.2, 0.04, "oak")
        chair("lyst_reception_chair", xe - 0.42, yn - 2.2, z0, 90.0, "white")
        box("lyst_wordmark", xe - 0.02, yn - 2.2, z0 + 1.95, 0.02, 3.0, 0.62, "white")          # the surface the gate letters, rose ink
        # a framed campaign banner further down the east wall - the accent, one of two on the floor
        box("lyst_banner_frame_0", xe - 0.04, yg + 2.2, z0 + 1.85, 0.06, 2.4, 1.25, "white")
        box("lyst_banner_cloth_0", xe - 0.08, yg + 2.2, z0 + 1.85, 0.03, 2.2, 1.05, "rose")
        # the gallery wall: photographs museum-spaced, two rows of five, her in every one - and ONE gap, hook still in
        for r in range(2):
            for c in range(5):
                gy, gz = yg + 1.4 + 1.15 * c, z0 + 1.30 + 0.82 * r
                if (r, c) == (1, 2):
                    cyl("lyst_gallery_hook", xw + 0.03, gy, gz + 0.28, gz + 0.31, 0.012, "steel")   # the void
                    continue
                box("lyst_photo_frame_%d_%d" % (r, c), xw + 0.03, gy, gz, 0.04, 0.58, 0.72, "white")
                box("lyst_photo_%d_%d" % (r, c), xw + 0.055, gy, gz, 0.01, 0.48, 0.62, "photo")
        # staff benches: two white benches, two seats each facing across, linear pendants over them
        for k in range(2):
            by = yg + 1.9 + 2.6 * k
            box("lyst_bench_%d" % k, bx, by, z0 + 0.72, 2.4, 1.3, 0.05, "white")
            for sx in (-1, 1):
                box("lyst_bench_leg_%d_%d" % (k, sx > 0), bx + sx * 1.1, by, z0 + 0.35, 0.08, 1.1, 0.70, "white")
            box("lyst_bench_screen_%d" % k, bx, by, z0 + 0.92, 2.2, 0.03, 0.35, "rose")            # a low rose modesty screen down the middle
            chair("lyst_staff_chair_%d_0" % k, bx - 0.55, by - 0.95, z0, 0.0, "white")
            chair("lyst_staff_chair_%d_1" % k, bx + 0.55, by + 0.95, z0, 180.0, "white")
            box("lyst_pendant_%d" % k, bx, by, z0 + 2.45, 2.0, 0.08, 0.05, "steel")
            for sx in (-1, 1):
                cyl("lyst_pendant_drop_%d_%d" % (k, sx > 0), bx + sx * 0.8, by, z0 + 2.47, z0 + H, 0.006, "steel")
        # the mauve shelf, low, on the floor's west wall under the gallery: the movement's reading, the opera's motif
        box("lyst_shelf", xw + 0.22, yn - 1.4, z0 + 0.40, 0.32, 1.9, 0.80, "white")
        for k in range(8):
            box("lyst_book_%d" % k, xw + 0.22, yn - 2.2 + 0.235 * k, z0 + 0.92, 0.15, 0.2, 0.24, "banner")

        # --- SUMMER'S OFFICE: her desk against the band, facing the floor; the visitor sits with the light in their face
        box("lyst_desk", dx, dy, z0 + 0.74, 2.2, 0.9, 0.05, "white")
        box("lyst_desk_body", dx + 0.7, dy, z0 + 0.36, 0.7, 0.8, 0.70, "white")
        box("lyst_desk_leg", dx - 1.0, dy, z0 + 0.36, 0.06, 0.8, 0.70, "steel")
        chair("lyst_desk_chair", dx, dy - 0.75, z0, 0.0, "white")
        for sx in (-1, 1):
            chair("lyst_visitor_%d" % (sx > 0), dx + sx * 0.55, dy + 0.85, z0, 180.0, "white")
        box("lyst_lamp_base", dx - 0.8, dy - 0.2, z0 + 0.79, 0.16, 0.16, 0.04, "steel")
        cyl("lyst_lamp_stem", dx - 0.8, dy - 0.2, z0 + 0.81, z0 + 1.24, 0.015, "steel")
        cone("lyst_lamp_shade", dx - 0.8, dy - 0.2, z0 + 1.24, 0.17, 0.15, "rose")                 # the one warm practical
        box("lyst_book_desk", dx + 0.55, dy + 0.05, z0 + 0.79, 0.16, 0.24, 0.04, "banner")        # her copy: annotated, squared
        # the sofa for the chat, against her west wall, a low oak table
        box("lyst_sofa", xw + 0.55, ys + 2.6, z0 + 0.22, 0.85, 1.9, 0.44, "white")
        box("lyst_sofa_back", xw + 0.20, ys + 2.6, z0 + 0.62, 0.15, 1.9, 0.40, "white")
        box("lyst_coffee_table", xw + 1.45, ys + 2.6, z0 + 0.40, 0.6, 1.1, 0.03, "oak")
        for k in range(4):
            cyl("lyst_coffee_leg_%d" % k, xw + 1.45 + (0.22 if k % 2 else -0.22), ys + 2.6 + (0.45 if k > 1 else -0.45), z0, z0 + 0.39, 0.012, "steel")
        # her east wall: the plaque grid - twelve grants and awards, white frames, what the room is proud of
        for k in range(12):
            box("lyst_plaque_%d" % k, xe - 0.03, ys + 1.6 + 0.44 * (k % 4), z0 + 1.30 + 0.46 * (k // 4), 0.05, 0.32, 0.38, "paper")
        # her west wall, above the sofa: the second framed campaign banner
        box("lyst_banner_frame_1", xw + 0.04, ys + 2.6, z0 + 2.05, 0.06, 1.7, 0.95, "white")
        box("lyst_banner_cloth_1", xw + 0.08, ys + 2.6, z0 + 2.05, 0.03, 1.5, 0.78, "rose")

    with asset("LysteriaInterior", "working"):
        box("lyst_papers_0", bx - 0.6, yg + 1.6, z0 + 0.77, 0.30, 0.42, 0.04, "paper")
        box("lyst_papers_1", bx + 0.7, yg + 4.8, z0 + 0.77, 0.30, 0.42, 0.03, "paper")
        box("lyst_docbox", xe - 1.05, yn - 2.2, z0 + 1.23, 0.40, 0.30, 0.28, "paper")           # one archive box on reception

    with asset("LysteriaInterior", "launch"):
        # The Man Bun Collective rollout: six months of branding and no services, staged where an arrival meets it.
        # west of the benches, angled toward the door: an arrival meets them; the visitor's sightline to Summer stays clear
        for k, ex in enumerate((xw + 1.5, xw + 2.6)):
            by = yg + 0.75 + 0.55 * k
            for sx in (-1, 1):
                cyl("lyst_easel_leg_%d_%d" % (k, sx > 0), ex + sx * 0.36, by, z0, z0 + 1.50, 0.025, "white")
            cyl("lyst_easel_rake_%d" % k, ex, by - 0.40, z0, z0 + 1.38, 0.025, "white")
            box("lyst_easel_ledge_%d" % k, ex, by + 0.02, z0 + 0.70, 0.78, 0.07, 0.05, "white")
            box("lyst_mbc_board_%d" % k, ex, by + 0.05, z0 + 1.22, 0.82, 0.04, 1.00, "paper")
        for k in range(4):                                   # tote cartons, still shrink-wrapped, stacked by reception
            box("lyst_mbc_carton_%d" % k, xe - 2.1 - 0.66 * (k % 2), yn - 0.55, z0 + 0.32 + 0.64 * (k // 2), 0.6, 0.6, 0.6, "paper")
        for k in range(2):
            box("lyst_tote_stack_%d" % k, bx + 0.6, yg + 1.9 + 2.6 * k + 0.35, z0 + 0.85, 0.44, 0.34, 0.20, "rose")
        cyl("lyst_sash_pole", xw + 0.6, yg + 2.4, z0, z0 + 2.2, 0.03, "steel")                    # the sash on its stand
        box("lyst_sash_arm", xw + 0.6, yg + 2.4, z0 + 2.18, 0.62, 0.04, 0.04, "steel")
        box("lyst_sash", xw + 0.6, yg + 2.43, z0 + 1.50, 0.56, 0.03, 1.32, "rose")


def _limb(name, a, b, r, m="mannequin"):
    """A cylinder from point a to point b (metres), radius r."""
    import mathutils
    a = mathutils.Vector(a); b = mathutils.Vector(b); d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=r, depth=max(d.length, 0.01), location=(a + b) / 2)
    o = bpy.context.object; o.name = name
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    o.data.materials.append(mat(m)); return _tag(o)


def mannequin(name, x, y, z0, facing_deg=0.0, height=1.75, posture="standing"):
    """A HUMAN-SHAPED figure on a mark: head, neck, shoulders, tapered torso, upper arms, forearms, thighs, shins -
    enough silhouette for a depth/edge pass to read "a person" (a box-and-sphere figure was drawn as a bust on the
    credenza, 0/10 takes, 2026-09-08). Identity still comes from the generation layer, never from here.
    posture "seated": thighs horizontal toward +facing, shins vertical, forearms forward on a desk at 0.72 m."""
    import mathutils
    h = height
    R = mathutils.Matrix.Rotation(math.radians(facing_deg), 3, "Z")
    def P(dx, dy, dz):                      # body-local (x right, y forward, z up) -> world
        v = R @ mathutils.Vector((dx, dy, dz)); return (x + v.x, y + v.y, z0 + dz)
    sh_w, hip_w = 0.22 * h, 0.16 * h
    if posture == "seated":
        seat = 0.26 * h                     # seat height ~0.45 m at 1.75
        hip, shoulder = seat, seat + 0.34 * h
        head = shoulder + 0.115 * h
        for sx in (-1, 1):
            _limb(name + "_thigh_%d" % (sx > 0), P(sx * hip_w * 0.4, 0.0, hip), P(sx * hip_w * 0.4, 0.24 * h, hip), 0.075)
            _limb(name + "_shin_%d" % (sx > 0), P(sx * hip_w * 0.4, 0.24 * h, hip), P(sx * hip_w * 0.4, 0.24 * h, 0.02), 0.06)
            _limb(name + "_upperarm_%d" % (sx > 0), P(sx * sh_w * 0.5, 0.0, shoulder), P(sx * sh_w * 0.55, 0.10 * h, shoulder - 0.16 * h), 0.05)
            _limb(name + "_forearm_%d" % (sx > 0), P(sx * sh_w * 0.55, 0.10 * h, shoulder - 0.16 * h), P(sx * sh_w * 0.35, 0.28 * h, shoulder - 0.14 * h), 0.045)
    else:
        hip, shoulder = 0.52 * h, 0.82 * h
        head = shoulder + 0.115 * h
        for sx in (-1, 1):
            _limb(name + "_thigh_%d" % (sx > 0), P(sx * hip_w * 0.4, 0.0, hip), P(sx * hip_w * 0.4, 0.0, 0.27 * h), 0.075)
            _limb(name + "_shin_%d" % (sx > 0), P(sx * hip_w * 0.4, 0.0, 0.27 * h), P(sx * hip_w * 0.4, 0.02, 0.02), 0.06)
            _limb(name + "_upperarm_%d" % (sx > 0), P(sx * sh_w * 0.5, 0.0, shoulder), P(sx * sh_w * 0.58, 0.0, shoulder - 0.17 * h), 0.05)
            _limb(name + "_forearm_%d" % (sx > 0), P(sx * sh_w * 0.58, 0.0, shoulder - 0.17 * h), P(sx * sh_w * 0.6, 0.05, shoulder - 0.32 * h), 0.045)
    # torso: hips box, chest box a little wider, shoulders bar, neck, head
    box(name + "_hips", *P(0, 0, hip + 0.06 * h), hip_w * 1.9, 0.13 * h, 0.14 * h, "mannequin", rot=math.radians(facing_deg))
    box(name + "_chest", *P(0, 0, shoulder - 0.10 * h), sh_w * 1.8, 0.14 * h, 0.20 * h, "mannequin", rot=math.radians(facing_deg))
    _limb(name + "_shoulders", P(-sh_w * 0.5, 0, shoulder), P(sh_w * 0.5, 0, shoulder), 0.05)
    _limb(name + "_neck", P(0, 0, shoulder), P(0, 0, shoulder + 0.05 * h), 0.04)
    sphere(name + "_head", *P(0, 0.01, head), 0.065 * h, "mannequin")


def build_Mannequins():
    """Mannequins on their marks, one state per scene family; empty when the scene has nobody."""
    with asset("Mannequins", "office_dawn"):
        mannequin("man_pengold", 0, -3.0, OFFICE_FLOOR, 0.0, 1.78, posture="seated")   # seated at the desk chair, facing the windows
    with asset("Mannequins", "feast"):
        mannequin("man_pengold", 0, STAGE_Y + 1.0, ST_H, 0.0)                 # at the podium
        mannequin("man_summer", 2.0, Y_BACK + 1.5, ST_H, 0.0)                 # beneath the portrait
        mannequin("man_dick", -6.0, STAGE_Y - 0.5, ST_H, 90.0)
        mannequin("man_valencia", 9.0, Y_BACK + 1.0, ST_H, 0.0)               # upstage right, her own light
    with asset("Mannequins", "build"):
        for k, (x, y) in enumerate(((ST_W / 2 - 1.2, Y_BACK + 0.8), (ST_W / 2 - 2.2, Y_BACK + 1.6), (ST_W / 2 - 0.4, STAGE_Y + 1.5))):
            mannequin("man_worker_%d" % k, x, y, 0.0, 180.0)
    with asset("Mannequins", "lysteria"):
        # Summer at her desk behind the glass; the staff on the floor (props for now - casting note in the set bible:
        # handmaidens, revolutionary chic, all attractive and younger than her; two men in glasses, different bodies)
        z0, ys, yg, xe = 4.2, LYST_Y - LYST_D / 2, LYST_GLASS_Y, LYST_X + LYST_W / 2 - 0.14
        dx, dy, bx = LYST_X + 1.2, ys + 1.9, LYST_X - 0.7
        mannequin("man_summer", dx, dy - 0.75, z0, 0.0, 1.72, posture="seated")
        mannequin("man_staff_reception", xe - 0.42, LYST_Y + LYST_D / 2 - 2.2, z0, 90.0, 1.64, posture="seated")
        for k, (h, sx, sy, f) in enumerate(((1.62, -0.55, -0.95, 0.0), (1.80, 0.55, 0.95, 180.0), (1.67, -0.55, -0.95, 0.0), (1.76, 0.55, 0.95, 180.0))):
            mannequin("man_staff_%d" % k, bx + sx, yg + 1.9 + 2.6 * (k // 2) + sy, z0, f, h, posture="seated")


BUILDERS = [build_PengoldOffice, build_PILFInterior, build_LysteriaInterior, build_Mannequins, build_HarvestDressing,
            build_CityHall, build_Banner, build_Square, build_RallyStage, build_BuildSiteDressing, build_NorthRow,
            build_EastSide, build_WestSide, build_AxisStreet, build_University, build_Ground]

# asset id -> the states it has (assets absent from this table are stateless)
STATEFUL = {"RallyStage": STAGE_STATES, "BuildSite": ["joists", "half_decked", "beam_seated", "swept"],
            "PengoldOffice": ["dawn", "meeting"], "Mannequins": ["office_dawn", "feast", "build", "lysteria"],
            "HarvestDressing": ["finished", "feast"], "LysteriaInterior": ["working", "launch"]}
# one variantSet on /World per state FAMILY; each drives only the assets listed (an asset absent from a family is
# untouched by that family's selection). "none" deactivates the asset.
STATE_FAMILIES = {
    "build":  dict(states=STAGE_STATES, assets=["RallyStage", "BuildSite", "HarvestDressing"], default="finished"),
    "office": dict(states=["dawn", "meeting"], assets=["PengoldOffice"], default="dawn"),
    "people": dict(states=["none", "office_dawn", "feast", "build", "lysteria"], assets=["Mannequins"], default="none"),
    "lysteria": dict(states=["working", "launch"], assets=["LysteriaInterior"], default="working"),
}

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

OFFICE_CONTROL = {
 "marks": [   # where a body stands or sits; facing in degrees (0 = toward +Y, the windows and the square)
   {"name": "desk_chair", "pos": [0.0, -3.0, OFFICE_FLOOR], "facing_deg": 0.0, "posture": "seated"},
   {"name": "window_centre", "pos": [0.0, R_WALL - 1.2, OFFICE_FLOOR], "facing_deg": 0.0, "posture": "standing"},
   {"name": "door", "pos": [-6.5, -5.0, OFFICE_FLOOR], "facing_deg": 180.0, "posture": "standing"},
 ],
}
# LYSTERIA (Summer's office). Facing 0 = toward +Y, i.e. AWAY from the windows and into the room; she sits with the
# square behind her. The mission statement is a text plane on the east wall, lettered by the gate, not by the diffusion.
LYST_WORDMARK_TEXT = ["LYSTERIA"]                 # the org's name, in the rose; a wordmark in type, never a logo mark
LYST_NAMEPLATE_TEXT = ["SUMMER WINTERS"]          # his name, kept - the bible's pun (abundance turned to barrenness) lives here
LYST_CONTROL = {
 "marks": [   # facing 0 = toward +Y (into the floor, away from the band); the desk chair faces the floor through the glass
   {"name": "desk_chair", "pos": [LYST_X + 1.2, LYST_Y - 7.0 + 1.9 - 0.75, 4.2], "facing_deg": 0.0, "posture": "seated"},
   {"name": "visitor_chair", "pos": [LYST_X + 0.65, LYST_Y - 7.0 + 1.9 + 0.85, 4.2], "facing_deg": 180.0, "posture": "seated"},
   {"name": "sofa", "pos": [LYST_X - LYST_W / 2 + 0.69, LYST_Y - 7.0 + 2.6, 4.2], "facing_deg": 270.0, "posture": "seated"},
   {"name": "glass_door", "pos": [LYST_X - LYST_W / 2 + 0.69, LYST_GLASS_Y + 0.7, 4.2], "facing_deg": 180.0, "posture": "standing"},
   {"name": "reception", "pos": [LYST_X + LYST_W / 2 - 0.56, LYST_Y + 7.0 - 2.2, 4.2], "facing_deg": 90.0, "posture": "seated"},
   {"name": "floor_centre", "pos": [LYST_X - 0.7, LYST_GLASS_Y + 3.2, 4.2], "facing_deg": 180.0, "posture": "standing"},
   {"name": "window_centre", "pos": [LYST_X, LYST_Y - 7.0 + 0.9, 4.2], "facing_deg": 180.0, "posture": "standing"},
   {"name": "door", "pos": [LYST_X - LYST_W / 2 + 1.0, LYST_Y + 6.0, 4.2], "facing_deg": 180.0, "posture": "standing"},
 ],
 "text_planes": [
   # the wordmark on the floor's east wall: a camera on the floor looks +X at it, so world -Y is frame-left;
   # corners clockwise from top-left AS THE CAMERA SEES IT
   {"name": "lyst_wordmark", "text": LYST_WORDMARK_TEXT,
    "corners": [[LYST_X + LYST_W / 2 - 0.17, LYST_Y + 7.0 - 3.7, 6.46], [LYST_X + LYST_W / 2 - 0.17, LYST_Y + 7.0 - 0.7, 6.46],
                [LYST_X + LYST_W / 2 - 0.17, LYST_Y + 7.0 - 0.7, 5.84], [LYST_X + LYST_W / 2 - 0.17, LYST_Y + 7.0 - 3.7, 5.84]]},
   # her nameplate on the glass door: a camera on the floor looks -Y at it, so world +X is frame-left
   {"name": "lyst_nameplate", "text": LYST_NAMEPLATE_TEXT,
    "corners": [[LYST_X - LYST_W / 2 + 0.69 + 0.23, LYST_GLASS_Y - 0.032, 5.755], [LYST_X - LYST_W / 2 + 0.69 - 0.23, LYST_GLASS_Y - 0.032, 5.755],
                [LYST_X - LYST_W / 2 + 0.69 - 0.23, LYST_GLASS_Y - 0.032, 5.685], [LYST_X - LYST_W / 2 + 0.69 + 0.23, LYST_GLASS_Y - 0.032, 5.685]]},
 ],
}
STAGE_MARKS = {
 "marks": [
   {"name": "podium", "pos": [0.0, STAGE_Y + 1.0, ST_H], "facing_deg": 0.0, "posture": "standing"},
   {"name": "beneath_portrait", "pos": [2.0, Y_BACK + 1.5, ST_H], "facing_deg": 0.0, "posture": "standing"},
   {"name": "stage_left_threshold", "pos": [-ST_W / 2 + 1.0, STAGE_Y, ST_H], "facing_deg": 90.0, "posture": "standing"},
   {"name": "upstage_right", "pos": [9.0, Y_BACK + 1.0, ST_H], "facing_deg": 0.0, "posture": "standing"},
 ],
}
CONTROL_POINTS["marks"] = STAGE_MARKS["marks"]
CONTROL_POINTS_BY_ASSET = {"RallyStage": CONTROL_POINTS, "Banner": BANNER_CONTROL, "PengoldOffice": OFFICE_CONTROL,
                           "LysteriaInterior": LYST_CONTROL}


def build_all(only=None):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    for fn in BUILDERS:
        name = fn.__name__[6:]
        if only and name not in only:
            continue
        fn()
