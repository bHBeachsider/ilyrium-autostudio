#!/usr/bin/env python3
r"""NH-S901 sound design layers via fal-ai/elevenlabs/sound-effects/v2.

The teaser is wordless and unscored; these layers ARE the soundtrack. Each is generated
once from the brief in NH-S901_scaffold_sfx_brief.md, then placed and mixed with ffmpeg
in mix_NH-S901.py. No music. No voices with intelligible words.
"""
import os
import sys
import urllib.request

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "NH-S901_sfx")

for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env",
            r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

# name, text, seconds, loop
LAYERS = [
 ("hammer_single",  "a single carpenter's hammer striking a nail into pine timber, three unhurried strikes about two seconds apart, outdoors in a large cold stone city square with long natural reverb, no other sound", 10, False),
 ("hammer_work",    "steady unhurried carpentry hammering on timber, two hammers at slightly different rhythms, outdoors in a large cold stone city square with natural reverb", 20, True),
 ("nailgun",        "a pneumatic nail gun firing in short bursts of three, outdoors, echoing off stone buildings, with the compressor hissing between bursts", 12, False),
 ("chop_saw",       "a chop saw spinning up with a rising whine, cutting through a pine board with a rasp, then stopping abruptly, outdoors with stone reverb", 8, False),
 ("circular_saw",   "a circular saw cutting a long pine board outdoors, a steady rasping cut lasting several seconds, distant stone echo", 10, False),
 ("timber_drop",    "heavy pine timber boards dropped onto a stack of timber on granite paving, a flat resonant slap and clatter, outdoors with reverb", 6, False),
 ("drill",          "a cordless drill driving a long screw into timber then winding down, outdoors", 5, False),
 ("workmen_far",    "several men's voices calling to each other from far across a large stone square, the words completely unintelligible, one short laugh, outdoors, distant and reverberant", 14, True),
 ("wind_winter",    "cold steady winter wind moving across an open stone city square, low and continuous, occasional gusts, no voices", 22, True),
 ("halyard",        "a metal flag halyard clip ticking irregularly against a hollow metal flagpole in the wind, outdoors, close", 16, True),
 ("city_ambience",  "quiet distant city traffic ambience in a mid-sized downtown on a winter morning, slow cars, a far-off bus air brake, no horns, no voices", 22, True),
 ("interior_room",  "the interior of a large quiet high-ceilinged office room, close room tone, an old cast-iron radiator ticking as it heats, faint muffled construction sounds through closed glass windows", 12, True),
 ("boots_decking",  "work boots stepping on fresh pine decking boards, a few slow steps, then a hand brush sweeping sawdust off wood, outdoors", 7, False),
 ("bus_brake_far",  "a distant city bus air brake release and the bus pulling away slowly, far off across a square", 5, False),
 # v3 (2026-09-05): the banner insert
 # v9 (Brad, 2026-09-05): "there are sounds of hammering in scene without any hammering. maybe insert random worker
 # conversations or laughing." Work sound now only where the action is on screen; elsewhere the square carries voices.
 ("workmen_chat",   "two or three workmen talking to each other while they work outdoors in a large stone city square, ordinary unhurried conversation, the words completely unintelligible, no shouting, distant and reverberant, no music", 22, True),
 ("workmen_laugh",  "a short easy laugh from two men working outdoors across a large stone square, one says a few unintelligible words after it, distant and reverberant", 8, False),
 ("workmen_call",   "one workman calling a short instruction to another across a large stone square outdoors, unintelligible, the other answers briefly, distant and reverberant", 7, False),
 # v8 (Brad, 2026-09-05): the build day is a drizzle under a flat grey sky
 ("drizzle_square", "light steady drizzle falling on wet granite paving and stone in a large open city square, fine rain hiss, occasional drips from a stone ledge, distant wet-road tyre hiss, no thunder, no voices", 22, True),
 ("drizzle_timber", "light rain pattering close on fresh pine boards and a tarpaulin, drips, outdoors, close perspective", 12, True),
 ("banner_flap",    "a large heavy fabric banner stirring and softly flapping in a light steady winter wind, the canvas breathing and creaking against its ropes, outdoors, close, no voices", 10, True),
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
    print("[OK] fal auth OK", flush=True)


def main():
    preflight()
    import fal_client
    os.makedirs(OUT, exist_ok=True)
    for name, text, secs, loop in LAYERS:
        dst = os.path.join(OUT, name + ".mp3")
        if os.path.exists(dst):
            print("[SKIP] %s exists" % name, flush=True); continue
        print("-- %s (%ds%s)" % (name, secs, ", loop" if loop else ""), flush=True)
        try:
            args = {"text": text, "duration_seconds": secs, "prompt_influence": 0.5,
                    "output_format": "mp3_44100_128"}
            if loop:
                args["loop"] = True
            res = fal_client.subscribe("fal-ai/elevenlabs/sound-effects/v2", arguments=args)
            url = (res.get("audio") or {}).get("url")
            if not url:
                print("   [FAIL] no audio: %s" % str(res)[:200], flush=True); continue
            urllib.request.urlretrieve(url, dst)
            print("   [OK] %s (%d KB)" % (name, os.path.getsize(dst) // 1024), flush=True)
        except Exception as exc:
            print("   [FAIL] %s: %s" % (name, exc), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
