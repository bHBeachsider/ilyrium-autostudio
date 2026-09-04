#!/usr/bin/env python3
r"""NH-S901 'The Scaffold' - keyframes, one per shot spec.  v2 (populated square, long stage, banner).

METHOD, AND WHY NOT THE LoRA
----------------------------
Every keyframe is a reference-conditioned edit on fal nano-banana-pro, using the LOCKED
plates from 03_design/environments/city_hall/ as the environment reference, so the
building, the square, the banner and the office are provably the same object in every
frame - the same technique that held the facade across the dusk relight.

The one shot with a face (SH005) composes Pengold's locked anchor INTO the locked office
plate as a second reference. For a single still, multi-reference composition holds
identity better than the LoRA does (NH-USA-009); the LoRA's job is video and scale, and
it is named in the spec for the i2v stage.

SH001 is a black frame and is generated locally. SH002 and SH010 are the LOCKED exterior
plates themselves; SH011 is SH010 with the last light taken down in pixels. A plate that
IS the shot is not regenerated.

v2 (2026-09-04, after Brad's notes on the v1 cut): the square is a living downtown - parked
cars, a lumber flatbed, a bus, pedestrians at distance with their backs to us, nobody
looking at the build - the dais is a ~24 m rally stage with a rear truss, and the mauve
banner (NEW HARNOMY ... spelled wrong, on purpose - NH-USA-033) hangs from the portico in
every shot that sees the building. Reference roles are assigned explicitly in each prompt
because the reference outvotes the prompt (NH-USA-016/025): the plate that holds the
camera is named first, the plate that holds the stage shape second, and a plate that
already contains a finished element is never used when that element must be absent.

Cost: four generations, ~$0.60.
"""
import os
import sys
import urllib.request

import httpx
from dotenv import load_dotenv
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ENV = os.path.join(PROJ, "03_design", "environments", "city_hall")
ANCHOR = os.path.join(PROJ, "03_design", "characters", "casting", "finals", "PEN-FINAL.png")

for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env",
            r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

LOOK = ("prestige political drama, House of Cards season one color grade, Roger Deakins single-source "
        "lighting, anamorphic cinematography, Arri Alexa, slight 35mm film grain, color palette "
        "desaturated twelve percent, warm tungstens lifted, deep browns and charcoals in shadows, faint "
        "cool blue holding only in the deepest blacks, photographic realism, cinematic")

EXT_FIRST = os.path.join(ENV, "plate_exterior_firstlight_LOCKED.png")   # before the build; banner up; living square
EXT_DUSK = os.path.join(ENV, "plate_exterior_dusk_LOCKED.png")          # finished 24 m stage + truss; banner up
OFFICE = os.path.join(ENV, "plate_office_A_LOCKED.png")
POV = os.path.join(ENV, "plate_pov_square_v1.png")                      # camera + columns only (its small dais is superseded)
SH003_V1 = os.path.join(PROJ, "..", "..", "ilyrium-shots", "keyframes", "NH-S901-SH003_key.png")  # v1 take: right building, right action, empty square

COPY = {  # shot -> plate that IS the keyframe (cropped 16:9 locally)
    "NH-S901-SH002": EXT_FIRST,
    "NH-S901-SH010": EXT_DUSK,
}

LIFE = ("The square is a normal mid-sized American downtown on a weekday morning in November: cars parked "
        "nose to tail along the kerbs, a flatbed truck stacked with fresh pine lumber, a white box van with "
        "its rear doors open, a city bus at the far corner, a few pedestrians in winter coats crossing the "
        "granite paving at a distance with their backs or profiles to the camera, a dog-walker, a courier on "
        "a bicycle, bins and a bike rack. No pedestrian is close, none faces the camera, none is looking at "
        "the timber structure. Traffic is parked or stopped. ")

BANNER = ("A long fabric banner in a dull brownish mauve hangs from the portico's entablature between the "
          "columns, exactly the banner in the reference, its pale lettering unchanged. ")

NO_WINK = "No rope, no noose, no cable, no bunting, no flags on the timber. "

STAGE_HALF = ("The structure under construction is a LONG low timber rally stage about twenty-four metres "
              "wide and just over a metre high, standing on the building's axis about forty metres in front "
              "of the portico with its back to the building: a platform frame of open pine joists, decking "
              "boards laid across about half of it, stacks of fresh lumber alongside, and along its rear "
              "edge three tall square pine uprights standing vertical and braced with temporary diagonal "
              "props, WITH NO CROSSBEAM ON TOP - the tops of the uprights are bare and separate against the "
              "sky. ")

STAGE_TRUSS = ("The structure is a LONG low timber rally stage about twenty-four metres wide and just over "
               "a metre high, fully decked, standing on the building's axis about forty metres in front of "
               "the portico with its back to the building; along its rear edge a timber truss of three tall "
               "square pine uprights carrying one long horizontal crossbeam at about the height of the "
               "ground-floor arches behind. ")

JOBS = [
 # v3 (2026-09-04). v2 takes are kept in _v2_takes/ for the record:
 #  SH003 v2 re-imagined the building (giant-order colonnade, carved CITY HALL) once the camera moved -
 #    so the v1 take, which had the right building and the right action, is now the camera reference;
 #  SH006 v2 ran the stage AWAY from the camera with the uprights at the far end - the contract (SET_BIBLE
 #    section 4) has it parallel to the facade with the truss nearest the building, i.e. nearest Pengold;
 #  SH007 v2 seated the beam mid-post on four uprights; the finished truss (dusk plate) is two tall
 #    uprights at the stage ends with the beam across their tops at first-floor-window height.
 ("NH-S901-SH003", "16:9", [SH003_V1, EXT_FIRST],
  "Use the FIRST reference for everything about the camera, the building and the action: the same low angle "
  "looking up at the corner of the semicircular colonnade, the same two workmen in high-visibility vests "
  "raising the tall pine upright with their breath steaming, the same low winter sun. Keep that building "
  "exactly - two storeys, round arches on the ground floor, the colonnade above, no carved lettering "
  "anywhere on the stone. Change only these things, taking them from the SECOND reference: " + BANNER +
  "The low platform frame of open pine joists at the workmen's feet runs out of frame to the left and to the "
  "right. Behind the workmen, along the kerb in front of the building, " + LIFE + NO_WINK +
  "No faces toward the camera. " + LOOK),

 ("NH-S901-SH006", "16:9", [POV, EXT_FIRST],
  "Use the FIRST reference for the camera and the room edge only: the same point of view from inside the "
  "Mayor's office looking down through the French window, the same two giant limestone columns close on "
  "either side rising out of frame, the same stone balustrade, the same faint reflection on the glass, the "
  "same far side of the square with the steeple and low blocks. IGNORE the small wooden platform in the first "
  "reference; it does not exist. Use the SECOND reference for what the square contains. In the square below, "
  "seen from above and behind, build ONLY THIS: a LONG low timber rally stage under construction, about "
  "twenty-four metres wide and just over a metre high, running LEFT TO RIGHT across the view, parallel to "
  "the building's facade, so wide that it spans nearly the whole gap between the two columns; its long "
  "near edge is toward the camera. It is a platform frame of open pine joists with decking boards laid "
  "across about half of it, stacks of fresh lumber alongside. Along its NEAR edge - the edge closest to the "
  "camera and the building - stand two tall square pine uprights, one near each end of the stage, vertical "
  "and braced with temporary diagonal props, WITH NO CROSSBEAM - their tops are bare and separate. Six "
  "workmen in high-visibility vests move around it, small, seen from above, no faces. Beyond the stage " +
  LIFE + "Flat winter daylight, thin high cloud. " + NO_WINK + LOOK),

 ("NH-S901-SH007", "16:9", [EXT_FIRST, EXT_DUSK],
  "Use the FIRST reference for the building, the banner, the square, its parked cars and its daylight. Use "
  "the SECOND reference for the exact shape and size of the timber stage and its truss; ignore its dusk "
  "lighting entirely - this is midday, flat bright winter light. Camera at head height on the granite "
  "paving in front of the stage, a medium-wide shot. The stage is the long low decked platform from the "
  "second reference, running out of frame on both sides. Its truss is two tall square pine uprights, one "
  "at each end of the stage behind it, each about seven metres tall with a diagonal brace, and the long "
  "pine crossbeam is at this moment being lowered onto their tops by a small mobile hoist whose cable comes "
  "in from above: the beam hangs level a hand's breadth above the two post tops. Two workmen in "
  "high-visibility vests stand on the decked platform below it, backs to the camera, each steadying one "
  "end of the beam with a tag rope, faces turned up to the beam. Behind and above, the semicircular "
  "colonnade of City Hall, " + BANNER + LIFE + NO_WINK + LOOK),
 ("NH-S901-SH009", "16:9", [EXT_FIRST, EXT_DUSK],   # v2 take accepted 2026-09-04
  "Use the FIRST reference for the building, the banner, the square, its parked cars and its daylight. Use "
  "the SECOND reference ONLY for the shape and size of the finished timber stage: a long low decked platform "
  "with a row of folding chairs set along it and a podium at centre, a rear truss with its crossbeam seated. "
  "Ignore the second reference's dusk lighting entirely - this is mid-afternoon, low bright winter sun, "
  "long shadows. Camera at head height on the paving near the LEFT end of the stage, a medium shot: a short "
  "flight of four raw pine steps has just been set against the end of the platform, and a workman in a "
  "high-visibility vest, seen in profile, puts his weight on the first tread to test it, one hand on the "
  "platform edge. The platform and its row of chairs run away from the camera to the right, out of frame. "
  "Behind, part of the colonnade of City Hall and the mauve banner. " + LIFE + NO_WINK +
  "No faces toward the camera. " + LOOK),
]


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
    only = set(sys.argv[1:])
    preflight()
    import fal_client
    cache = {}
    for sid, ar, refs, prompt in JOBS:
        if only and sid not in only:
            continue
        print("-- %s" % sid, flush=True)
        try:
            urls = []
            for rp in refs:
                if rp not in cache:
                    cache[rp] = fal_client.upload_file(rp)
                urls.append(cache[rp])
            res = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={
                "prompt": prompt, "image_urls": urls, "aspect_ratio": ar,
                "resolution": "2K", "output_format": "png", "num_images": 1})
            imgs = res.get("images") or []
            if not imgs:
                print("   [FAIL] no image: %s" % str(res)[:200], flush=True); continue
            dst = os.path.join(HERE, sid + "_key.png")
            urllib.request.urlretrieve(imgs[0]["url"], dst)
            print("   [OK] %s (%d KB)" % (os.path.basename(dst), os.path.getsize(dst) // 1024), flush=True)
        except Exception as exc:
            print("   [FAIL] %s: %s" % (sid, exc), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
