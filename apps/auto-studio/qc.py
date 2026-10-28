"""
Frame-level QC (roadmap polish): flag unusable takes via FFmpeg detectors —
black frames, freezes, and long silences — before they reach the cut. No extra
deps (bundled imageio-ffmpeg). qc_project() QCs the selected take of every shot.
"""

import os
import re
import subprocess


def _ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def qc_clip(video_path: str, timeout: int = 120, mode: str = "take",
            loudness_lufs: float = -14.0) -> dict:
    """Analyze one clip. Returns {ok, flags[], black, freezes, silence}.

    mode="cut" is for assembled masters: decode/container/loudness checks only. The
    per-take detectors (freezedetect in particular) stay a per-take gate — on a master
    they false-flag low-motion AI takes once downscaled and multiply on looped shots
    (FilmCraft Phase 0, 2026-10-12)."""
    if mode == "cut":
        return qc_cut(video_path, timeout=timeout, loudness_lufs=loudness_lufs)
    if not video_path or not os.path.exists(video_path):
        return {"ok": False, "flags": ["file missing"], "black": 0, "freezes": 0, "silence": 0}
    cmd = [_ffmpeg(), "-hide_banner", "-i", video_path,
           "-vf", "blackdetect=d=0.2:pic_th=0.98,freezedetect=n=-60dB:d=0.4",
           "-af", "silencedetect=n=-45dB:d=1.0", "-f", "null", "-"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        err = p.stderr or ""
    except Exception as e:
        return {"ok": False, "flags": [f"qc error: {type(e).__name__}"], "black": 0, "freezes": 0, "silence": 0}
    black = sum(float(x) for x in re.findall(r"black_duration:(\d+\.?\d*)", err))
    freezes = len(re.findall(r"freeze_start", err))
    silence = sum(float(x) for x in re.findall(r"silence_duration:\s*(\d+\.?\d*)", err))
    flags = []
    if black >= 0.3:
        flags.append(f"black frames {round(black, 1)}s")
    if freezes:
        flags.append(f"freeze x{freezes}")
    if silence >= 2.0:
        flags.append(f"silence {round(silence, 1)}s")
    return {"ok": not flags, "flags": flags, "black": round(black, 2), "freezes": freezes, "silence": round(silence, 2)}


LOUDNESS_TOLERANCE_LU = 1.0


def qc_cut(video_path: str, timeout: int = 600, loudness_lufs: float = -14.0) -> dict:
    """QC an assembled master: strict decode clean, has video + audio streams, integrated
    loudness within LOUDNESS_TOLERANCE_LU of `loudness_lufs` (ffmpeg ebur128 as oracle).
    Returns {ok, flags[], decode_errors, video, audio, integrated_lufs, true_peak_dbfs}."""
    out = {"ok": False, "flags": [], "decode_errors": None, "video": False, "audio": False,
           "integrated_lufs": None, "true_peak_dbfs": None}
    if not video_path or not os.path.exists(video_path):
        out["flags"] = ["file missing"]
        return out
    try:
        dec = subprocess.run([_ffmpeg(), "-v", "error", "-err_detect", "compliant", "-i", video_path,
                              "-f", "null", "-"], capture_output=True, text=True, timeout=timeout)
        meter = subprocess.run([_ffmpeg(), "-hide_banner", "-nostats", "-i", video_path,
                                "-af", "ebur128=peak=true", "-f", "null", "-"],
                               capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        out["flags"] = [f"qc error: {type(e).__name__}"]
        return out
    dec_err = (dec.stderr or "").strip()
    out["decode_errors"] = dec_err[:400] or None
    err = meter.stderr or ""
    out["video"] = bool(re.search(r"Stream #\S+.*: Video:", err))
    out["audio"] = bool(re.search(r"Stream #\S+.*: Audio:", err))
    summary = err[err.rfind("Summary:"):] if "Summary:" in err else ""
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", summary)
    tp = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary)
    out["integrated_lufs"] = float(m.group(1)) if m else None
    out["true_peak_dbfs"] = float(tp.group(1)) if tp else None
    flags = []
    if dec.returncode != 0 or dec_err:
        flags.append("decode errors")
    if not out["video"]:
        flags.append("no video stream")
    if not out["audio"]:
        flags.append("no audio stream")
    if out["integrated_lufs"] is None:
        if out["audio"]:
            flags.append("loudness unmeasured")
    elif abs(out["integrated_lufs"] - loudness_lufs) > LOUDNESS_TOLERANCE_LU:
        flags.append(f"loudness {out['integrated_lufs']} LUFS (target {loudness_lufs})")
    out["flags"] = flags
    out["ok"] = not flags
    return out


def qc_project(project: dict) -> dict:
    """QC the selected take of each shot. Returns {shots:[{scene, ok, flags,...}], flagged:[scene,...]}."""
    import project_store as ps
    out = []
    for s in sorted(project.get("shots", []), key=lambda x: x.get("scene_number", 0)):
        sel = s.get("selected_take")
        take = ps.get_take(s, sel) if sel else None
        if take and take.get("video") and os.path.exists(take["video"]):
            r = qc_clip(take["video"]); r["scene"] = s["scene_number"]
            out.append(r)
    return {"shots": out, "flagged": [r["scene"] for r in out if not r["ok"]]}
