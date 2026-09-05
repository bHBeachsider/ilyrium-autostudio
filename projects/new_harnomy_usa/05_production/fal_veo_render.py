#!/usr/bin/env python3
r"""fal_veo_render.py - render NH-S901 shots on Veo 3.1 (fal-ai/veo3.1/image-to-video) from the LOCKED keyframes.

WHY THIS EXISTS
---------------
Brad, 2026-09-05, on the v2 cut: "the quality is not excellent. The movements are unnaturally slow. can we use veo
3.1 or another model to produce film grade quality." Wan 2.2 on the box renders 16 fps and its 4-step distillation
reads as slow motion; Veo 3.1 renders 24 fps at 1080p with natural motion and holds the keyframe's text, faces and
geometry. The keyframes do not change - identity, set and banner are still won at the still.

This is a standalone renderer, outside batch_render's ledger: the pipeline has no fal renderer yet (finding
NH-USA-038). Every request and response is written beside the mp4 as a JSON sidecar so the render is reproducible
and can be back-filled into the provenance ledger when the FalRenderer lands.

usage: fal_veo_render.py [--only SH002 SH007 ...] [--fast] [--dry-run] [--force]
  --fast   fal-ai/veo3.1/fast/image-to-video ($0.10/s, exploration) instead of standard ($0.20/s, finals)
Cost at 1080p without audio: standard $0.20/s -> 8 x 6 s + 1 x 8 s + the 4 s banner insert = $12.00 per full pass.
"""
import json
import os
import sys
import time
import urllib.request

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, ".."))
KEYS = os.path.join(PROJ, "04_preproduction", "keyframes", "NH-S901")
OUT = os.path.join(HERE, "renders", "NH-S901", "veo")

for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env",
            r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

LOOK = ("Prestige political drama photographed on an Arri Alexa with anamorphic lenses: single-source natural "
        "light, slight 35mm film grain, colours desaturated about twelve percent, warm tungstens, deep browns and "
        "charcoals in the shadows, photographic realism.")
STATIC = ("The camera is locked off on a tripod and does not move at all: no pan, no tilt, no zoom, no drift, no "
          "handheld shake. Real-time speed, natural human movement, never slow motion.")
NEG = ("turning around, walking away, camera pull back, dolly, reframing, people walking into frame, pedestrians in the foreground, moving bus, moving vehicles, slow motion, speed ramp, time-lapse, camera movement, zoom, pan, dolly, handheld shake, on-screen text, "
       "captions, subtitles, watermark, logo, lens flare, fast traffic, cars driving through the frame, people looking "
       "at the camera, faces toward camera, cartoon, illustration, oversaturated")

# shot -> (duration, prompt). Durations are Veo's 4/6/8 s; the cut trims to the storyboard's length.
SHOTS = {
 "SH002": ("6s",
  "Wide establishing shot of the square outside New Harnomy City Hall at first light on a cold November morning. "
  + STATIC + " The only movement is small and human: a handful of pedestrians in winter coats walk slowly across "
  "the granite paving at a distance with their backs to the camera, a dog-walker crosses, a cyclist rolls slowly "
  "past, steam rises from the hot-food cart. Every car stays parked exactly where it is; the flatbed lumber truck "
  "and the white box van stand still with their engines off; the bus at the far corner is stopped. The mauve banner "
  "on the portico stirs very slightly in a light wind. Long low winter sun, long shadows, frost on the paving. " + LOOK),
 "SH012": ("4s",   # the banner insert; plays second
  "Medium shot with a long lens of a mauve fabric banner hanging between the limestone columns of a semicircular "
  "portico, filling the frame width, lit by low raking winter sun from the left. " + STATIC + " The only movement: "
  "the fabric breathes very slightly in a light wind - a slow soft ripple travelling along it, the fold near the "
  "middle lifting and settling, the lettering staying perfectly legible and undistorted throughout. Nothing else "
  "moves; the stone is fixed. No people. " + LOOK),
 "SH003": ("6s",
  "Low angle from the paving. Two workmen in high-visibility vests and knit caps steadily raise a tall square pine "
  "upright from a lean to full vertical, hand over hand, their breath steaming in the cold; a third man holds a "
  "diagonal brace steady. " + STATIC + " Behind them the semicircular colonnade of City Hall with its mauve banner "
  "stays perfectly fixed; the parked cars, the lumber flatbed and the box van do not move; two distant pedestrians "
  "walk slowly away from the camera. Effortful, deliberate, real-time movement, faces turned toward the post, "
  "never toward the camera. Low winter sun. " + LOOK),
 "SH004": ("6s",
  "Extreme close-up insert. A chop saw blade spins up to full speed and is pushed down through a length of fresh "
  "pine; sawdust sprays and hangs glittering in the low winter sun, drifting slowly through the light after the "
  "cut; the gloved hands hold the timber steady, then lift the blade clear. " + STATIC + " Shallow depth of field, "
  "sharp focus on the blade and the cut. " + LOOK),
 "SH005": ("6s",
  "Interior, a mayor's ornate office. A man in an immaculate dark navy suit stands at the tall French window with "
  "his back three-quarters to the camera, looking down into the square below. He stays exactly where he is for the "
  "whole shot, feet planted, facing the window: he does not turn, does not look back, does not walk, does not "
  "raise his hands. The only movement in the frame is the slow rise and fall of his breathing and, once, the "
  "fingers of his right hand closing and opening at his side. " + STATIC + " Tungsten desk lamp warm in the "
  "foreground, flat winter daylight through the glass, the giant limestone columns just outside the window fixed. "
  "A portrait of a man watching. " + LOOK),
 "SH006": ("6s",
  "Point of view from the Mayor's office window, looking down between two giant limestone columns at a long timber "
  "rally stage under construction in the square below. " + STATIC + " Six workmen in high-visibility vests move "
  "at a normal working pace around the platform, two carrying a board together, one kneeling to fix decking; the "
  "two tall braced uprights stand still. Beyond the stage the square goes about its morning: parked cars do not "
  "move, the lumber truck and open box van stand still, a bus is stopped at the far corner, a few pedestrians walk "
  "slowly at a distance with their backs to us, a cyclist rolls by. Flat winter daylight, a faint reflection of "
  "the room on the glass. " + LOOK),
 "SH007": ("6s",
  "Medium-wide shot from the paving in front of a long decked timber stage. A long pine crossbeam hanging level "
  "from two hoist cables descends the last hand's breadth and settles onto the tops of the two tall pine uprights "
  "at the ends of the stage; the cables go slack. Two workmen on the platform, backs to the camera, steady it with "
  "tag ropes and look up as it seats, then lower their arms and stand still. " + STATIC + " Behind and above them "
  "the semicircular colonnade of City Hall and its mauve banner do not move; parked cars stay parked; the lumber "
  "flatbed and box van stand at the kerb; one distant pedestrian walks slowly away. Flat bright winter light, "
  "unhurried real-time motion, and after the beam seats, stillness. " + LOOK),
 "SH008": ("6s",
  "Close insert on new pine decking, camera low at board level, fixed. Work boots stand on the fresh boards; a "
  "gloved hand with a stiff hand brush sweeps sawdust off the square edge of the platform toward the camera in two "
  "slow strokes, the dust falling and catching the low raking winter sun; the boots shift their weight once and "
  "stay. " + STATIC + " The framing at the end of the shot is identical to the framing at the start. Shallow depth "
  "of field on the boards and the boots. " + LOOK),
 "SH009": ("6s",
  "Medium shot beside the left end of a long finished timber stage. A workman in a high-visibility vest, seen in "
  "profile, puts his weight on the first tread of a short flight of new pine steps set against the platform, "
  "bounces once to test it, nods to himself, steps down and walks out of frame to the left at an ordinary pace. "
  + STATIC + " The row of folding chairs and the podium on the platform stay perfectly still; behind them City Hall "
  "with its mauve banner; parked cars do not move; the lumber truck and box van stand at the kerb; steam from a "
  "hot-food cart; a bus stopped at the far corner. Low afternoon winter sun, long shadows. " + LOOK),
 "SH010": ("8s",
  "Wide shot at dusk, a completely empty square. The finished long timber rally stage with its row of folding chairs, "
  "a podium and a tall rear truss stands alone in front of City Hall, whose windows are lit warm tungsten; the mauve "
  "banner hangs on the portico. " + STATIC + " There are NO PEOPLE anywhere in this shot and nothing drives: every car "
  "stays parked and dark, the bus at the far corner is parked with its engine off and does not move, no one walks "
  "into or through the frame. The only change over eight seconds is the sky deepening slowly from blue toward night "
  "and a very faint stir of the banner fabric. A locked-off, silent, unpeopled hold on an object. Deep blue winter "
  "twilight, absolute stillness. " + LOOK),
}


def preflight():
    key = os.getenv("FAL_KEY")
    if not key:
        sys.exit("[FAIL] FAL_KEY not set.")
    r = httpx.post("https://rest.fal.ai/storage/auth/token?storage_type=fal-cdn-v3",
                   headers={"Authorization": "Key " + key}, timeout=30)
    if r.status_code == 403 and "balance" in r.text.lower():
        sys.exit("[FAIL] fal balance exhausted.")
    if r.status_code in (401, 403):
        sys.exit("[FAIL] fal auth rejected (%s)" % r.status_code)
    print("[OK] fal auth OK (probe %s)" % r.status_code, flush=True)


def main():
    args = sys.argv[1:]
    fast = "--fast" in args
    dry = "--dry-run" in args
    force = "--force" in args
    only = None
    if "--only" in args:
        i = args.index("--only")
        only = set(a for a in args[i + 1:] if not a.startswith("--"))
    endpoint = "fal-ai/veo3.1/fast/image-to-video" if fast else "fal-ai/veo3.1/image-to-video"
    rate = 0.10 if fast else 0.20
    os.makedirs(OUT, exist_ok=True)
    if not dry:
        preflight()
        import fal_client
    total = 0.0
    order = [a for a in args[args.index("--only") + 1:] if not a.startswith("--")] if only else list(SHOTS)
    for sid in order:
        dur, prompt = SHOTS[sid]
        dst = os.path.join(OUT, "NH-S901-%s.mp4" % sid)
        side = dst[:-4] + ".json"
        if os.path.exists(dst) and not force:
            print("[SKIP] %s exists" % sid, flush=True); continue
        key = os.path.join(KEYS, "NH-S901-%s_key.png" % sid)
        secs = int(dur[:-1]); total += secs * rate
        arguments = {"prompt": prompt, "aspect_ratio": "16:9", "duration": dur, "resolution": "1080p",
                     "generate_audio": False, "negative_prompt": NEG, "seed": 901000 + int("".join(ch for ch in sid if ch.isdigit())) }
        print("-- %s  %s  %s  (~$%.2f)" % (sid, endpoint, dur, secs * rate), flush=True)
        if dry:
            continue
        t0 = time.time()
        try:
            image_url = fal_client.upload_file(key)
            res = fal_client.subscribe(endpoint, arguments=dict(arguments, image_url=image_url))
            url = (res.get("video") or {}).get("url")
            if not url:
                print("   [FAIL] no video: %s" % str(res)[:300], flush=True); continue
            urllib.request.urlretrieve(url, dst)
            rec = {"shot_id": "NH-S901-" + sid, "endpoint": endpoint, "keyframe": os.path.relpath(key, PROJ),
                   "arguments": arguments, "image_url": image_url, "response": res,
                   "seconds": round(time.time() - t0, 1), "est_cost_usd": secs * rate,
                   "rendered_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            json.dump(rec, open(side, "w", encoding="utf-8"), indent=2)
            print("   [OK] %s (%d KB, %.0fs)" % (os.path.basename(dst), os.path.getsize(dst) // 1024, time.time() - t0), flush=True)
        except Exception as exc:
            print("   [FAIL] %s: %s" % (sid, exc), flush=True)
    print("DONE  est. spend this run: $%.2f" % total, flush=True)


if __name__ == "__main__":
    main()
