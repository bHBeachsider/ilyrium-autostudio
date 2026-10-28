#!/usr/bin/env python3
r"""assemble_v2.py - build the NH-S901 v2 picture from the shot renders.

SH004, SH005, SH008: v1 renders reused (their keyframes did not change).
SH001: generated black. The v1 "black" was a Wan render of a black keyframe, and Wan invented a title card
       in it - a logo reading roughly X ADIYL BSX with glyphs drifting past (NH-USA-037). A black frame is
       not a shot to render; it is five seconds of nothing, made with lavfi.
SH002, SH003, SH006, SH007, SH009, SH010: v2 renders (living square, 24 m stage, HARNOMY banner).
SH010 + SH011: built here, not rendered. The v2 Wan render of SH010 held for three seconds and then
       drove a car across the foreground and a van THROUGH the stage (NH-USA-031 again, worse). So the
       two dusk holds are one continuous element from the LOCKED dusk plate: an 11 s push of 1.5 %,
       and over the last six seconds the light taken down (a highlight-preserving curve: shadows to
       x0.42, lit windows hold at ~x0.9), then one second of black. A locked-off hold does not need a
       diffusion model, and this one cannot drift.

usage: assemble_v2.py RENDER_DIR OUT.mp4
  RENDER_DIR holds v2/NH-S901-SH0xx.mp4 for the six re-rendered shots; v1 pieces are read from /tmp/cut/p0N.mp4.
"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image

FPS = 16
W, H = 832, 480
V1 = "/tmp/cut"
REUSE = {"SH004": "p04.mp4", "SH005": "p05.mp4", "SH008": "p08.mp4"}
ORDER = ["SH001", "SH002", "SH003", "SH004", "SH005", "SH006", "SH007", "SH008", "SH009", "SH010", "SH011"]
FRAMES = {"SH001": 81, "SH002": 97, "SH003": 97, "SH004": 81, "SH005": 81, "SH006": 81, "SH007": 97,
          "SH008": 81, "SH009": 97, "SH010": 81, "SH011": 97}


def run(*cmd):
    subprocess.run(list(cmd), check=True, capture_output=True)


def last_frame(mp4, png):
    n = int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                            "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", mp4],
                           capture_output=True, text=True).stdout.strip())
    run("ffmpeg", "-y", "-v", "error", "-i", mp4, "-vf", "select=eq(n\\,%d)" % (n - 1), "-vframes", "1", png)


DUSK_PLATE = "/tmp/env/plate_exterior_dusk_v6_HARNOMY.png"   # = plate_exterior_dusk_LOCKED.png
PUSH = 0.015                                                    # total push over SH010+SH011


def dusk_hold(out_mp4, frames, frame_offset, total_frames, ramp=False):
    """Frames [frame_offset, frame_offset+frames) of one continuous 1.5 % push on the dusk plate.
    ramp=True: the light goes over these frames (identity -> SH011 grade, eased)."""
    src = Image.open(DUSK_PLATE).convert("RGB")
    Wp, Hp = src.size
    cw = int(round(Hp * 16 / 9)); cx = (Wp - cw) // 2
    src = src.crop((cx, 0, cx + cw, Hp))                        # exact 16:9 at plate resolution
    Wp, Hp = src.size
    tmp = os.path.splitext(out_mp4)[0] + "_frames"
    os.makedirs(tmp, exist_ok=True)
    for i in range(frames):
        g = (frame_offset + i) / (total_frames - 1)             # 0..1 across both shots
        z = 1.0 + PUSH * g
        w, h = Wp / z, Hp / z
        x0, y0 = (Wp - w) / 2, (Hp - h) / 2
        fr = src.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + w, y0 + h))
        if ramp:
            a = np.asarray(fr).astype(np.float32) / 255.0
            lum = a.mean(-1, keepdims=True)
            k_end = 0.42 + 0.50 * np.clip(lum, 0, 1) ** 1.5
            t = i / (frames - 1); t = t * t * (3 - 2 * t)     # ease: slowly, then faster, then settles
            out = a * (1.0 + t * (k_end - 1.0))
            out[..., 0] *= (1 - 0.04 * t); out[..., 2] *= (1 + 0.04 * t)
            fr = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
        fr.save(os.path.join(tmp, "f%04d.png" % i))
    run("ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "f%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-r", str(FPS), out_mp4)


def normalise(src, dst):
    """Re-encode a render to the common stream shape so concat is a stream copy."""
    run("ffmpeg", "-y", "-v", "error", "-i", src, "-vf", "scale=%d:%d,fps=%d" % (W, H, FPS), "-an",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", dst)


def main():
    rdir, out = sys.argv[1], sys.argv[2]
    work = os.path.join(os.path.dirname(out) or ".", "v2_pieces")
    os.makedirs(work, exist_ok=True)
    pieces = []
    for sid in ORDER:
        dst = os.path.join(work, sid + ".mp4")
        if sid == "SH001":
            run("ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=%dx%d:r=%d" % (W, H, FPS),
                "-frames:v", str(FRAMES["SH001"]), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", dst)
        elif sid in REUSE:
            normalise(os.path.join(V1, REUSE[sid]), dst)
        elif sid == "SH010":
            dusk_hold(dst, FRAMES["SH010"], 0, FRAMES["SH010"] + FRAMES["SH011"])
        elif sid == "SH011":
            dusk_hold(dst, FRAMES["SH011"], FRAMES["SH010"], FRAMES["SH010"] + FRAMES["SH011"], ramp=True)
        else:
            normalise(os.path.join(rdir, "NH-S901-%s.mp4" % sid), dst)
        n = int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                                "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", dst],
                               capture_output=True, text=True).stdout.strip())
        print("%s %d frames (expected %d)" % (sid, n, FRAMES[sid]))
        pieces.append(dst)
    black = os.path.join(work, "black.mp4")
    run("ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=%dx%d:r=%d:d=1" % (W, H, FPS),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", black)
    pieces.append(black)
    lst = os.path.join(work, "list.txt")
    with open(lst, "w") as f:
        for p in pieces:
            f.write("file '%s'\n" % os.path.abspath(p))
    run("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out],
                         capture_output=True, text=True).stdout.strip()
    print("wrote", out, dur, "s")


if __name__ == "__main__":
    main()
