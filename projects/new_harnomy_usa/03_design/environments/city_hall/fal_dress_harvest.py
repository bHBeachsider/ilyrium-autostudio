#!/usr/bin/env python3
r"""fal_dress_harvest.py - dress the LOCKED exteriors and the banner keyframes with Thanksgiving iconography.

Brad, 2026-09-05: "needs thanksgiving related iconography - sheaves, pumpkins, not sure whatever else so audience
knows this is thanksgiving." The holiday is now ERSATZGIVING; the audience has to read it as Thanksgiving
repurposed, so the square wears the real holiday's furniture: corn-stalk sheaves tied to the lampposts and the
portico columns, pumpkins and gourds massed at the column bases and along the stage front and steps, hay bales,
garlands of autumn leaves and Indian corn along the balustrade. Municipal-issue, tasteful, a bit much.

Order of operations matters: dress FIRST with the model, then re-letter the banner in pixels with
set_banner_text.py - the model will not be trusted with the text (NH-USA-033).

usage: fal_dress_harvest.py JOB [JOB ...]      jobs: plate_first plate_dusk SH003 SH007 SH009 SH012
"""
import os
import sys
import urllib.request

import httpx
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
KEYS = os.path.join(PROJ, "04_preproduction", "keyframes", "NH-S901")
OUT = os.path.join(HERE, "_harvest")

for env in (r"C:/Users/bradu/Documents/ilyrium-autostudio/.env", r"C:/Users/bradu/Documents/slm-foundry/.env"):
    load_dotenv(env, override=False)

DRESS = ("Add Thanksgiving harvest decorations to this exact image and change NOTHING else - same camera, same "
         "building, same light, same people, same vehicles, same timber stage and truss, same banner in the same place "
         "with the same lettering. The decorations: tall bundles of dried corn stalks (sheaves) tied with twine to the "
         "base of every portico column and to the lampposts; clusters of orange pumpkins, white pumpkins and knobbly "
         "gourds heaped at the column bases and along the front edge of the timber stage and beside its steps; a few "
         "square hay bales; garlands of dried autumn leaves and ears of Indian corn swagged along the stone balustrade "
         "of the portico. Municipal, tasteful, slightly too much of it. Photographic realism, matching grain and colour.")
KEEP_TEXT = " Keep the banner's existing text exactly as it is; do not redraw or reword it."

PLATE_FIRST = os.path.join(HERE, "plate_exterior_firstlight_LOCKED.png")
PLATE_DUSK = os.path.join(HERE, "plate_exterior_dusk_LOCKED.png")

JOBS = {
 "plate_first": ("21:9", [PLATE_FIRST], DRESS + KEEP_TEXT),
 "plate_dusk":  ("21:9", [PLATE_DUSK], DRESS + " At dusk the pumpkins catch the warm light from the windows. CRITICAL: the "
                "tall raw-timber truss behind the stage - the two square pine uprights at the ends of the stage and the long "
                "crossbeam across their tops - must remain EXACTLY as it is, unchanged, undecorated and fully visible; you may "
                "lean one corn-stalk sheaf against the FOOT of each upright but never hide, remove or replace the uprights or the "
                "beam. Garlands go on the stone balustrade only, never across the truss." + KEEP_TEXT),
 "SH003": ("16:9", [os.path.join(KEYS, "NH-S901-SH003_key.png"), os.path.join(OUT, "plate_first.png")],
           "Use the FIRST image as the shot - change nothing about its camera, people, timber, vehicles or banner. "
           "Add to it the same Thanksgiving harvest decorations that the SECOND image shows on the same building: "
           "corn-stalk sheaves tied to the column bases and lampposts, pumpkins and gourds heaped at the column bases, "
           "garlands of autumn leaves and Indian corn along the balustrade. Photographic realism." + KEEP_TEXT),
 "SH007": ("16:9", [os.path.join(KEYS, "NH-S901-SH007_key.png"), os.path.join(OUT, "plate_first.png")],
           "Use the FIRST image as the shot - change nothing about its camera, people, timber, vehicles or banner. "
           "Add to it the same Thanksgiving harvest decorations the SECOND image shows on the same building, and along "
           "the front edge of the timber stage in the foreground a row of pumpkins, gourds and small hay bales, with "
           "corn-stalk sheaves tied to the two tall uprights. Photographic realism." + KEEP_TEXT),
 "SH009": ("16:9", [os.path.join(KEYS, "NH-S901-SH009_key.png"), os.path.join(OUT, "plate_first.png")],
           "Use the FIRST image as the shot - change nothing about its camera, the workman, the stage, the chairs, "
           "the podium, the vehicles or the banner. Add to it the same Thanksgiving harvest decorations the SECOND "
           "image shows on the building, and pumpkins, gourds and a hay bale beside the timber steps and along the "
           "front edge of the stage, with corn-stalk sheaves tied to the truss uprights. Photographic realism." + KEEP_TEXT),
 "SH012": ("16:9", [os.path.join(KEYS, "NH-S901-SH012_key.png")],
           "Change nothing about this image except: tie tall bundles of dried corn stalks with twine to the base of "
           "each limestone column flanking the banner, heap a few orange and white pumpkins and gourds at those bases "
           "on the ledge, and swag a garland of dried autumn leaves and Indian corn along the balustrade just under the "
           "banner. The banner, its fabric and its lettering stay exactly as they are. Photographic realism." + KEEP_TEXT),
 # the insert, re-lettered by the model from the LOCKED plate at a scale where it copies letterforms (NH-USA-040)
 "SH012_letter": ("16:9", [os.path.join(OUT, "SH012.png"), PLATE_FIRST],
           "Use the FIRST image for everything: camera, columns, corn sheaves, pumpkins, garlands, fabric, light. Change "
           "ONLY the lettering on the mauve banner so that it reads, in the same pale condensed capitals, two centred "
           "lines - line one, larger: WELCOME TO NEW HARNOMY'S ANNUAL ERSATZGIVING HOLIDAY GATHERING!  line two, "
           "smaller: A FESTIVAL OF CONTRITION, ATONEMENT AND REPENTANCE  - exactly as the banner in the SECOND image is "
           "lettered; copy that spelling letter for letter, including the invented words HARNOMY and ERSATZGIVING. "
           "Nothing else changes. Photographic realism."),
 # v5 (Brad, 2026-09-05): the truss must stay SOLID from the beam-seating (SH007) through the finish (SH009, SH010) -
 # SH009 had drifted to a lattice/box truss - and once finished it is covered with seasonal decorations.
 "SH009_truss": ("16:9", [os.path.join(KEYS, "NH-S901-SH009_key.png")],
           "Keep this exact image - same camera, same workman testing the steps, same stage, chairs, podium, pumpkins, hay, "
           "vehicles, building and banner. Change ONLY the tall timber truss behind the stage: rebuild it as two tall square "
           "SOLID pine posts with one long SOLID pine beam laid flat across their tops and a short diagonal brace at each "
           "corner - plain sawn timber, NO lattice, NO open-web or box-truss members, NO cross-hatching, NO steel. Then "
           "dress that solid truss for the holiday: a thick garland of dried autumn leaves, ears of Indian corn and small "
           "gourds wound along the whole length of the beam and spiralling down both posts, a corn-stalk sheaf tied at the "
           "foot of each post. The timber stays visible under the garland. Photographic realism." + KEEP_TEXT),
 "plate_dusk_truss": ("21:9", [PLATE_DUSK],
           "Change ONLY the tall timber truss behind the stage in this image: keep it exactly where it is and exactly as built "
           "- two tall square solid pine posts and one long solid beam across their tops with a short brace at each corner - "
           "and dress it for the holiday: a thick garland of dried autumn leaves, ears of Indian corn and small gourds wound "
           "along the whole length of the beam and spiralling down both posts, catching the warm light from the windows. The "
           "timber stays visible under the garland; the silhouette of posts and beam against the dusk sky stays clear. Nothing "
           "else changes. Photographic realism." + KEEP_TEXT),
}


def preflight():
    key = os.getenv("FAL_KEY")
    if not key:
        sys.exit("[FAIL] FAL_KEY not set.")
    r = httpx.post("https://rest.fal.ai/storage/auth/token?storage_type=fal-cdn-v3",
                   headers={"Authorization": "Key " + key}, timeout=30)
    if r.status_code == 403 and "balance" in r.text.lower():
        sys.exit("[FAIL] fal balance exhausted.")
    print("[OK] fal auth OK (probe %s)" % r.status_code, flush=True)


def main():
    preflight()
    import fal_client
    os.makedirs(OUT, exist_ok=True)
    cache = {}
    for job in sys.argv[1:]:
        ar, refs, prompt = JOBS[job]
        print("-- %s" % job, flush=True)
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
            dst = os.path.join(OUT, job + ".png")
            urllib.request.urlretrieve(imgs[0]["url"], dst)
            print("   [OK] %s (%d KB)" % (os.path.basename(dst), os.path.getsize(dst) // 1024), flush=True)
        except Exception as exc:
            print("   [FAIL] %s: %s" % (job, exc), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
