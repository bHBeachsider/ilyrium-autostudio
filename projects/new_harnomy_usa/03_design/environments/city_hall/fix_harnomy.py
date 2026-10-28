#!/usr/bin/env python3
r"""fix_harnomy.py - swap the M-O-N of a rendered "HARMONY" back to N-O-M ("HARNOMY") in pixels.

nano-banana-pro auto-corrects the town's name on every generation (NH-USA-033). The banner lettering is
pale sans capitals on mauve fabric, so the three glyphs can be located from the column ink profile and
re-laid in the other order, alpha-keyed on luminance so the fabric weave survives under them.

usage: fix_harnomy.py IN.png OUT.png X0 Y0 X1 Y1 [--debug DBG.png] [--word N]
  X0..Y1  a rough box around the banner's FIRST text line (the line that carries NEW HARNOMY).
  --word  index of the word to fix within that line (default 1 = second word).
Prints the letter runs it found; refuses to write if it does not find exactly seven letters.
"""
import sys
import numpy as np
from PIL import Image


def runs_of(mask):
    out, s = [], None
    for i, v in enumerate(mask):
        if v and s is None:
            s = i
        if not v and s is not None:
            out.append((s, i - 1)); s = None
    if s is not None:
        out.append((s, len(mask) - 1))
    return out


def fix(src, dst, roi, word_index=1, debug=None):
    img = Image.open(src).convert("RGB")
    a = np.asarray(img).astype(np.float32)
    x0, y0, x1, y1 = roi
    reg = a[y0:y1, x0:x1]
    lum = reg.mean(-1)
    bg = np.percentile(lum, 30)            # fabric
    ink_thr = bg + 0.45 * (np.percentile(lum, 97) - bg)
    ink = lum > ink_thr
    # text rows: rows with enough ink columns; take the first band (line 1)
    rows = ink.sum(1) > max(3, 0.02 * ink.shape[1])
    bands = runs_of(rows)
    bands = [b for b in bands if b[1] - b[0] >= 6]
    if not bands:
        raise SystemExit("no text band found in roi")
    r0, r1 = max(bands, key=lambda b: ink[b[0]:b[1] + 1].sum())
    pad = 2
    r0 = max(0, r0 - pad); r1 = min(ink.shape[0] - 1, r1 + pad)
    line = ink[r0:r1 + 1]
    cols = line.any(0)
    letter_runs = runs_of(cols)
    # merge runs separated by tiny gaps (anti-aliasing splits), gap <= 1 px
    merged = []
    for r in letter_runs:
        if merged and r[0] - merged[-1][1] <= 1:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(r)
    letter_runs = [r for r in merged if r[1] - r[0] >= 2]
    gaps = [letter_runs[i + 1][0] - letter_runs[i][1] for i in range(len(letter_runs) - 1)]
    med = np.median(gaps) if gaps else 3
    # words: split where the gap is clearly a space (> 2.2x median letter gap)
    words, cur = [], [letter_runs[0]]
    for i, g in enumerate(gaps):
        if g > 2.2 * med:
            words.append(cur); cur = []
        cur.append(letter_runs[i + 1])
    words.append(cur)
    print("line rows %d-%d (abs %d-%d); words: %s" % (r0, r1, y0 + r0, y0 + r1,
          [(x0 + w[0][0], x0 + w[-1][1], len(w)) for w in words]))
    if word_index >= len(words):
        raise SystemExit("word index out of range")
    W = words[word_index]
    if len(W) != 7:
        sevens = [i for i, w in enumerate(words) if len(w) == 7]
        if len(sevens) == 1:
            word_index = sevens[0]; W = words[word_index]
            print("word %d is not 7 letters; using the only 7-letter word, index %d" % (word_index, sevens[0]))
    print("letters in word %d: %s" % (word_index, [(x0 + l[0], x0 + l[1]) for l in W]))
    if len(W) != 7:
        raise SystemExit("expected 7 letters (HARMONY), found %d - adjust roi" % len(W))
    H, A, R, M, O, N, Y = W
    ay0, ay1 = y0 + r0, y0 + r1 + 1
    ax = lambda l: (x0 + l[0], x0 + l[1] + 1)
    Mx, Ox, Nx = ax(M), ax(O), ax(N)
    g1, g2 = Ox[0] - Mx[1], Nx[0] - Ox[1]
    out = a.copy()
    # fabric sample: the space between this word and the previous one, same rows
    prev = words[word_index - 1] if word_index > 0 else None
    if prev is not None:
        sx0, sx1 = x0 + prev[-1][1] + 2, x0 + W[0][0] - 1
    else:
        sx0, sx1 = x0 + W[-1][1] + 2, x0 + W[-1][1] + 8
    strip = a[ay0:ay1, sx0:sx1]
    span0, span1 = Mx[0], Nx[1]
    tile = np.hstack([strip] * ((span1 - span0) // strip.shape[1] + 2))[:, :span1 - span0]
    out[ay0:ay1, span0:span1] = tile
    gM, gO, gN = (a[ay0:ay1, s:e] for s, e in (Mx, Ox, Nx))

    def paste(g, x):
        gl = g.mean(-1)
        b = np.percentile(gl, 15); k = np.percentile(gl, 90)
        alpha = np.clip((gl - b) / max(k - b, 1.0), 0, 1)[..., None]
        w = g.shape[1]
        out[ay0:ay1, x:x + w] = out[ay0:ay1, x:x + w] * (1 - alpha) + g * alpha
        return x + w

    x = paste(gN, span0); x = paste(gO, x + g1); x = paste(gM, x + g2)
    print("laid N,O,M over x %d-%d (ends %d, expected %d)" % (span0, span1, x, span1))
    res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    res.save(dst)
    if debug:
        cx0 = max(0, x0 + words[0][0][0] - 10); cx1 = min(a.shape[1], x0 + W[-1][1] + 12)
        crop = res.crop((cx0, ay0 - 8, cx1, ay1 + 8))
        crop.resize((crop.width * 6, crop.height * 6), Image.NEAREST).save(debug)
    return dst


if __name__ == "__main__":
    args = sys.argv[1:]
    dbg = None; wi = 1
    if "--debug" in args:
        i = args.index("--debug"); dbg = args[i + 1]; del args[i:i + 2]
    if "--word" in args:
        i = args.index("--word"); wi = int(args[i + 1]); del args[i:i + 2]
    src, dst = args[0], args[1]
    roi = tuple(int(v) for v in args[2:6])
    fix(src, dst, roi, wi, dbg)
