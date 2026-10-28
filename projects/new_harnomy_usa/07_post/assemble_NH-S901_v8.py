#!/usr/bin/env python3
r"""assemble_v3.py - NH-S901 'The Scaffold' v3: Veo 3.1 shots at 1080p/24, trailer shape, timeline JSON.

Picture:
  SH001   5.0 s  black, with the ILYRIUM STUDIOS card fading through it under the first hammer strikes
  SH002   6.0 s  Veo  wide, first light
  SH012   4.0 s  Veo  the banner insert (plays second) (new, 2026-09-05) - the one place the audience can read the misspelling
  SH003   6.0 s  Veo  uprights
  SH004   5.0 s  Veo  chop saw           (6 s render trimmed)
  SH005   5.0 s  Veo  Pengold's window   (trimmed)
  SH006   5.0 s  Veo  his POV            (trimmed)
  SH007   6.0 s  Veo  the crossbeam
  SH008   5.0 s  Veo  decking            (trimmed)
  SH009   6.0 s  Veo  the steps
  SH010   5.0 s  Veo  dusk, the object alone          } one continuous element: the 8 s Veo hold, then its last
  SH011   6.0 s  the last light goes, cut on stillness } frame held; the light taken down over the final 6 s
  black   1.0 s  silence
  TITLE   5.5 s  NEW HARNOMY, U.S.A. / AN OPERA
  STUDIO  2.5 s  ILYRIUM STUDIOS
  black   1.0 s

Writes OUT.mp4 (video only) and OUT.timeline.json {shot: [start, duration]} for the mix.
usage: assemble_v3.py VEO_DIR OUT.mp4 [--font-dir DIR]
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FPS = 24
W, H = 1920, 1080
FONT_DIR = "/tmp/fonts/package/files"
PALE = (222, 211, 214)          # the banner's pale lettering, slightly warm
MAUVE = (104, 72, 84)           # Framework mauve: aged university-press paperback

PLAN = [  # (id, seconds, source)
    ("SH001", 5.0, "black+card"),
    ("SH002", 6.0, "veo"), ("SH012", 4.0, "veo"), ("SH003", 6.0, "veo"), ("SH004", 5.0, "veo"),
    ("SH005", 5.0, "veo"), ("SH006", 5.0, "veo"), ("SH007", 6.0, "veo"), ("SH008", 5.0, "veo"),
    ("SH009", 6.0, "veo"), ("SH010", 5.0, "dusk"), ("SH011", 6.0, "dusk"),
    ("BLACK1", 1.0, "black"), ("TITLE", 5.5, "title"), ("STUDIO", 2.5, "studio"), ("BLACK2", 1.0, "black"),
]


def run(*cmd):
    subprocess.run(list(cmd), check=True, capture_output=True)


def nframes(path):
    return int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                               "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", path],
                              capture_output=True, text=True).stdout.strip())


def encode_frames(pattern, out):
    run("ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", pattern, "-c:v", "libx264",
        "-pix_fmt", "yuv420p", "-crf", "15", "-r", str(FPS), out)


def normalise(src, dst, seconds):
    """Trim a Veo clip to `seconds`, conform to 1920x1080/24, strip audio."""
    run("ffmpeg", "-y", "-v", "error", "-i", src, "-t", "%.3f" % seconds, "-an",
        "-vf", "scale=%d:%d:flags=lanczos,fps=%d,setsar=1" % (W, H, FPS),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "15", dst)


def black(dst, seconds):
    run("ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=%dx%d:r=%d" % (W, H, FPS),
        "-frames:v", str(int(round(seconds * FPS))), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "15", dst)


# ---------------------------------------------------------------- cards
def font(weight, px):
    return ImageFont.truetype(os.path.join(FONT_DIR, "oswald-latin-%d-normal.woff" % weight), px)


def draw_tracked(draw, xy_center, text, fnt, fill, tracking):
    """Letter-spaced text centred on xy_center. tracking in px added after every glyph."""
    widths = [draw.textlength(ch, font=fnt) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = xy_center[0] - total / 2.0
    bbox = fnt.getbbox("H")
    y = xy_center[1] - (bbox[1] + bbox[3]) / 2.0
    for ch, wch in zip(text, widths):
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += wch + tracking


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def fade_env(t, fin_a, fin_b, fout_a, fout_b):
    """0->1 between fin_a..fin_b, 1->0 between fout_a..fout_b."""
    if t < fin_a:
        return 0.0
    if t < fin_b:
        return ease((t - fin_a) / (fin_b - fin_a))
    if t < fout_a:
        return 1.0
    if t < fout_b:
        return 1.0 - ease((t - fout_a) / (fout_b - fout_a))
    return 0.0


def render_card(dst, seconds, layers):
    """layers: list of dicts {text, weight, px, tracking, y, color, fade:(fin_a,fin_b,fout_a,fout_b), rule:bool}"""
    n = int(round(seconds * FPS))
    tmp = os.path.splitext(dst)[0] + "_frames"
    os.makedirs(tmp, exist_ok=True)
    fonts = {(l["weight"], l["px"]): font(l["weight"], l["px"]) for l in layers}
    for i in range(n):
        t = i / FPS
        im = Image.new("RGB", (W, H), (0, 0, 0))
        d = ImageDraw.Draw(im)
        for l in layers:
            a = fade_env(t, *l["fade"])
            if a <= 0:
                continue
            col = tuple(int(round(c * a)) for c in l["color"])
            fnt = fonts[(l["weight"], l["px"])]
            draw_tracked(d, (W / 2, l["y"]), l["text"], fnt, col, l["tracking"])
            if l.get("rule"):
                widths = sum(d.textlength(ch, font=fnt) for ch in l["text"]) + l["tracking"] * (len(l["text"]) - 1)
                rc = tuple(int(round(c * a)) for c in MAUVE)
                y = l["y"] + l["px"] * 0.62
                d.rectangle([W / 2 - widths / 2, y, W / 2 + widths / 2, y + 3], fill=rc)
        im.save(os.path.join(tmp, "f%04d.png" % i))
    encode_frames(os.path.join(tmp, "f%04d.png"), dst)


def card_studio(dst, seconds, fin_a, fin_b, fout_a, fout_b):
    render_card(dst, seconds, [dict(text="ILYRIUM STUDIOS", weight=300, px=54, tracking=14, y=H / 2, color=PALE,
                                    fade=(fin_a, fin_b, fout_a, fout_b))])


def card_title(dst, seconds):
    render_card(dst, seconds, [
        dict(text="NEW HARNOMY, U.S.A.", weight=500, px=170, tracking=10, y=H / 2 - 40, color=PALE,
             fade=(0.3, 1.5, seconds - 0.9, seconds - 0.1), rule=True),
        dict(text="AN OPERA", weight=300, px=52, tracking=16, y=H / 2 + 150, color=PALE,
             fade=(1.9, 2.7, seconds - 0.9, seconds - 0.1)),
    ])


# ---------------------------------------------------------------- the dusk element
def dusk_element(veo_sh010, dst10, dst11, s10, s11):
    """SH010 = first s10 seconds of the Veo hold. SH011 = the rest of the hold, then its last frame held, the light
    taken down over all of SH011 (identity -> shadows x0.42, lit windows ~x0.9), settling to a still."""
    tmp = os.path.splitext(dst11)[0] + "_frames"
    os.makedirs(tmp, exist_ok=True)
    # decode the whole hold to frames at 1080p/24
    src_frames = os.path.join(tmp, "src")
    os.makedirs(src_frames, exist_ok=True)
    run("ffmpeg", "-y", "-v", "error", "-i", veo_sh010, "-vf", "scale=%d:%d:flags=lanczos,fps=%d" % (W, H, FPS),
        os.path.join(src_frames, "s%04d.png"))
    src = sorted(os.listdir(src_frames))
    n10 = int(round(s10 * FPS)); n11 = int(round(s11 * FPS))
    # SH010: straight copy of the first n10 frames
    normalise(veo_sh010, dst10, s10)
    last = None
    for i in range(n11):
        j = n10 + i
        p = os.path.join(src_frames, src[min(j, len(src) - 1)])
        fr = Image.open(p).convert("RGB")
        a = np.asarray(fr).astype(np.float32) / 255.0
        lum = a.mean(-1, keepdims=True)
        k_end = 0.42 + 0.50 * np.clip(lum, 0, 1) ** 1.5
        t = ease(i / (n11 - 1))
        out = a * (1.0 + t * (k_end - 1.0))
        out[..., 0] *= (1 - 0.04 * t); out[..., 2] *= (1 + 0.04 * t)
        Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(os.path.join(tmp, "f%04d.png" % i))
    encode_frames(os.path.join(tmp, "f%04d.png"), dst11)


def main():
    args = sys.argv[1:]
    global FONT_DIR
    if "--font-dir" in args:
        i = args.index("--font-dir"); FONT_DIR = args[i + 1]; del args[i:i + 2]
    veo, out = args[0], args[1]
    work = os.path.join(os.path.dirname(out) or ".", "v8_pieces")
    os.makedirs(work, exist_ok=True)
    pieces, timeline, t = [], {}, 0.0
    for sid, secs, kind in PLAN:
        dst = os.path.join(work, sid + ".mp4")
        if kind == "veo":
            normalise(os.path.join(veo, "NH-S901-%s.mp4" % sid), dst, secs)
        elif kind == "still":
            key = os.environ["KEY_" + sid]
            run("ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", key, "-t", "%.3f" % secs, "-r", str(FPS),
                "-vf", "scale=%d:%d:flags=lanczos,setsar=1" % (W, H), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "15", dst)
        elif kind == "slowhead":
            run("ffmpeg", "-y", "-v", "error", "-t", "1.6", "-i", os.path.join(veo, "NH-S901-%s.mp4" % sid), "-an",
                "-vf", "setpts=PTS/0.4,minterpolate=fps=%d:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none,scale=%d:%d:flags=lanczos,setsar=1" % (FPS, W, H),
                "-t", "%.3f" % secs, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "15", dst)
        elif kind == "black+card":
            card_studio(dst, secs, 0.9, 1.7, 3.5, 4.3)
        elif kind == "black":
            black(dst, secs)
        elif kind == "title":
            card_title(dst, secs)
        elif kind == "studio":
            card_studio(dst, secs, 0.2, 0.8, secs - 0.8, secs - 0.2)
        elif kind == "dusk":
            if sid == "SH010":
                s11 = [p for p in PLAN if p[0] == "SH011"][0][1]
                dusk_element(os.path.join(veo, "NH-S901-SH010.mp4"), dst, os.path.join(work, "SH011.mp4"), secs, s11)
            # SH011 was written with SH010
        n = nframes(dst)
        print("%-7s %5.2fs %4d frames (want %d)" % (sid, secs, n, int(round(secs * FPS))))
        timeline[sid] = [round(t, 4), secs]
        t += secs
        pieces.append(dst)
    lst = os.path.join(work, "list.txt")
    with open(lst, "w") as f:
        for p in pieces:
            f.write("file '%s'\n" % os.path.abspath(p))
    run("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out)
    timeline["END"] = [round(t, 4), 0.0]
    json.dump(timeline, open(os.path.splitext(out)[0] + ".timeline.json", "w"), indent=1)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out],
                         capture_output=True, text=True).stdout.strip()
    print("wrote", out, dur, "s;", "timeline ->", os.path.splitext(out)[0] + ".timeline.json")


if __name__ == "__main__":
    main()
