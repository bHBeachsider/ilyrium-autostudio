"""FilmCraft edit engine (Phase 1): pure script generation, the producer dispatch, the lint
rule, and — only when FILMCRAFT_CLI is set — an end-to-end 3-clip cut through
producer.assemble_cut(engine="filmcraft") plus the Phase 0 golden-set upgrade regression.
"""
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = REPO_ROOT / "apps" / "auto-studio"
for p in (str(REPO_ROOT), str(APP_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import lint_no_raw_sdk as lint  # noqa: E402
from harness import run as hrun  # noqa: E402
from media import filmcraft_assembler as fa  # noqa: E402

TPF24 = 10_584_000_000  # ticks per frame at 24 fps
HAS_CLI = bool(os.environ.get("FILMCRAFT_CLI"))
needs_cli = pytest.mark.skipif(not HAS_CLI, reason="FILMCRAFT_CLI not set")
GOLDEN = REPO_ROOT / "tests" / "fixtures" / "filmcraft_bakeoff"


def _manifest(**over):
    m = {
        "name": "cut_t", "width": 1920, "height": 1080, "fps": 24.0, "sample_rate": 48000,
        "pillarbox": "#ffffff", "save_path": "C:/tmp/cut_t.fcproj",
        "levels": fa.levels({}),
        "shots": [
            {"scene": 1, "video": "a.mp4", "video_frames": 122, "has_audio": False,
             "vo": "a.mp3", "vo_frames": 136, "shot_frames": 136, "title": "one"},
            {"scene": 2, "video": "b.mp4", "video_frames": 121, "has_audio": True,
             "vo": "b.mp3", "vo_frames": 395, "shot_frames": 395, "title": "two"},
        ],
        "music": {"path": "bed.mp3", "frames": 400},
    }
    m.update(over)
    return m


def _fake_learned(manifest):
    _, plan, _ = fa.build_dry_script(manifest)
    nxt, out = 100, []
    for p in plan:
        if p["role"] == "take" and p["has_audio"]:
            out.append([nxt, nxt + 1])
            nxt += 3
        else:
            out.append([nxt])
            nxt += 2
    return out


# --------------------------------------------------------------------------- #
# Pure: frame math, settings, levels
# --------------------------------------------------------------------------- #
def test_frame_math():
    assert fa.frames_to_ticks(1, 24) == TPF24
    assert fa.frames_to_ticks(1, 23.976) == 10_594_584_000
    assert fa.to_frames(int(5.0625 * 254_016_000_000), 24) == 122   # 121.5 -> 122 (half up)
    assert fa.to_frames(1_440_270_720_000, 24) == 136               # 5.670 s VO
    assert fa.to_frames(2_522_378_880_000, 24) == 238               # 9.930 s VO


def test_levels_mapping_nothing_applied_twice():
    assert fa.levels({}) == {"native_gain_db": -9.12, "bed_trim_db": fa.BED_TRIM_DB,
                             "bed_duck_db": fa.BED_DUCK_DB, "duck_fade_s": fa.DUCK_FADE_S}
    assert fa.BED_TRIM_DB == -10.0 and fa.BED_DUCK_DB == -12.0 and fa.DUCK_FADE_S == 0.8
    lv = fa.levels({"music_gain": 0.15, "audio_duck": 0.5})
    assert lv["bed_trim_db"] == -16.48 and lv["native_gain_db"] == -6.02


def test_sequence_settings_kernel_and_aspect():
    s = fa.sequence_settings({}, None)
    assert (s["width"], s["height"], s["fps"], s["pillarbox"]) == (1920, 1080, 24.0, "#000000")
    s = fa.sequence_settings({"aspect_ratio": "9:16"}, {"delivery": {"pillarbox": "#ffffff"}})
    assert (s["width"], s["height"], s["pillarbox"]) == (1080, 1920, "#ffffff")


def test_9_16_canvas_is_portrait_letterbox():
    s = fa.sequence_settings({"aspect_ratio": "9:16"}, None)
    assert s["width"] == 1080 and s["height"] == 1920
    assert s["matte_style"] == "letterbox"
    s16 = fa.sequence_settings({"aspect_ratio": "16:9"}, None)
    assert s16["matte_style"] == "pillarbox"


# --------------------------------------------------------------------------- #
# Pure: script generation
# --------------------------------------------------------------------------- #
def test_dry_script_layout_and_loop_fill():
    m = _manifest()
    steps, plan, meta = fa.build_dry_script(m)
    assert [s["id"] for s in steps[:4]] == ["file.newProject", "file.import", "file.newSequence",
                                            "file.newColorMatte"]
    assert steps[1]["params"]["paths"] == ["a.mp4", "b.mp4", "a.mp3", "b.mp3", "bed.mp3"]
    assert meta["sequence"] == 12 and meta["matte"] == 13            # 7 + items, then the matte
    assert steps[3]["params"]["color"] == "#ffffff"
    places = steps[4:]
    assert places[0]["params"] == {"item": 13, "track": "V1", "frame": 0,
                                   "duration": 531 * TPF24, "audio": False}
    takes = [p["params"] for p, r in zip(places, plan) if r["role"] == "take"]
    # shot 1: one copy at 0 (136 frames needs 122 + 14); shot 2: 121*3 + 32 = 395 from frame 136
    assert [(t["item"], t["frame"], t.get("duration")) for t in takes] == [
        (1, 0, None), (1, 122, 14 * TPF24),
        (2, 136, None), (2, 257, None), (2, 378, None), (2, 499, 32 * TPF24)]
    assert all(t["track"] == "V2" for t in takes)
    assert takes[0]["audio"] is False and takes[2]["audioTrack"] == "A1"
    vo = [p["params"] for p, r in zip(places, plan) if r["role"] == "vo"]
    assert [(v["item"], v["frame"]) for v in vo] == [(3, 0), (4, 136)]
    bed = [p["params"] for p, r in zip(places, plan) if r["role"] == "music"]
    assert [(b["frame"], b.get("duration")) for b in bed] == [(0, None), (400, 131 * TPF24)]
    assert meta["starts"] == [0, 136] and meta["total_frames"] == 531


def test_cut_script_tail():
    m = _manifest()
    learned = _fake_learned(m)
    script = fa.build_cut_script(m, learned)
    ids = [s["id"] for s in script]
    assert ids[-1] == "file.saveAs" and script[-1]["params"]["path"] == m["save_path"]
    fit = next(s for s in script if s["id"] == "clip.fitToFrame")["params"]["clips"]
    assert len(fit) == 6
    duck = next(s for s in script if s["id"] == "essentialSound.set")["params"]["values"]
    assert duck == {"ducking.enabled": True, "ducking.reduceDb": -12.0, "ducking.fadeS": 0.8}
    assert ids.index("essentialSound.generateDucking") > ids.index("essentialSound.set")
    markers = [s["params"] for s in script if s["id"] == "markers.add"]
    assert [mk["time"] for mk in markers] == [0, 136 * TPF24]       # frame-quantised
    assert all(mk["time"] % TPF24 == 0 for mk in markers)
    gains = [s["params"]["db"] for s in script if s["id"] == "clip.audioGain"]
    assert gains == [-9.12, -10.0]                                  # native, bed — once each
    assert fa.build_cut_script(m, learned) == script                # pure + deterministic


def test_cut_script_without_vo_or_music_skips_audio_steps():
    m = _manifest(music=None)
    for s in m["shots"]:
        s.update(vo=None, vo_frames=0, shot_frames=s["video_frames"])
    ids = [s["id"] for s in fa.build_cut_script(m, _fake_learned(m))]
    assert "essentialSound.generateDucking" not in ids
    assert "essentialSound.setType" not in ids


def test_check_dry_run_rejects_id_drift():
    m = _manifest()
    steps, plan, meta = fa.build_dry_script(m)
    rows = [{"ok": True, "result": None},
            {"ok": True, "result": {"items": [1, 2, 3, 4, 5]}},
            {"ok": True, "result": {"sequence": 12}},
            {"ok": True, "result": {"item": 13}}] + [
        {"ok": True, "result": {"clips": c}} for c in _fake_learned(m)]
    assert fa.check_dry_run(m, rows) == _fake_learned(m)
    rows[2] = {"ok": True, "result": {"sequence": 99}}
    with pytest.raises(RuntimeError, match="sequence id"):
        fa.check_dry_run(m, rows)


def test_image_sequence_detection(tmp_path):
    seq = tmp_path / "beauty"
    seq.mkdir()
    for n in (1001, 1002):
        (seq / f"beauty.{n:04d}.png").write_bytes(b"")
    pattern, start = fa._image_sequence(seq)
    assert pattern.endswith("beauty.%04d.png") and start == 1001
    assert fa._image_sequence(tmp_path / "clip.mp4") is None


def test_missing_cli_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("FILMCRAFT_CLI", raising=False)
    with pytest.raises(RuntimeError, match="FILMCRAFT_CLI not set"):
        hrun.filmcraft_cli()
    monkeypatch.setenv("FILMCRAFT_CLI", "filmcraft-cli.exe")      # bare name: never via PATH
    with pytest.raises(RuntimeError, match="not an absolute path"):
        hrun.filmcraft_cli()


# --------------------------------------------------------------------------- #
# Producer dispatch + lint rule
# --------------------------------------------------------------------------- #
def test_dispatch_defaults_to_moviepy(monkeypatch):
    import producer
    calls = []
    monkeypatch.setattr(producer, "_assemble_cut_moviepy", lambda *a, **k: calls.append("moviepy") or {})
    monkeypatch.setattr(producer, "_assemble_cut_filmcraft", lambda *a, **k: calls.append("filmcraft") or {})
    monkeypatch.delenv("ILYRIUM_EDIT_ENGINE", raising=False)
    producer.assemble_cut({}, "x")
    monkeypatch.setenv("ILYRIUM_EDIT_ENGINE", "filmcraft")
    producer.assemble_cut({}, "x")
    producer.assemble_cut({}, "x", engine="moviepy")
    assert calls == ["moviepy", "filmcraft", "moviepy"]
    with pytest.raises(ValueError):
        producer.assemble_cut({}, "x", engine="premiere")


def test_lint_forbids_direct_filmcraft_calls(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("import sub" + "process\nsub" + "process.run(['filmcraft" + "-cli', 'run'])\n",
                   encoding="utf-8")
    assert any("filmcraft" in v for v in lint.check_file(bad))
    ok = tmp_path / "ok.py"
    ok.write_text("import os\nCLI = os.environ.get('FILMCRAFT" + "_CLI')\n", encoding="utf-8")
    assert lint.check_file(ok) == []


# --------------------------------------------------------------------------- #
# Integration (binary required)
# --------------------------------------------------------------------------- #
def _demo_clip(scene: str, out_dir: Path, prep_traces: Path) -> Path:
    out = out_dir / f"{scene}.mp4"
    script = out_dir / f"make_{scene}.jsonl"
    fa._write_jsonl(script, [
        {"id": "file.newProject", "params": {"name": scene}},
        {"id": "file.importDemoFootage", "params": {"scene": scene}},
        {"id": "file.newSequence", "params": {"name": scene, "width": 640, "height": 360, "fps": 24,
                                              "sampleRate": 48000}},
        {"id": "timeline.place", "params": {"item": 1, "track": "V1", "frame": 0}},
        {"id": "file.exportMedia", "params": {"path": str(out), "format": "h264", "hardwareEncoding": "off",
                                              "bitrateMode": "crf", "crf": 23, "range": "custom",
                                              "startSeconds": 0, "endSeconds": 1, "wait": True}},
    ])
    hrun.filmcraft_run(None, script, project_id="demo_prep", trace_dir=prep_traces)
    return out


@needs_cli
def test_demo_three_clip_cut_end_to_end(tmp_path, monkeypatch):
    import producer
    import project_store as ps
    media = tmp_path / "media"
    media.mkdir()
    clips = [_demo_clip(s, media, tmp_path / "prep") for s in ("Dunes", "Forest", "CityNight")]
    proj_dir = tmp_path / "campaign"
    proj_dir.mkdir()
    project = {"campaign_id": "fc_demo", "cuts": [], "style_kernel": {"delivery": {"pillarbox": "#ffffff"}},
               "shots": [{"scene_number": i + 1, "visual_prompt": f"demo {c.stem}", "selected_take": "take_1",
                          "takes": [{"take_id": "take_1", "video": str(c), "audio": None}]}
                         for i, c in enumerate(clips)]}
    monkeypatch.setenv("ILYRIUM_EDIT_ENGINE", "filmcraft")
    res = producer.assemble_cut(project, str(proj_dir), upload_to_r2=False)

    assert res["cut_id"] == "cut_1" and Path(res["final_video"]).is_file()
    cut = json.loads((proj_dir / "project.json").read_text(encoding="utf-8"))["cuts"][-1]
    assert cut["engine"] == "filmcraft" and cut["filmcraft_version"].startswith("filmcraft-cli")
    for k in ("fcproj", "script_sha256", "sequence_sha256", "export_sha256"):
        assert cut[k]
    cut_dir = proj_dir / "cuts" / "cut_1"
    for f in ("dry.jsonl", "ids.json", "cut.jsonl", "cut_1.fcproj", "sequence.json", "cut_meta.json",
              "master.mp4", "cut_1.xml"):
        assert (cut_dir / f).is_file(), f
    assert len(list((cut_dir / "frames").glob("*.png"))) == 3
    seq = json.loads((cut_dir / "sequence.json").read_text(encoding="utf-8"))
    v2 = seq["video"][1]["items"]
    assert [c["name"] for c in v2] == ["Dunes.mp4", "Forest.mp4", "CityNight.mp4"]
    assert all(a["endFrame"] == b["startFrame"] for a, b in zip(v2, v2[1:]))
    assert seq["video"][0]["items"][0]["endFrame"] == seq["durationFrames"] == 72
    # one trace row per binary call: 3 probes, dry run, run, inspect, export, 3 renders, xml
    rows = [json.loads(ln) for ln in (proj_dir / "traces" / "traces.jsonl").read_text(encoding="utf-8").splitlines()]
    fc_rows = [r for r in rows if r["model"] == "filmcraft-cli"]
    assert len(fc_rows) == 11
    assert all(r["tool_calls"][0]["recorded_response"]["exit_code"] == 0 for r in fc_rows)
    assert all(r["tool_calls"][0]["recorded_response"]["filmcraft_version"] for r in fc_rows)
    # determinism: a second cut of the same project yields the same edit decision
    built2 = fa.assemble(project, proj_dir, "cut_2", kernel=project["style_kernel"])
    s1 = (cut_dir / "sequence.json").read_text(encoding="utf-8").replace('"cut_1"', '"CUT"')
    s2 = (Path(built2["cut_dir"]) / "sequence.json").read_text(encoding="utf-8").replace('"cut_2"', '"CUT"')
    assert s1 == s2
    assert ps.latest_cut(json.loads((proj_dir / "project.json").read_text(encoding="utf-8")))["cut_id"] == "cut_1"


@needs_cli
def test_golden_bakeoff_sequence_is_stable(tmp_path):
    """Upgrade regression: replaying the Phase 0 cut.jsonl must reproduce its sequence.json and
    .fcproj byte for byte. Skips if the Kingsize CH 69 media is not on this machine."""
    steps = [json.loads(ln) for ln in (GOLDEN / "cut.jsonl").read_text(encoding="utf-8").splitlines()]
    media = steps[1]["params"]["paths"]
    if not all(Path(p).is_file() for p in media):
        pytest.skip("Phase 0 media not on this machine")
    steps[-1]["params"]["path"] = str(tmp_path / "cut_4.fcproj")
    script = tmp_path / "cut.jsonl"
    fa._write_jsonl(script, steps)
    hrun.filmcraft_run(None, script, project_id="golden", trace_dir=tmp_path)
    seq = hrun.filmcraft_inspect(tmp_path / "cut_4.fcproj", project_id="golden", trace_dir=tmp_path)
    assert json.loads(seq) == json.loads((GOLDEN / "sequence.json").read_text(encoding="utf-8"))
    assert (tmp_path / "cut_4.fcproj").read_bytes() == (GOLDEN / "cut_4.fcproj").read_bytes()
