from films.woods_of_west import render_film


def test_build_media_list_pairs_clip_and_audio(tmp_path):
    shots = [{"id": 1, "line": None}, {"id": 13, "line": "x"}]
    ml = render_film.build_media_list(
        shots, str(tmp_path), str(tmp_path), str(tmp_path),
        render_clip=lambda sh: f"clip{sh['id']}.mp4",
        render_audio=lambda sh: (f"aud{sh['id']}.mp3" if sh["line"] else None),
    )
    assert ml == [
        {"scene_number": 1, "video": "clip1.mp4", "audio": None},
        {"scene_number": 13, "video": "clip13.mp4", "audio": "aud13.mp3"},
    ]


def test_build_media_list_skips_failed_clip(tmp_path):
    shots = [{"id": 1, "line": None}, {"id": 2, "line": None}]
    ml = render_film.build_media_list(
        shots, str(tmp_path), str(tmp_path), str(tmp_path),
        render_clip=lambda sh: None if sh["id"] == 1 else "clip2.mp4",
        render_audio=lambda sh: None,
    )
    assert [m["scene_number"] for m in ml] == [2]


def test_build_media_list_skips_audio_call_when_clip_fails(tmp_path):
    audio_calls = []
    render_film.build_media_list(
        [{"id": 1, "line": "x"}], str(tmp_path), str(tmp_path), str(tmp_path),
        render_clip=lambda sh: None,
        render_audio=lambda sh: audio_calls.append(sh["id"]),
    )
    assert audio_calls == []   # no clip -> don't waste a TTS call


def _boom(*a, **k):
    raise RuntimeError("provider down")


def test_render_shot_clip_skips_on_keyframe_failure(monkeypatch):
    # A Fal keyframe failure must NOT abort the run — it returns None (shot skipped).
    monkeypatch.setattr(render_film.keyframes, "generate_shot_keyframe", _boom)
    out = render_film.render_shot_clip({"id": 5, "motion": "x"}, "cartoon",
                                       {"cal": "c.png"}, "/tmp/kf", "/tmp/clip")
    assert out is None


def test_render_shot_clip_skips_on_i2v_failure(monkeypatch):
    # Keyframe succeeds, i2v fails -> still None, not an exception.
    monkeypatch.setattr(render_film.keyframes, "generate_shot_keyframe",
                        lambda *a, **k: "kf.png")
    monkeypatch.setattr(render_film, "render_i2v_comfyui", _boom)
    out = render_film.render_shot_clip({"id": 5, "motion": "x"}, "cartoon",
                                       {"cal": "c.png"}, "/tmp/kf", "/tmp/clip")
    assert out is None


def test_render_shot_clip_returns_path_on_success(monkeypatch):
    monkeypatch.setattr(render_film.keyframes, "generate_shot_keyframe",
                        lambda *a, **k: "kf.png")
    monkeypatch.setattr(render_film, "render_i2v_comfyui",
                        lambda image_path, motion, sid, **k: f"clip{sid}.mp4")
    out = render_film.render_shot_clip({"id": 7, "motion": "pan"}, "cartoon",
                                       {"cal": "c.png"}, "/tmp/kf", "/tmp/clip")
    assert out == "clip7.mp4"


def test_render_shot_audio_swallows_tts_failure(monkeypatch):
    # An ElevenLabs error (e.g. 401) must NOT abort the render — degrade to silent.
    monkeypatch.setattr(render_film.voices, "render_shot_dialogue", _boom)
    out = render_film.render_shot_audio({"id": 13, "line": "x"}, "/tmp/aud")
    assert out is None


def test_render_shot_audio_passes_through_path(monkeypatch):
    monkeypatch.setattr(render_film.voices, "render_shot_dialogue",
                        lambda shot, d: f"{d}/shot{shot['id']}.mp3")
    out = render_film.render_shot_audio({"id": 13, "line": "x"}, "/tmp/aud")
    assert out == "/tmp/aud/shot13.mp3"
