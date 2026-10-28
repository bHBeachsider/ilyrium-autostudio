"""backlot.world.nh.cameras - one camera per shot, as data. No bpy.

Each entry: location, look-at target, focal length (mm on a 36 mm sensor), resolution. The rotation is derived
(camera looks down -Z with +Y up, the convention Blender and USD share). Shot cameras obey the set rule from
NH-USA-047: exteriors look square at the facade. Survey cameras exist to look at the world, not to shoot it.
"""
from .geometry import R_COL, R_WALL, STAGE_Y, Y_BACK, UNI_Y, NORTH_Y, OFFICE_FLOOR, PILF_X, PILF_Y, LYST_X, LYST_Y, LYST_W, LYST_D, LYST_GLASS_Y, BOARD_Z0, BODEGA_X

Y0 = R_COL

SHOT_CAMERAS = {
    "PLATE": dict(loc=(0.0, Y0 + 66.0, 9.0), target=(0.0, 0.0, 12.0), lens=22.0, res=(1584, 672)),
    "SH002": dict(loc=(0.0, Y0 + 66.0, 9.0), target=(0.0, 0.0, 12.0), lens=26.0, res=(1920, 1080)),
    "SH003": dict(loc=(-9.0, STAGE_Y + 13.0, 1.6), target=(-9.0, Y_BACK - 6.0, 6.5), lens=26.0, res=(1920, 1080)),
    "SH006": dict(loc=(0.0, R_WALL - 0.2, 7.2), target=(0.0, STAGE_Y - 4.0, 0.0), lens=20.0, res=(1920, 1080)),
    "SH007": dict(loc=(0.0, STAGE_Y + 18.0, 1.7), target=(0.0, Y_BACK - 10.0, 7.0), lens=28.0, res=(1920, 1080)),
    "SH009": dict(loc=(-5.0, STAGE_Y + 26.0, 1.7), target=(-5.0, STAGE_Y - 14.0, 4.0), lens=32.0, res=(1920, 1080)),
    "SH010": dict(loc=(0.0, Y0 + 66.0, 9.0), target=(0.0, 0.0, 12.0), lens=26.0, res=(1920, 1080)),
    # NH-S101 - Pengold's office at dawn (interior; the POV contract with SH006: same room, same windows)
    "S101_SH004": dict(loc=(-6.0, -5.2, OFFICE_FLOOR + 1.7), target=(0.8, 3.5, OFFICE_FLOOR + 1.3), lens=24.0, res=(2520, 1080)),   # wide: desk, the man, the three windows and the columns beyond
    "S101_SH005": dict(loc=(-0.8, 2.0, OFFICE_FLOOR + 1.45), target=(0.0, -3.0, OFFICE_FLOOR + 1.25), lens=55.0, res=(1920, 1080)),  # medium, the 22 s
    "S101_SH006": dict(loc=(0.9, -0.2, OFFICE_FLOOR + 1.2), target=(0.0, -2.0, OFFICE_FLOOR + 0.76), lens=85.0, res=(1920, 1080)),   # hands / desk edge
    "S101_SH007": dict(loc=(0.0, 0.2, OFFICE_FLOOR + 1.4), target=(0.0, -3.0, OFFICE_FLOOR + 1.4), lens=85.0, res=(1920, 1080)),     # close-up, past the lens
    # LYSTERIA (no number yet; shot cameras so the passes renderer and the gate can measure the glass-walled interior)
    # THE VIEW OF THE SCAFFOLD: from her desk end, out through the band, the rally stage going up in front of City Hall
    "LYST_WINDOW": dict(loc=(LYST_X + 0.6, LYST_Y - LYST_D / 2 + 1.3, 4.2 + 1.55), target=(0.0, STAGE_Y, 3.0), lens=40.0, res=(2520, 1080)),
    # the boardroom (top floor): across the table and out through its band at the same view, higher
    "LYST_BOARD": dict(loc=(LYST_X - 0.3, LYST_Y + LYST_D / 2 - 1.6, BOARD_Z0 + 1.55), target=(LYST_X + 0.2, LYST_Y - LYST_D / 2, BOARD_Z0 + 1.3), lens=24.0, res=(2520, 1080)),
    "LYST_BOARD_VIEW": dict(loc=(LYST_X - 0.2, LYST_Y - LYST_D / 2 + 1.6, BOARD_Z0 + 1.6), target=(-2.0, STAGE_Y - 2.0, 3.0), lens=35.0, res=(2520, 1080)),
    # the visitor's view (2.39:1): from the floor, through the glass, to Summer against the band
    "LYST_DESK": dict(loc=(LYST_X + 1.7, LYST_GLASS_Y + 3.6, 4.2 + 1.5), target=(LYST_X + 1.2, LYST_Y - LYST_D / 2 + 1.9, 4.2 + 1.15), lens=32.0, res=(2520, 1080)),
}

SURVEY_CAMERAS = {
    "PLAN": dict(loc=(0.0, 95.0, 260.0), target=(0.0, 95.0, 0.0), lens=40.0, res=(1920, 1080)),
    "AERIAL": dict(loc=(-120.0, -60.0, 90.0), target=(0.0, 70.0, 8.0), lens=35.0, res=(1920, 1080)),
    "AXIS_UP": dict(loc=(0.0, 30.0, 2.0), target=(0.0, UNI_Y + 40.0, 8.0), lens=40.0, res=(1920, 1080)),
    "AXIS_DOWN": dict(loc=(0.0, UNI_Y - 6.0, 2.0), target=(0.0, 0.0, 14.0), lens=40.0, res=(1920, 1080)),
    "BODEGA": dict(loc=(BODEGA_X + 6.0, 58.0, 1.7), target=(BODEGA_X, NORTH_Y, 4.0), lens=30.0, res=(1920, 1080)),
    "CHURCH_E": dict(loc=(14.0, 62.0, 2.0), target=(50.0, 24.0, 20.0), lens=30.0, res=(1920, 1080)),
    # PILF storefront interior (build_PILFInterior): from the back-wall corner looking out through the shopfront glass,
    # and from the glass looking back at the wall board and the three folding tables
    "PILF_IN": dict(loc=(PILF_X - 5.6, PILF_Y - 4.6, 1.6), target=(PILF_X + 6.0, PILF_Y + 1.0, 1.3), lens=20.0, res=(1920, 1080)),
    "PILF_IN_BACK": dict(loc=(PILF_X + 5.8, PILF_Y + 4.6, 1.6), target=(PILF_X - 6.0, PILF_Y - 1.0, 1.3), lens=20.0, res=(1920, 1080)),
    # LYSTERIA (build_LysteriaInterior, upper floor z0 = 4.2). The floor is the north half (door end), Summer's office is
    # the south half behind the glass wall, backed by the glazed band onto the square.
    "LYST_IN": dict(loc=(LYST_X - LYST_W / 2 + 0.9, LYST_Y + LYST_D / 2 - 0.9, 4.2 + 1.6), target=(LYST_X + 1.0, LYST_Y - LYST_D / 2 + 1.5, 4.2 + 1.2), lens=20.0, res=(1920, 1080)),
    "LYST_IN_BACK": dict(loc=(LYST_X - 3.6, LYST_Y - LYST_D / 2 + 0.6, 4.2 + 1.6), target=(LYST_X + 1.5, LYST_Y + LYST_D / 2 - 1.0, 4.2 + 1.3), lens=20.0, res=(1920, 1080)),
    # arriving: in at the door, the reception desk and the wordmark on the wall behind it
    "LYST_RECEPTION": dict(loc=(LYST_X - LYST_W / 2 + 1.2, LYST_Y + LYST_D / 2 - 1.1, 4.2 + 1.6), target=(LYST_X + LYST_W / 2, LYST_Y + LYST_D / 2 - 2.2, 4.2 + 1.7), lens=24.0, res=(1920, 1080)),
    # her POV: from the desk, out through the glass over the floor - she sees everyone
    "LYST_POV": dict(loc=(LYST_X + 1.2, LYST_Y - LYST_D / 2 + 1.4, 4.2 + 1.25), target=(LYST_X - 0.7, LYST_Y + LYST_D / 2 - 2.0, 4.2 + 1.3), lens=28.0, res=(1920, 1080)),
}

# which set state each shot camera shoots in (the build ladder, NH-USA-045)
SHOT_STATES = {"PLATE": "finished", "SH002": "joists", "SH003": "joists", "SH006": "half_decked",
               "SH007": "beam_seated", "SH009": "finished", "SH010": "finished",
               "S101_SH004": "finished", "S101_SH005": "finished", "S101_SH006": "finished", "S101_SH007": "finished",
               "LYST_DESK": "half_decked", "LYST_WINDOW": "joists", "LYST_BOARD": "half_decked", "LYST_BOARD_VIEW": "joists"}
# depth normalisation per shot: LINEAR for exteriors (the 93% first-take result was measured with it; inverse depth
# compresses the far uprights out of SH006 - 2/5 under inverse vs 5/5 under linear, 2026-09-08), INVERSE for
# interiors (a fixed linear range leaves a room near-white)
DEPTH_MODE = {"S101_SH004": "inverse", "S101_SH005": "inverse", "S101_SH006": "inverse", "S101_SH007": "inverse",
              "LYST_DESK": "inverse", "LYST_BOARD": "inverse"}      # the two window views look 60 m out: linear, like the exteriors
# shots inside a room. The gate's RallyStage geometry check (posts on their columns, the deck line) does not apply
# to an interior even when the stage is visible through a window at 60 m - it would look for two 3-pixel uprights and
# fail every office key (recorded 2026-09-08 for S101, scoped 2026-09-09). The comparative clay check still runs.
INTERIOR_SHOTS = {"S101_SH004", "S101_SH005", "S101_SH006", "S101_SH007", "LYST_DESK", "LYST_WINDOW", "LYST_BOARD", "LYST_BOARD_VIEW"}
# every other state family a shot selects (build is SHOT_STATES); absent = the family's default
SHOT_VARIANTS = {
    "SH003": {"people": "build"}, "SH006": {"office": "dawn", "people": "none"}, "SH007": {"people": "build"},
    "S101_SH004": {"office": "dawn", "people": "office_dawn"}, "S101_SH005": {"office": "dawn", "people": "office_dawn"},
    "S101_SH006": {"office": "dawn", "people": "office_dawn"}, "S101_SH007": {"office": "dawn", "people": "office_dawn"},
    "LYST_DESK": {"lysteria": "working", "people": "lysteria"}, "LYST_WINDOW": {"lysteria": "working", "people": "none"},
    "LYST_BOARD": {"people": "boardroom"}, "LYST_BOARD_VIEW": {"people": "none"},
}


def rotation_deg(loc, target):
    """Blender-convention XYZ euler, degrees, for a camera at loc looking at target (-Z forward, +Y up)."""
    from mathutils import Vector
    q = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y")
    e = q.to_euler("XYZ")
    import math
    return [math.degrees(e.x), math.degrees(e.y), math.degrees(e.z)]
