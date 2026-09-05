#!/usr/bin/env python3
r"""mix_NH-S901.py - place and mix the fourteen sound layers under 'The Scaffold' and mux onto the picture.

The teaser is wordless and unscored; this file IS the soundtrack. Every placement below is a line of the
storyboard's sound brief (04_preproduction/storyboards/NH-S901_THE_SCAFFOLD_TEASER.md). The mix is done in
numpy so every gain, fade and low-pass is a number in this file rather than a session nobody can reopen.

Three buses: BED (the ambiences and far layers, automated), FX (the events, never ducked), INT (the room,
shots 5-6). A master envelope carries the end.

usage: mix_NH-S901.py SFX_DIR PICTURE.mp4 OUT.mp4 [--timeline PICTURE.timeline.json] [--wav OUT.wav] [--master DB]

Timeline: read from the assembler's timeline JSON ({shot: [start, duration]}, v3) so the in-points are the
picture's own; without --timeline the v2 layout (16n+1 frames at 16 fps + 1 s black) is computed.

v3 (2026-09-05): the banner insert SH012 (wind and the fabric breathing), and the trailer's end - one second of
silence after the cut on stillness, then the FOURTH hammer strike under the title (the first sound of the trailer
is its last), then nothing under the studio card.
"""
import os
import subprocess
import sys
import wave

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
FPS = 16
SHOTS = [("SH001", 5), ("SH002", 6), ("SH003", 6), ("SH004", 5), ("SH005", 5), ("SH006", 5),
         ("SH007", 6), ("SH008", 5), ("SH009", 6), ("SH010", 5), ("SH011", 6)]
TAIL_BLACK = 1.0


def in_points(timeline=None):
    if timeline:
        import json
        tl = json.load(open(timeline))
        return {k: v[0] for k, v in tl.items()}, {k: v[1] for k, v in tl.items()}
    t, out, dur = 0.0, {}, {}
    for sid, s in SHOTS:
        out[sid] = t; dur[sid] = (FPS * s + 1) / FPS
        t += (FPS * s + 1) / FPS
    out["END"] = t + TAIL_BLACK
    return out, dur


def db(x):
    return 10 ** (np.asarray(x, dtype=float) / 20.0)


class Mix:
    def __init__(self, sfx_dir, length_s):
        self.dir = sfx_dir
        self.n = int(round(length_s * SR))
        self.bus = {k: np.zeros(self.n) for k in ("bed", "fx", "int")}
        self.auto = {k: [] for k in self.bus}      # breakpoints (t, dB) per bus
        self.master = []
        self.cache = {}

    def load(self, name):
        if name not in self.cache:
            raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(self.dir, name + ".mp3"),
                                  "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
            self.cache[name] = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
        return self.cache[name]

    @staticmethod
    def lowpass(x, hz):
        return sosfilt(butter(2, hz / (SR / 2), btype="low", output="sos"), x)

    @staticmethod
    def fade(x, fin=0.0, fout=0.0):
        x = x.copy()
        a, b = int(fin * SR), int(fout * SR)
        if a > 0:
            x[:a] *= np.linspace(0, 1, a)
        if b > 0:
            x[-b:] *= np.linspace(1, 0, b)
        return x

    def place(self, name, at, gain_db=0.0, bus="fx", start=0.0, end=None, fin=0.01, fout=0.05, lp=None,
              loop_until=None):
        """Put SFX `name` (optionally a [start,end] slice) on `bus` at timeline second `at`.
        loop_until: repeat the slice with a 250 ms crossfade until that timeline second."""
        x = self.load(name)
        s = int(start * SR)
        e = len(x) if end is None else int(end * SR)
        seg = x[s:e]
        if loop_until is not None:
            need = int((loop_until - at) * SR)
            xf = int(0.25 * SR)
            out = seg.copy()
            while len(out) < need:
                nxt = seg.copy()
                out[-xf:] = out[-xf:] * np.linspace(1, 0, xf) + nxt[:xf] * np.linspace(0, 1, xf)
                out = np.concatenate([out, nxt[xf:]])
            seg = out[:need]
        if lp:
            seg = self.lowpass(seg, lp)
        seg = self.fade(seg, fin, fout) * float(db(gain_db))
        i = int(at * SR)
        j = min(i + len(seg), self.n)
        self.bus[bus][i:j] += seg[:j - i]

    @staticmethod
    def envelope(points, n):
        """Breakpoint automation in dB: holds the first value before the first point, linear ramps between
        points, holds the last value after. Returns linear gain."""
        if not points:
            return np.ones(n)
        pts = sorted(points)
        t = np.arange(n) / SR
        return db(np.interp(t, [p[0] for p in pts], [p[1] for p in pts]))

    def render(self, master_db=0.0):
        out = np.zeros(self.n)
        for k, b in self.bus.items():
            out += b * self.envelope(self.auto[k], self.n)
        out *= self.envelope(self.master, self.n) * float(db(master_db))
        return out


def build(sfx_dir, master_db=0.0, timeline=None):
    S, D = in_points(timeline)
    m = Mix(sfx_dir, S["END"])

    # ---- SH001 black: three unhurried strikes, alone, in the cold. -----------------------------------------
    # hammer_single came back as a 14-strike run; its last strike (6.45 s) has the only clean 3.5 s tail, so
    # that one strike is the instrument, placed three times.
    # v8: shots slowed to 75% in post (motion-compensated interpolation) - an action at +t in the Veo clip lands at
    # +t/0.75 in the cut. Offsets inside these shots go through T().
    SLOW = {"SH003": 0.75, "SH004": 0.75, "SH006": 0.75, "SH007": 0.75, "SH008": 0.75, "SH009": 0.75}
    T = lambda sid, off: S[sid] + off / SLOW.get(sid, 1.0)
    STRIKE = dict(start=6.45, end=9.95, fin=0.003, fout=0.4)
    for t in (0.6, 2.5, 4.3):
        m.place("hammer_single", t, -7, **STRIKE)

    # ---- Exterior bed: SH002-SH004 and SH007-SH010 (hard-cut at the interior shots, like the picture) -------
    for a, b in ((S["SH002"], S["SH005"]), (S["SH007"], S["SH011"])):
        m.place("city_ambience", a, -22, bus="bed", fin=0.4, fout=0.25, loop_until=b)
        m.place("wind_winter", a, -21, bus="bed", fin=0.6, fout=0.25, loop_until=b)
        m.place("drizzle_square", a, -19, bus="bed", fin=0.5, fout=0.25, loop_until=b)
    # bed automation: duck under the saw; thin out through dusk
    m.auto["bed"] += [(S["SH004"], 0.0), (T("SH004", 0.25), -7.0), (S["SH005"] - 0.3, -7.0), (S["SH005"], 0.0),
                      (S["SH010"] - 0.5, 0.0), (S["SH010"] + 1.5, -5.0), (S["SH011"], -8.0)]

    # ---- SH002 first light: a bus at the corner, men arriving, lumber coming off the flatbed -----------------
    m.place("bus_brake_far", S["SH002"] + 2.3, -17)
    m.place("workmen_far", S["SH002"] + 2.8, -25, fin=1.0, fout=0.5, end=3.2)
    m.place("timber_drop", S["SH002"] + 3.9, -10, start=0.6, end=2.0, fout=0.3)      # unloading, off-screen (the small drop)

    # ---- SH012 the banner (v3): only wind and the fabric breathing; the city falls away for four seconds ----
    if "SH012" in S:
        m.auto["bed"] += [(S["SH012"] - 0.2, 0.0), (S["SH012"] + 0.4, -6.0), (S["SH003"] - 0.3, -6.0), (S["SH003"], 0.0)]
        m.place("banner_flap", S["SH012"], -16, fin=0.4, fout=0.4, end=D["SH012"])
        m.place("wind_winter", S["SH012"], -19, fin=0.5, fout=0.4, start=6.0, end=6.0 + D["SH012"])
        m.place("drizzle_square", S["SH012"], -20, fin=0.4, fout=0.4, start=3.0, end=3.0 + D["SH012"])

    # ---- SH003 uprights: distant nailing on the joists, voices, the post's foot seats at the end ------------
    m.place("workmen_far", T("SH003", 0.2), -22, fin=0.5, fout=0.6, end=5.6)
    m.place("hammer_work", T("SH003", 0.6), -24, start=0.0, end=4.6, fin=0.3, fout=0.5)
    m.place("timber_drop", T("SH003", 5.3), -5, start=0.6, end=2.0, fin=0.005, fout=0.3)

    # ---- SH004 chop saw: the whine rises and is cut off hard ---------------------------------------------------
    saw_len = (S["SH005"] - 0.3) - (T("SH004", 0.15))
    m.place("chop_saw", T("SH004", 0.15), -13, start=0.0, end=saw_len, fin=0.02, fout=0.03)
    m.place("drizzle_timber", S["SH004"], -24, fin=0.3, fout=0.2, loop_until=S["SH005"])

    # ---- SH005 Pengold at the glass / SH006 his POV: the room, and the build through closed windows ---------
    m.place("interior_room", S["SH005"], -8, bus="int", fin=0.05, fout=0.05, loop_until=S["SH007"])
    m.place("hammer_work", S["SH005"] + 0.8, -25, bus="int", start=5.0, end=14.5, fin=0.5, fout=0.5, lp=900)
    m.place("circular_saw", S["SH005"] + 2.2, -33, bus="int", start=1.0, end=5.5, fin=0.3, fout=0.4, lp=700)
    m.place("city_ambience", S["SH005"], -34, bus="int", fin=0.2, fout=0.2, lp=400, loop_until=S["SH007"])
    m.place("drizzle_square", S["SH005"], -30, bus="int", fin=0.3, fout=0.3, lp=1500, loop_until=S["SH007"])   # rain on the glass
    m.place("workmen_far", T("SH006", 0.3), -30, bus="int", end=4.6, fin=0.4, fout=0.4, lp=1200)
    m.place("nailgun", T("SH006", 0.9), -27, bus="int", start=0.0, end=2.7, fin=0.05, fout=0.1, lp=1000)

    # ---- SH007 the crossbeam seats. Then the beat too long. --------------------------------------------------
    m.place("workmen_far", T("SH007", 0.2), -22, end=3.2, fin=0.3, fout=0.6)
    m.place("timber_drop", T("SH007", 2.95), -12, start=3.05, end=5.6, fin=0.003, fout=0.6)   # the big slap at 3.14 -> lands at +3.04 s
    m.place("halyard", T("SH007", 3.2), -28, bus="bed", fin=0.8, fout=0.4, end=2.8)           # only the wind is left

    # ---- SH008 decking: boots, the nail gun, the brush ------------------------------------------------------
    m.place("boots_decking", T("SH008", 0.2), +10, fin=0.05, fout=0.2, end=4.7)
    m.place("drizzle_timber", S["SH008"], -22, fin=0.3, fout=0.3, loop_until=S["SH009"])
    m.place("nailgun", T("SH008", 1.5), -12, start=0.0, end=1.95, fin=0.02, fout=0.08)
    m.place("hammer_work", T("SH008", 0.4), -26, start=8.0, end=12.4, fin=0.3, fout=0.4)

    # ---- SH009 steps: the last screws, his weight on the tread, he walks off -------------------------------
    m.place("drill", T("SH009", 0.1), -18, fin=0.05, fout=0.2, end=3.2)
    m.place("boots_decking", T("SH009", 1.0), +8, start=3.85, end=5.75, fin=0.02, fout=0.15)    # two steps, the test
    m.place("workmen_far", T("SH009", 1.6), -24, start=6.0, end=12.5, fin=0.5, fout=0.6)        # the laugh is in here
    m.place("bus_brake_far", T("SH009", 3.8), -22)

    # ---- SH010 dusk: sound thins to wind and the halyard; the first strikes return, far away ----------------
    m.place("halyard", S["SH010"] + 0.1, -18, bus="bed", fin=1.2, fout=0.0, loop_until=S["SH011"] + 5.0)
    for t in (0.9, 2.7, 4.5):
        m.place("hammer_single", S["SH010"] + t, -20, lp=2500, **STRIKE)

    # ---- SH011 the last light goes: everything to nothing by 5.0 s in; one second of silence; black --------
    m.master += [(S["SH011"] + 0.8, 0.0), (S["SH011"] + 5.0, -70.0)]
    if "TITLE" in S:
        m.master += [(S["TITLE"] - 0.05, -70.0), (S["TITLE"], 0.0)]
        m.place("hammer_single", S["TITLE"] + 0.35, -8, **STRIKE)     # the fourth strike, under the title

    out = m.render(master_db)
    end_silence = int((S["SH011"] + 5.0) * SR)
    resume = int((S["TITLE"] - 0.05) * SR) if "TITLE" in S else len(out)
    out[end_silence:resume] = 0.0
    peak = np.abs(out).max()
    if peak > db(-1.0):
        print("[mix] peak %.2f dBFS - limiting by %.1f dB" % (20 * np.log10(peak), 20 * np.log10(peak) + 1.0))
        out *= float(db(-1.0)) / peak
    return out, S


def write_wav(x, path):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


def main():
    args = sys.argv[1:]
    master = 3.0; wav = None
    if "--master" in args:
        i = args.index("--master"); master = float(args[i + 1]); del args[i:i + 2]
    if "--wav" in args:
        i = args.index("--wav"); wav = args[i + 1]; del args[i:i + 2]
    timeline = None
    if "--timeline" in args:
        i = args.index("--timeline"); timeline = args[i + 1]; del args[i:i + 2]
    sfx_dir, picture, out = args[0], args[1], args[2]
    x, S = build(sfx_dir, master, timeline)
    wav = wav or os.path.splitext(out)[0] + ".wav"
    write_wav(x, wav)
    print("[mix] %.2f s, in-points: %s" % (S["END"], {k: round(v, 3) for k, v in S.items()}))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", picture, "-i", wav, "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out], check=True)
    lufs = subprocess.run(["ffmpeg", "-v", "info", "-i", out, "-af", "ebur128=peak=true", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    tail = lufs[lufs.rfind("Integrated loudness"):]
    print("[mix] loudness: " + " | ".join(l.strip() for l in tail.splitlines()[:8] if l.strip()))
    print("[mix] wrote", out)


if __name__ == "__main__":
    main()
