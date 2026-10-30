"""FilmCraft edit engine — cut-as-code (Phase 1 of docs/plans/2026-10-12-filmcraft-edit-engine.md).

A cut is a generated JSONL command script (`cut.jsonl`) run headless by filmcraft-cli into a
`.fcproj`; `inspect sequence` is saved beside it as the edit decision. Every binary call goes
through harness.run.filmcraft_* (traced; lint-enforced).

Layout (one cut per directory, never overwritten):
  outputs/<campaign>/cuts/<cut_id>/
    dry.jsonl  ids.json  cut.jsonl  <cut_id>.fcproj  sequence.json  cut_meta.json
    master.mp4  frames/  <cut_id>.xml|.otio

Timeline: V1 colour matte (pillarbox; black, or kernel delivery.pillarbox), V2 the selected
takes fitted to frame (a take shorter than its VO loops, like the moviepy path), A1 native take
audio, A2 VO, A3 music bed. FilmCraft owns the levels and nothing is applied twice:
project `audio_duck` -> static native-audio gain, `music_gain` -> static bed trim, and the bed is
ducked against Dialogue by Essential Sound.

Clip ids are learned by a dry run of the placement steps (ids are deterministic for a fresh
project but hard to predict), persisted in ids.json, then baked into the static cut.jsonl.
Phase 0 results and decisions: docs/research/2026-10-12-filmcraft-bakeoff-results.md.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from fractions import Fraction
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from harness import run as harness_run  # noqa: E402

APP_DIR = Path(__file__).resolve().parents[1]
TICKS_PER_SECOND = 254_016_000_000

# Levels (decided 2026-10-12; starting points — Brad tunes by ear on the first real cut).
BED_TRIM_DB = -10.0        # static bed trim when project.json sets no music_gain
BED_DUCK_DB = -12.0        # Essential Sound ducking of the bed under Dialogue
DUCK_FADE_S = 0.8          # ducking fade
NATIVE_AUDIO_DUCK = 0.35   # mirrors post_production.CLIP_AUDIO_DUCK when audio_duck is unset

DEFAULT_PILLARBOX = "#000000"
DEFAULT_LOUDNESS_LUFS = -14.0
ASPECT_SIZES = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080),
                "4:5": (1080, 1350), "21:9": (2560, 1080)}

# Master export presets. Routing (decided 2026-10-12): FilmCraft NVENC is the master export
# for assembled cuts, explicit bitrate + loudness; delivery.py/ffmpeg keeps platform cutdowns.
EXPORT_PRESETS = {
    "master": {"format": "h264", "hardwareEncoding": "auto", "bitrateMode": "vbr1Pass",
               "bitrateKbps": 12000},
    "master_sw": {"format": "h264", "hardwareEncoding": "off", "bitrateMode": "crf", "crf": 18},
}

_IMAGE_EXTS = (".png", ".exr", ".tif", ".tiff", ".jpg", ".jpeg", ".dpx")


# --------------------------------------------------------------------------- #
# Pure helpers (no binary) — unit-tested
# --------------------------------------------------------------------------- #
def frame_rate(fps: float) -> Fraction:
    """Exact rate; 23.976 / 29.97 / 59.94 snap to the NTSC n*1000/1001 rationals."""
    n = round(fps)
    if n and abs(fps - Fraction(n * 1000, 1001)) < 0.005 and abs(fps - n) > 0.005:
        return Fraction(n * 1000, 1001)
    return Fraction(fps).limit_denominator(1000)


def ticks_per_frame(fps: float) -> Fraction:
    return Fraction(TICKS_PER_SECOND) / frame_rate(fps)


def to_frames(ticks: int, fps: float) -> int:
    """Ticks -> whole frames, half up (FilmCraft's own snapping: 121.5 -> 122)."""
    return math.floor(Fraction(ticks) / ticks_per_frame(fps) + Fraction(1, 2))


def frames_to_ticks(frames: int, fps: float) -> int:
    t = frames * ticks_per_frame(fps)
    if t.denominator != 1:
        raise ValueError(f"{fps} fps has no whole-tick frame duration")
    return int(t)


def db(gain: float) -> float:
    return round(20 * math.log10(gain), 2)


def sequence_settings(project: dict, kernel: dict | None = None) -> dict:
    """Sequence + delivery settings from the kernel's `delivery` block, then the project,
    then defaults (1920x1080, 24 fps, 48 kHz, black pillarbox, -14 LUFS).

    For portrait (9:16) the V1 colour matte acts as a letterbox matte; for landscape
    it is a pillarbox matte. `matte_style` carries this distinction.
    """
    d = (kernel or {}).get("delivery") or {}
    w, h = ASPECT_SIZES.get(str(project.get("aspect_ratio") or "16:9"), ASPECT_SIZES["16:9"])
    eff_w = int(d.get("width") or w)
    eff_h = int(d.get("height") or h)
    return {
        "width": eff_w,
        "height": eff_h,
        "fps": float(d.get("fps") or project.get("fps") or 24),
        "sample_rate": int(d.get("sample_rate") or 48000),
        "pillarbox": d.get("pillarbox") or DEFAULT_PILLARBOX,
        "loudness_lufs": float(d.get("loudness_lufs") or DEFAULT_LOUDNESS_LUFS),
        "matte_style": "letterbox" if eff_h > eff_w else "pillarbox",
    }


def levels(project: dict) -> dict:
    duck = project.get("audio_duck")
    gain = project.get("music_gain")
    return {
        "native_gain_db": db(max(0.001, min(1.0, duck))) if duck is not None else db(NATIVE_AUDIO_DUCK),
        "bed_trim_db": db(max(0.001, gain)) if gain else BED_TRIM_DB,
        "bed_duck_db": BED_DUCK_DB,
        "duck_fade_s": DUCK_FADE_S,
    }


def _import_list(manifest: dict) -> list[str]:
    paths = []
    for s in manifest["shots"]:
        paths.append(s["video"])
    for s in manifest["shots"]:
        if s.get("vo"):
            paths.append(s["vo"])
    if manifest.get("music"):
        paths.append(manifest["music"]["path"])
    seen, out = set(), []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _fill(item: int, length: int, total: int, base: dict, start: int, tpf_ticks) -> list[dict]:
    """Place `item` (natural length `length` frames) back to back from `start` to fill `total`
    frames; the last copy is trimmed with `duration`. This is the moviepy 'loop' extend."""
    steps, t = [], 0
    while t < total:
        seg = min(length, total - t)
        p = {"item": item, **base, "frame": start + t}
        if seg < length:
            p["duration"] = tpf_ticks(seg)
        steps.append({"id": "timeline.place", "params": p})
        t += seg
    return steps


def build_dry_script(manifest: dict) -> tuple[list[dict], list[dict], dict]:
    """Head (4 steps) + placement steps — everything whose ids do not depend on earlier
    clip ids. Returns (steps, plan, meta); plan[i] describes steps[4 + i]."""
    fps = manifest["fps"]
    tpf = lambda n: frames_to_ticks(n, fps)  # noqa: E731
    paths = _import_list(manifest)
    item = {p: i + 1 for i, p in enumerate(paths)}
    seq_id = 7 + len(paths)
    matte_id = seq_id + 1
    starts, cursor = [], 0
    for s in manifest["shots"]:
        starts.append(cursor)
        cursor += s["shot_frames"]
    total = cursor
    head = [
        {"id": "file.newProject", "params": {"name": manifest["name"]}},
        {"id": "file.import", "params": {"paths": paths}},
        {"id": "file.newSequence", "params": {"name": manifest["name"], "width": manifest["width"],
                                              "height": manifest["height"], "fps": fps,
                                              "sampleRate": manifest["sample_rate"],
                                              "video": 3, "audio": 3}},
        {"id": "file.newColorMatte", "params": {"color": manifest["pillarbox"],
                                                "seconds": float(Fraction(total) / frame_rate(fps))}},
    ]
    steps, plan = [], []
    steps.append({"id": "timeline.place", "params": {"item": matte_id, "track": "V1", "frame": 0,
                                                     "duration": tpf(total), "audio": False}})
    plan.append({"role": "matte"})
    for i, s in enumerate(manifest["shots"]):
        base = {"track": "V2"}
        if s["has_audio"]:
            base["audioTrack"] = "A1"
        else:
            base["audio"] = False
        for st in _fill(item[s["video"]], s["video_frames"], s["shot_frames"], base, starts[i], tpf):
            steps.append(st)
            plan.append({"role": "take", "shot": i, "has_audio": s["has_audio"]})
        if s.get("vo"):
            steps.append({"id": "timeline.place", "params": {"item": item[s["vo"]], "track": "A2",
                                                             "frame": starts[i], "video": False}})
            plan.append({"role": "vo", "shot": i})
    if manifest.get("music"):
        m = manifest["music"]
        for st in _fill(item[m["path"]], m["frames"], total, {"track": "A3", "video": False}, 0, tpf):
            steps.append(st)
            plan.append({"role": "music"})
    meta = {"items": item, "sequence": seq_id, "matte": matte_id, "starts": starts, "total_frames": total}
    return head + steps, plan, meta


def build_cut_script(manifest: dict, learned_clips: list[list[int]]) -> list[dict]:
    """The full static cut script, given the clip ids the dry run learned (one list per
    placement step, in order)."""
    head_and_places, plan, meta = build_dry_script(manifest)
    if len(learned_clips) != len(plan):
        raise ValueError(f"learned {len(learned_clips)} placements, script has {len(plan)}")
    fps = manifest["fps"]
    video, native, vo, bed = [], [], [], []
    for p, clips in zip(plan, learned_clips):
        if p["role"] == "take":
            video.append(clips[0])
            if p["has_audio"]:
                native.append(clips[1])
        elif p["role"] == "vo":
            vo.append(clips[0])
        elif p["role"] == "music":
            bed.append(clips[0])
    lv = manifest["levels"]
    tail = [{"id": "clip.fitToFrame", "params": {"clips": video}}]
    if native:
        tail.append({"id": "clip.audioGain", "params": {"clips": native, "mode": "set",
                                                        "db": lv["native_gain_db"]}})
    if vo:
        tail.append({"id": "essentialSound.setType", "params": {"clips": vo, "type": "dialogue"}})
    if bed:
        tail.append({"id": "clip.audioGain", "params": {"clips": bed, "mode": "set", "db": lv["bed_trim_db"]}})
        tail.append({"id": "essentialSound.setType", "params": {"clips": bed, "type": "music"}})
        tail.append({"id": "essentialSound.set", "params": {"clips": bed, "values": {
            "ducking.enabled": True, "ducking.reduceDb": lv["bed_duck_db"], "ducking.fadeS": lv["duck_fade_s"]}}})
        if vo:
            tail.append({"id": "essentialSound.generateDucking", "params": {"clips": bed}})
    for i, s in enumerate(manifest["shots"]):
        tail.append({"id": "markers.add", "params": {
            "target": "program", "time": frames_to_ticks(meta["starts"][i], fps),  # frame-quantised
            "name": f"scene_{s['scene']}", "comment": s.get("title", "")[:80]}})
    tail.append({"id": "file.saveAs", "params": {"path": manifest["save_path"]}})
    return head_and_places + tail


def check_dry_run(manifest: dict, rows: list[dict]) -> list[list[int]]:
    """Verify the ids the script assumed (import items, sequence, matte) and return the
    learned clip ids per placement step."""
    steps, plan, meta = build_dry_script(manifest)
    if len(rows) != len(steps):
        raise RuntimeError(f"dry run returned {len(rows)} lines for {len(steps)} steps")
    items = (rows[1].get("result") or {}).get("items")
    if items != list(range(1, len(meta["items"]) + 1)):
        raise RuntimeError(f"import ids {items} != predicted 1..{len(meta['items'])}")
    if (rows[2].get("result") or {}).get("sequence") != meta["sequence"]:
        raise RuntimeError(f"sequence id {rows[2].get('result')} != predicted {meta['sequence']}")
    if (rows[3].get("result") or {}).get("item") != meta["matte"]:
        raise RuntimeError(f"matte id {rows[3].get('result')} != predicted {meta['matte']}")
    return [(r.get("result") or {}).get("clips") for r in rows[4:]]


# --------------------------------------------------------------------------- #
# Media resolution (probes go through the harness)
# --------------------------------------------------------------------------- #
def _resolve(path: str, project_dir: Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    for cand in (APP_DIR / p, project_dir / p, project_dir / p.name):
        if cand.exists():
            return cand.resolve()
    return (APP_DIR / p).resolve()


def _image_sequence(path: Path) -> tuple[str, int] | None:
    """(ffmpeg pattern, start number) if `path` is an image-sequence directory or a numbered
    still, else None."""
    first = None
    if path.is_dir():
        frames = sorted(f for f in path.iterdir() if f.suffix.lower() in _IMAGE_EXTS)
        first = frames[0] if frames else None
    elif path.suffix.lower() in _IMAGE_EXTS:
        first = path
    if first is None:
        return None
    m = re.match(r"^(.*?)(\d+)(\.\w+)$", first.name)
    if not m:
        return None
    prefix, num, ext = m.groups()
    return str(first.with_name(f"{prefix}%0{len(num)}d{ext}")), int(num)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _write_jsonl(path: Path, steps: list[dict]) -> None:
    path.write_bytes("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in steps).encode("utf-8"))


def _write_json(path: Path, obj) -> None:
    path.write_bytes((json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def build_manifest(project: dict, project_dir: str | Path, cut_dir: Path, cut_id: str,
                   kernel: dict | None = None, trace: dict | None = None) -> dict:
    """Resolve the selected takes, probe durations (via the harness) and fix the sequence,
    level and pillarbox settings. Refuses a cut with any shot lacking a selected take."""
    import project_store as ps
    project_dir = Path(project_dir)
    trace = trace or {}
    settings = sequence_settings(project, kernel)
    fps = settings["fps"]
    if project.get("music_mode", "bed") != "bed":
        raise NotImplementedError("filmcraft engine supports music_mode='bed' only; use moviepy")
    shots = []
    for shot in sorted(project["shots"], key=lambda s: s["scene_number"]):
        take = ps.get_take(shot, shot.get("selected_take")) if shot.get("selected_take") else None
        if not take or not take.get("video"):
            raise ValueError(f"shot {shot['scene_number']} has no selected take with video — "
                             "the filmcraft engine refuses partial cuts")
        video = _resolve(take["video"], project_dir)
        seq = _image_sequence(video)
        if seq:
            video = harness_run.ffmpeg_image_sequence_to_mov(
                seq[0], fps, cut_dir / "media" / f"shot{shot['scene_number']}_seq.mov",
                start_number=seq[1], **trace)
        if not video.is_file():
            raise FileNotFoundError(f"shot {shot['scene_number']}: take media missing: {video}")
        vp = harness_run.filmcraft_probe(video, **trace)
        vo = _resolve(take["audio"], project_dir) if take.get("audio") else None
        if vo is not None and not vo.is_file():
            raise FileNotFoundError(f"shot {shot['scene_number']}: VO missing: {vo}")
        vo_frames = to_frames(harness_run.filmcraft_probe(vo, **trace)["duration"], fps) if vo else 0
        video_frames = to_frames(vp["duration"], fps)
        title = shot.get("title") or (shot.get("visual_prompt") or "")[:80]
        shots.append({"scene": shot["scene_number"], "video": str(video), "video_frames": video_frames,
                      "has_audio": bool(vp.get("audio_streams")) and vp.get("kind") != "AudioOnly",
                      "vo": str(vo) if vo else None, "vo_frames": vo_frames,
                      "shot_frames": max(video_frames, vo_frames), "title": title})
    music = None
    if project.get("music"):
        mp = _resolve(project["music"], project_dir)
        if not mp.is_file():
            raise FileNotFoundError(f"music bed missing: {mp}")
        music = {"path": str(mp), "frames": to_frames(harness_run.filmcraft_probe(mp, **trace)["duration"], fps)}
    return {"name": cut_id, **{k: settings[k] for k in ("width", "height", "fps", "sample_rate", "pillarbox")},
            "loudness_lufs": settings["loudness_lufs"], "shots": shots, "music": music,
            "levels": levels(project), "save_path": str(cut_dir / f"{cut_id}.fcproj")}


# --------------------------------------------------------------------------- #
# Engine operations
# --------------------------------------------------------------------------- #
def _trace_args(project: dict, project_dir: Path) -> dict:
    return {"project_id": project.get("campaign_id") or "filmcraft", "trace_dir": project_dir}


def assemble(project: dict, project_dir: str | Path, cut_id: str, kernel: dict | None = None) -> dict:
    """Build cut <cut_id>: dry run -> ids.json -> cut.jsonl -> .fcproj -> sequence.json.
    Writes only under outputs/<campaign>/cuts/<cut_id>/ and refuses an existing cut dir."""
    project_dir = Path(project_dir)
    cut_dir = project_dir / "cuts" / cut_id
    if cut_dir.exists() and any(cut_dir.iterdir()):
        raise FileExistsError(f"{cut_dir} already exists — cuts are append-only")
    cut_dir.mkdir(parents=True, exist_ok=True)
    trace = _trace_args(project, project_dir)
    manifest = build_manifest(project, project_dir, cut_dir, cut_id, kernel=kernel, trace=trace)

    dry_steps, plan, meta = build_dry_script(manifest)
    _write_jsonl(cut_dir / "dry.jsonl", dry_steps)
    learned = check_dry_run(manifest, harness_run.filmcraft_run(None, cut_dir / "dry.jsonl", **trace))
    _write_json(cut_dir / "ids.json", {"sequence": meta["sequence"], "matte": meta["matte"],
                                       "items": meta["items"], "placements":
                                       [{**p, "clips": c} for p, c in zip(plan, learned)]})

    script = build_cut_script(manifest, learned)
    _write_jsonl(cut_dir / "cut.jsonl", script)
    fcproj = Path(manifest["save_path"])
    rows = harness_run.filmcraft_run(None, cut_dir / "cut.jsonl", output_path=fcproj, **trace)
    real = [(r.get("result") or {}).get("clips") for r in rows[4:4 + len(plan)]]
    if real != learned:
        raise RuntimeError("clip ids differ from the dry run — FilmCraft id allocation changed")

    seq_text = harness_run.filmcraft_inspect(fcproj, "sequence", **trace)
    (cut_dir / "sequence.json").write_bytes(seq_text.encode("utf-8"))
    out = {"engine": "filmcraft", "cut_dir": str(cut_dir), "fcproj": str(fcproj),
           "script_sha256": _sha256(cut_dir / "cut.jsonl"),
           "sequence_sha256": _sha256(cut_dir / "sequence.json"),
           "filmcraft_version": harness_run.filmcraft_version(),
           "total_frames": meta["total_frames"], "fps": manifest["fps"],
           "scene_starts_frames": meta["starts"], "loudness_lufs": manifest["loudness_lufs"],
           "trace": {"project_id": trace["project_id"], "trace_dir": str(trace["trace_dir"])},
           "manifest": manifest}
    _write_json(cut_dir / "cut_meta.json", out)
    return out


def _meta(cut_dir: Path) -> dict:
    return json.loads((Path(cut_dir) / "cut_meta.json").read_text(encoding="utf-8"))


def _cut_trace(meta: dict) -> dict:
    return dict(meta["trace"])


def export(cut_dir: str | Path, preset: str = "master", loudness_lufs: float | None = None,
           out_name: str = "master.mp4") -> dict:
    """Export the cut through a named preset with explicit bitrate and loudness."""
    meta = _meta(cut_dir)
    settings = dict(EXPORT_PRESETS[preset])
    settings["loudnessLufs"] = loudness_lufs if loudness_lufs is not None else meta["loudness_lufs"]
    settings["path"] = str(Path(cut_dir) / out_name)
    return harness_run.filmcraft_export(meta["fcproj"], settings, **_cut_trace(meta))


def render_frames(cut_dir: str | Path, times: list[float] | None = None) -> list[str]:
    """QA frames: by default half a second into every scene (clamped inside the scene)."""
    meta = _meta(cut_dir)
    fps = meta["fps"]
    if times is None:
        starts = meta["scene_starts_frames"] + [meta["total_frames"]]
        times = [min(a / fps + 0.5, (a + (b - a) / 2) / fps) for a, b in zip(starts, starts[1:])]
    out = []
    for n, t in enumerate(times, 1):
        out.append(str(harness_run.filmcraft_render(meta["fcproj"], t, Path(cut_dir) / "frames" / f"scene_{n}.png",
                                                    **_cut_trace(meta))))
    return out


def interchange(cut_dir: str | Path, fmt: str = "fcp7xml") -> str:
    """Resolve hand-off: FCP7 XML (A7-verified) or OTIO."""
    meta = _meta(cut_dir)
    cmd, ext = {"fcp7xml": ("file.exportFcp7Xml", "xml"), "otio": ("file.exportOtio", "otio")}[fmt]
    out = Path(cut_dir) / f"{Path(meta['fcproj']).stem}.{ext}"
    script = Path(cut_dir) / f"interchange_{fmt}.jsonl"
    _write_jsonl(script, [{"id": cmd, "params": {"path": str(out)}}])
    harness_run.filmcraft_run(meta["fcproj"], script, output_path=out, **_cut_trace(meta))
    return str(out)
