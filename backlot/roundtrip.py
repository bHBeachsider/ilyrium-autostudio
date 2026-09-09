#!/usr/bin/env python3
r"""roundtrip.py - the hand-edit loop, run INSIDE Blender (its Python has bpy and the bundled USD `pxr`).

    blender -b --python backlot\roundtrip.py -- open   [--build finished]      USD stage -> usd\nh\nh_backlot.blend
    (open nh_backlot.blend in Blender, move asset ROOT Empties - RallyStage, PengoldOffice, Bodega... - save)
    blender -b --python backlot\roundtrip.py -- readback                      .blend -> overrides\readback.usda,
                                                                              then compose + derive + clay of --shots
Nothing else is needed: no venv, no pip. The asset is the unit of edit - moving a mesh inside an asset is not read
back (promote it to its own asset in world/nh/geometry.py if it must move on its own).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)


def main():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    cmd = a[0] if a else "open"
    rest = a[1:]
    if cmd == "open":
        from backlot import open_in_blender
        sys.argv = ["open_in_blender.py", "--"] + rest
        open_in_blender.main()
    elif cmd == "readback":
        from backlot import readback
        blend = rest[0] if rest and not rest[0].startswith("--") else os.path.join(HERE, "usd", "nh", "nh_backlot.blend")
        sys.argv = ["readback.py", "--", blend]
        readback.main()
        from backlot.usd import compose, derive
        sys.argv = ["compose.py"]; compose.main()
        sys.argv = ["derive.py"]; derive.main()
        shots = rest[rest.index("--shots") + 1:] if "--shots" in rest else []
        if shots:
            from backlot.usd import render_clay
            sys.argv = ["render_clay.py"] + shots; render_clay.main()
    else:
        sys.exit("usage: roundtrip.py -- open [--build STATE] | readback [BLEND] [--shots SH009 ...]")


if __name__ == "__main__":
    main()
