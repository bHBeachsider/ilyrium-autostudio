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

usage: fal_veo_render.py [--only SH002 SH007 ...] [--fast] [--dry-run] [--force] [--seed-bump K]
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

LOOK = ("Prestige political drama photographed on an Arri Alexa with anamorphic lenses: flat overcast daylight, "
        "slight 35mm film grain, colours desaturated about twelve percent, warm tungstens, deep browns and "
        "charcoals in the shadows, photographic realism.")
STATIC = ("The camera is locked off on a tripod and does not move at all: no pan, no tilt, no zoom, no drift, no "
          "handheld shake. Real-time speed, natural human movement, never slow motion.")
WEATHER = ("A heavy flat overcast, sheet-cake grey sky, no sun and no shadows; a light steady drizzle falls, fine rain "
           "visible against the dark stone, the granite paving wet with shallow puddles mirroring the grey sky; street lamps "
           "and windows glow warm and are doubled in the wet. ")
TRAFFIC = ("On the far street beyond the square and along the side kerbs a few cars move slowly and steadily with their "
           "headlights and tail-lights on, reflected in the wet road, at an unhurried city pace - no car ever enters the "
           "square or comes near the stage. ")
NEG = ("turning around, walking away, camera pull back, dolly, reframing, people walking into frame, pedestrians in the foreground, moving bus, moving vehicles, slow motion, speed ramp, time-lapse, camera movement, zoom, pan, dolly, handheld shake, on-screen text, "
       "captions, subtitles, watermark, logo, tripod, light stand, camera equipment, lens flare, fast traffic, cars driving through the frame, people looking "
       "at the camera, faces toward camera, cartoon, illustration, oversaturated")

# shot -> (duration, prompt). Durations are Veo's 4/6/8 s; the cut trims to the storyboard's length.
SHOTS = {
 "SH002": ("6s",
  "Wide establishing shot of the square outside New Harnomy City Hall on a grey drizzling November morning. "
  + WEATHER + STATIC + " The only movement is small and human: a handful of pedestrians in winter coats walk slowly across "
  "the granite paving at a distance with their backs to the camera, a dog-walker crosses, a cyclist rolls slowly "
  "past under an umbrella, steam rises from the hot-food cart. The granite paving in front of the building's entrance steps stays open and empty throughout - nothing is built or stacked on it. The parked cars along the kerbs stay parked; the flatbed lumber truck "
  "and the white box van stand still with their engines off; the bus at the far corner pulls away slowly. " + TRAFFIC +
  "The damp mauve banner on the portico hangs heavy and barely stirs. " + LOOK),
 "SH012": ("4s",   # the banner insert; plays second
  "Medium shot with a long lens of a mauve fabric banner hanging between the limestone columns of a semicircular "
  "portico, filling the frame width, in flat grey overcast light with a fine drizzle falling. " + STATIC + " The only movement: "
  "the fabric, heavy with rain, hangs almost perfectly still - at most a barely visible breath along its lower edge - "
  "while drops gather and run off its bottom hem; no fold ever lifts, no part of the banner curls or turns over, every "
  "word stays fully visible, perfectly legible and undistorted for the whole shot. "
  "Nothing else moves; the stone is fixed. No people. " + LOOK),
 "SH003": ("6s",
  "Locked-off eye-height shot from the wet paving a few metres back from the stage, looking straight at City Hall; the "
  "open pine joists of the platform frame make a band across the bottom quarter of the frame and the building fills the rest. Two workmen in high-visibility vests and knit caps steadily raise a tall square pine "
  "upright on the far edge of the frame from a lean to full vertical, hand over hand, their breath steaming in the cold; a third man holds a "
  "diagonal brace steady, rain beading on their wet vests. " + WEATHER + STATIC + " Behind them the semicircular colonnade of City Hall with its mauve banner "
  "stays perfectly fixed; the parked cars, the lumber flatbed and the box van do not move; two distant pedestrians "
  "walk slowly away from the camera under umbrellas. " + TRAFFIC + "Effortful, deliberate, real-time movement, faces turned toward the post, "
  "never toward the camera. " + LOOK),
 "SH004": ("6s",
  "Extreme close-up insert. A chop saw blade spins up to full speed and is pushed down through a length of fresh "
  "pine; damp sawdust sprays and falls quickly in the flat grey light, fine drizzle drops on the steel and the wet timber; "
  "the gloved hands hold the timber steady, then lift the blade clear. " + STATIC + " Overcast, no sun. Shallow depth of field, "
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
  "rally stage under construction far out in the square below, thirty metres from the building, with empty wet granite "
  "paving between the balustrade and the stage. " + WEATHER + STATIC + " Six workmen in high-visibility vests move "
  "at a normal working pace around the platform, two carrying a decking board together to the open joists on the right, one kneeling to fix "
  "a board at the boundary; the two tall bare uprights stand still. Beyond the stage the square goes about its morning: parked cars do not "
  "move, the lumber truck and open box van stand still, a bus is stopped at the far corner, a few pedestrians walk "
  "slowly at a distance with their backs to us, a cyclist rolls by. Nobody walks across the empty paving below the "
  "balustrade. " + TRAFFIC + LOOK),
 "SH007": ("6s",
  "Medium-wide shot from the paving in front of a long decked timber stage. A long pine crossbeam hanging level "
  "from two hoist cables descends the last hand's breadth and settles onto the tops of the two tall pine uprights "
  "at the ends of the stage; the cables go slack. Two workmen on the platform, backs to the camera, steady it with "
  "tag ropes and look up as it seats, then lower their arms and stand still, rain on their vests. " + WEATHER + STATIC + " Behind and above them "
  "the semicircular colonnade of City Hall and its mauve banner do not move; parked cars stay parked; the lumber "
  "flatbed and box van stand at the kerb; one distant pedestrian walks slowly away under an umbrella. " + TRAFFIC +
  "Unhurried real-time motion, and after the beam seats, stillness. " + LOOK),
 "SH008": ("6s",
  "Close insert on new pine decking, camera low at board level, fixed. Work boots stand on the fresh boards; a "
  "gloved hand with a stiff hand brush sweeps sawdust off the square edge of the platform toward the camera in two "
  "slow strokes, the damp dust dropping in clumps onto the wet setts, drizzle beading on the boards; the boots shift their weight once and "
  "stay. " + STATIC + " The framing at the end of the shot is identical to the framing at the start. Shallow depth "
  "of field on the boards and the boots. " + LOOK),
 "SH009": ("6s",
  "Head-height medium shot from the wet paving in front of the left end of a long finished timber stage, looking "
  "straight at City Hall; the stage runs horizontally across the frame. A workman in a high-visibility vest and white "
  "hard hat, seen in profile, puts his weight on the first tread of a short flight of new pine steps at the front of "
  "the platform, bounces once to test it, nods to himself, steps down and walks out of frame to the RIGHT at an ordinary pace across the open paving. The stage ENDS at the tall pine upright: nothing of the structure is ever visible to the right of that upright, only wet granite. The single row of folding chairs stays a single row. "
  + STATIC + " The row of folding chairs and the podium on the platform stay perfectly still; behind them City Hall "
  "with its mauve banner; parked cars do not move; the lumber truck and box van stand at the kerb; steam from a "
  "hot-food cart; a bus stopped at the far corner. The stage, its steps and the podium remain in the frame in exactly "
  "the same place from the first frame to the last; the camera never pans to follow the workman - he simply leaves the "
  "frame. " + WEATHER + TRAFFIC + LOOK),
 "SH010": ("8s",
  "Wide shot at dusk, a completely empty square. The finished long timber rally stage with its row of folding chairs, "
  "a podium and a tall rear truss stands alone in front of City Hall, whose windows are lit warm tungsten; the mauve "
  "banner hangs damp on the portico. " + WEATHER.replace("grey sky", "grey sky at dusk") + STATIC + " There are NO PEOPLE "
  "anywhere in this shot: every car in the square stays parked and dark, the bus at the far corner is parked with its "
  "engine off, no one walks into or through the frame. On the far street beyond the square only, a car or two passes "
  "slowly with headlights on, reflected in the wet road. The only other change over eight seconds is the grey light "
  "failing slowly toward night, rain ringing the puddles and a very faint stir of the wet banner fabric. A locked-off, "
  "silent, unpeopled hold on an object. Grey-blue drizzling dusk, stillness. " + LOOK),
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
    bump = int(args[args.index("--seed-bump") + 1]) if "--seed-bump" in args else 0   # retake with a new seed
    only = None
    if "--only" in args:
        i = args.index("--only")
        only = set()
        for a in args[i + 1:]:
            if a.startswith("--"):
                break
            only.add(a)
    endpoint = "fal-ai/veo3.1/fast/image-to-video" if fast else "fal-ai/veo3.1/image-to-video"
    rate = 0.10 if fast else 0.20
    os.makedirs(OUT, exist_ok=True)
    if not dry:
        preflight()
        import fal_client
    total = 0.0
    order = [a for a in args[args.index("--only") + 1:] if a in only] if only else list(SHOTS)
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
