"""End-to-end smoke test for ONE shot in ONE style: character sheets -> keyframe
-> Wan i2v clip. Validates the full chain before the full bake-off. Not a unit test."""
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_AUTOSTUDIO = os.path.dirname(os.path.dirname(_HERE))
if _AUTOSTUDIO not in sys.path:
    sys.path.insert(0, _AUTOSTUDIO)
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(_AUTOSTUDIO)), ".env"), override=True)

from films.woods_of_west import script, characters, keyframes
from media.comfyui_renderer import render_i2v_comfyui

STYLE = "cartoon"
OUT = os.path.join(_AUTOSTUDIO, "outputs", "woods_of_west", "_smoke")

t0 = time.time()
print(f"[smoke] building character sheets ({STYLE})...", flush=True)
refs = characters.build_character_sheets(STYLE, os.path.join(OUT, "characters"))
print(f"[smoke] sheets: {refs} ({time.time()-t0:.0f}s)", flush=True)

shot = [s for s in script.SHOTS if s["id"] == 13][0]
print(f"[smoke] keyframe for shot {shot['id']}...", flush=True)
kf = keyframes.generate_shot_keyframe(shot, STYLE, refs, os.path.join(OUT, "keyframes"))
print(f"[smoke] keyframe: {kf} ({time.time()-t0:.0f}s)", flush=True)

print(f"[smoke] Wan i2v (this loads the model first time, can take minutes)...", flush=True)
clip = render_i2v_comfyui(kf, shot["motion"], 13, output_dir=os.path.join(OUT, "clips"),
                          output_name="smoke13.mp4")
print(f"[smoke] CLIP: {clip}", flush=True)
print(f"[smoke] exists={os.path.exists(clip)} size={os.path.getsize(clip) if os.path.exists(clip) else 0} bytes "
      f"total={time.time()-t0:.0f}s", flush=True)
print("[smoke] DONE", flush=True)
