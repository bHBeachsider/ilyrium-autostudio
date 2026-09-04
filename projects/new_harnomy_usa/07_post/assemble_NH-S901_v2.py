#!/usr/bin/env python3
r"""assemble_v2.py - build the NH-S901 v2 picture from the shot renders.

SH001 black, SH004, SH005, SH008: v1 renders reused (their keyframes did not change).
SH002, SH003, SH006, SH007, SH009, SH010: v2 renders (living square, 24 m stage, HARNOMY banner).
SH011: built here, not rendered - the last frame of SH010 with the light taken down over 6 s
       (a highlight-preserving curve: shadows to x0.42, lit windows hold at ~x0.9), perfectly still,
       then one second of black. NH-USA-031 option (b): a locked-off hold does not need a diffusion model.

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
REUSE = {"SH001": "p01.mp4", "SH004": "p04.mp4", "SH005": "p05.mp4", "SH008": "p08.mp4"}
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


def light_ramp(src_png, out_mp4, frames):
    """The last light goes: interpolate the shadow curve from identity to the SH011 grade over `frames`."""
    a = np.asarray(Image.open(src_png).convert("RGB")).astype(np.float32) / 255.0
    lum = a.mean(-1, keepdims=True)
    k_end = 0.42 + 0.50 * np.clip(lum, 0, 1) ** 1.5
    tmp = os.path.splitext(out_mp4)[0] + "_frames"
    os.makedirs(tmp, exist_ok=True)
    for i in range(frames):
        t = i / (frames - 1)
        t = t * t * (3 - 2 * t)                    # ease: the light goes slowly, then faster, then settles
        k = 1.0 + t * (k_end - 1.0)
        out = a * k
        out[..., 0] *= (1 - 0.04 * t); out[..., 2] *= (1 + 0.04 * t)
        Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(os.path.join(tmp, "f%04d.png" % i))
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
        if sid in REUSE:
            normalise(os.path.join(V1, REUSE[sid]), dst)
        elif sid == "SH011":
            lf = os.path.join(work, "SH010_last.png")
            last_frame(os.path.join(work, "SH010.mp4"), lf)
            light_ramp(lf, dst, FRAMES["SH011"])
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
