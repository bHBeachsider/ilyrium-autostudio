"""
Delivery tail (roadmap P4): captions, platform export presets, marketing cutdowns.

- build_captions(project, out_dir): SRT/VTT from the script's voiceover lines, timed
  sequentially by per-shot duration. No transcription needed — we already know the
  exact spoken words (a Whisper pass is only needed for un-scripted dialogue/ambient).
- export_preset(master, out_dir, target): FFmpeg re-encode to a platform spec
  (9:16 / 1:1 / 16:9) with loudness normalization → platform_cuts.
- make_cutdown(master, out_dir, seconds): a fast trimmed cutdown for short-form variants.

FFmpeg comes from imageio-ffmpeg (already a dep via moviepy); no system install needed.
"""

import os
import subprocess


def _ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _ts(seconds: float, sep: str = ",") -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def build_captions(project: dict, out_dir: str, default_dur: float = None) -> dict:
    """Write <campaign>.srt and .vtt from the shots' voiceover lines, sequenced by
    per-shot duration. Returns {'srt': path, 'vtt': path}."""
    dur = float(default_dur or os.getenv("ILYRIUM_SHOT_DURATION_SEC", "8"))
    os.makedirs(out_dir, exist_ok=True)
    base = project.get("campaign_id", "captions")
    srt_path = os.path.join(out_dir, f"{base}.srt")
    vtt_path = os.path.join(out_dir, f"{base}.vtt")

    shots = sorted(project.get("shots", []), key=lambda s: s.get("scene_number", 0))
    srt_lines, vtt_lines = [], ["WEBVTT", ""]
    t = 0.0
    idx = 0
    for s in shots:
        vo = (s.get("voiceover") or "").strip()
        # use the shot's selected take duration if recorded, else the default
        take = next((x for x in s.get("takes", []) if x.get("take_id") == s.get("selected_take")), None)
        seg = float(take.get("duration")) if take and take.get("duration") else dur
        if vo:
            idx += 1
            start, end = _ts(t), _ts(t + seg)
            srt_lines += [str(idx), f"{start} --> {end}", vo, ""]
            vtt_lines += [f"{_ts(t, '.')} --> {_ts(t + seg, '.')}", vo, ""]
        t += seg

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))
    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(vtt_lines))
    return {"srt": srt_path, "vtt": vtt_path, "cues": idx}


# target -> (width, height)
PRESETS = {"9:16": (1080, 1920), "1:1": (1080, 1080), "16:9": (1920, 1080)}


def export_preset(master_path: str, out_dir: str, target: str = "9:16",
                  vbitrate: str = "8M", loudnorm: bool = True) -> str:
    """Re-encode the master to a platform aspect with let/pillar-boxing + loudness norm."""
    if target not in PRESETS:
        raise ValueError(f"unknown preset {target}")
    w, h = PRESETS[target]
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(master_path))[0]
    out = os.path.join(out_dir, f"{base}_{target.replace(':', 'x')}.mp4")
    vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black"
    cmd = [_ffmpeg(), "-y", "-i", master_path, "-vf", vf, "-c:v", "libx264", "-b:v", vbitrate,
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k"]
    if loudnorm:
        cmd += ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11"]   # -14 LUFS ~ social platforms
    cmd += [out]
    subprocess.run(cmd, check=True, capture_output=True, timeout=600)
    return out


def _llm_pick_scenes(scenes: list, seconds: int) -> list:
    """Ask an LLM which scene_numbers (and order) make the best `seconds` cutdown."""
    import anthropic
    import json
    import re
    client = anthropic.Anthropic()
    sys = (f"You are a short-form ad editor. From the scenes, choose the subset and ORDER that makes "
           f"the punchiest {seconds}-second cutdown (hook first, CTA last). Assume ~6s per scene. "
           f"Output ONLY a JSON array of scene_number integers.")
    r = client.messages.create(model="claude-sonnet-5", max_tokens=300, system=sys,
                               messages=[{"role": "user", "content": json.dumps(scenes)}])
    t = "".join(b.text for b in r.content if getattr(b, "type", None) == "text")
    m = re.search(r"\[.*\]", t, re.DOTALL)
    return json.loads(m.group(0)) if m else []


def ai_cutdown(project: dict, out_dir: str, seconds: int = 15) -> str:
    """AI marketing cutdown: an LLM selects/orders scenes for a target duration, then a
    NEW variant is assembled from those scenes' selected takes (reuses existing renders —
    no re-generation). Returns the variant mp4 path."""
    import project_store as ps
    shots = sorted(project.get("shots", []), key=lambda x: x.get("scene_number", 0))
    scenes = [{"scene_number": s["scene_number"], "voiceover": s.get("voiceover", ""),
               "visual": (s.get("visual_prompt", "") or "")[:120]} for s in shots]
    try:
        order = _llm_pick_scenes(scenes, seconds)
    except Exception:
        order = []
    media = ps.selected_media(project)            # [{scene_number, video, audio}]
    by = {m["scene_number"]: m for m in media}
    chosen = [by[n] for n in order if n in by] or media[: max(1, seconds // 6)]
    if not chosen:
        raise RuntimeError("no usable takes to assemble a cutdown")
    from media.post_production import compile_final_video
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{project.get('campaign_id', 'cut')}_aicut{seconds}s.mp4")
    compile_final_video(chosen, output_filename=out, duck=project.get("audio_duck"),
                        music_path=project.get("music"), music_gain=project.get("music_gain", 0.15))
    return out


def make_cutdown(master_path: str, out_dir: str, seconds: int = 15) -> str:
    """Fast trim to the first N seconds for a short-form cutdown variant."""
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(master_path))[0]
    out = os.path.join(out_dir, f"{base}_cut{seconds}s.mp4")
    cmd = [_ffmpeg(), "-y", "-i", master_path, "-t", str(int(seconds)),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", out]
    subprocess.run(cmd, check=True, capture_output=True, timeout=600)
    return out
