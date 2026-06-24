"""Phase 2: render the full ~2-min film in BOTH chosen styles (cartoon, cinematic),
back-to-back, in one process. Reuses the approved bake-off character sheets."""
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_AS = os.path.dirname(os.path.dirname(_HERE))
if _AS not in sys.path:
    sys.path.insert(0, _AS)

from films.woods_of_west.render_film import run_film  # loads .env on import

ROOT = os.path.join(_AS, "outputs", "woods_of_west")
STYLES = ["cartoon", "cinematic", "ballpoint"]

for style in STYLES:
    t = time.time()
    print(f"\n######### FULL FILM: {style} #########", flush=True)
    try:
        master = run_film(style, ROOT)
        print(f"[{style}] MASTER: {master} ({time.time()-t:.0f}s)", flush=True)
    except Exception as e:
        print(f"[{style}] FAILED: {type(e).__name__}: {e}", flush=True)
print("\nALL DONE", flush=True)
