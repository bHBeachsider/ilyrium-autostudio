"""backlot.world.nh.cameras - one camera per shot, as data. No bpy.

Each entry: location, look-at target, focal length (mm on a 36 mm sensor), resolution. The rotation is derived
(camera looks down -Z with +Y up, the convention Blender and USD share). Shot cameras obey the set rule from
NH-USA-047: exteriors look square at the facade. Survey cameras exist to look at the world, not to shoot it.
"""
from .geometry import R_COL, R_WALL, STAGE_Y, Y_BACK, UNI_Y, NORTH_Y

Y0 = R_COL

SHOT_CAMERAS = {
    "PLATE": dict(loc=(0.0, Y0 + 66.0, 9.0), target=(0.0, 0.0, 12.0), lens=22.0, res=(1584, 672)),
    "SH002": dict(loc=(0.0, Y0 + 66.0, 9.0), target=(0.0, 0.0, 12.0), lens=26.0, res=(1920, 1080)),
    "SH003": dict(loc=(-9.0, STAGE_Y + 13.0, 1.6), target=(-9.0, Y_BACK - 6.0, 6.5), lens=26.0, res=(1920, 1080)),
    "SH006": dict(loc=(0.0, R_WALL - 0.2, 7.2), target=(0.0, STAGE_Y - 4.0, 0.0), lens=20.0, res=(1920, 1080)),
    "SH007": dict(loc=(0.0, STAGE_Y + 18.0, 1.7), target=(0.0, Y_BACK - 10.0, 7.0), lens=28.0, res=(1920, 1080)),
    "SH009": dict(loc=(-5.0, STAGE_Y + 26.0, 1.7), target=(-5.0, STAGE_Y - 14.0, 4.0), lens=32.0, res=(1920, 1080)),
    "SH010": dict(loc=(0.0, Y0 + 66.0, 9.0), target=(0.0, 0.0, 12.0), lens=26.0, res=(1920, 1080)),
}

SURVEY_CAMERAS = {
    "PLAN": dict(loc=(0.0, 95.0, 260.0), target=(0.0, 95.0, 0.0), lens=40.0, res=(1920, 1080)),
    "AERIAL": dict(loc=(-120.0, -60.0, 90.0), target=(0.0, 70.0, 8.0), lens=35.0, res=(1920, 1080)),
    "AXIS_UP": dict(loc=(0.0, 30.0, 2.0), target=(0.0, UNI_Y + 40.0, 8.0), lens=40.0, res=(1920, 1080)),
    "AXIS_DOWN": dict(loc=(0.0, UNI_Y - 6.0, 2.0), target=(0.0, 0.0, 14.0), lens=40.0, res=(1920, 1080)),
    "BODEGA": dict(loc=(16.0, 58.0, 1.7), target=(10.0, NORTH_Y, 4.0), lens=30.0, res=(1920, 1080)),
    "CHURCH_E": dict(loc=(14.0, 62.0, 2.0), target=(50.0, 24.0, 20.0), lens=30.0, res=(1920, 1080)),
}

# which set state each shot camera shoots in (the build ladder, NH-USA-045)
SHOT_STATES = {"PLATE": "finished", "SH002": "joists", "SH003": "joists", "SH006": "half_decked",
               "SH007": "beam_seated", "SH009": "finished", "SH010": "finished"}


def rotation_deg(loc, target):
    """Blender-convention XYZ euler, degrees, for a camera at loc looking at target (-Z forward, +Y up)."""
    from mathutils import Vector
    q = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y")
    e = q.to_euler("XYZ")
    import math
    return [math.degrees(e.x), math.degrees(e.y), math.degrees(e.z)]
