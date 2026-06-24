import os
from films.woods_of_west import sfx, render_film


def test_sfx_cues_cover_cold_open_train():
    # The 4:55 train cold-open must have SFX (the user-reported gap).
    assert 1 in sfx.SFX_CUES and "train" in sfx.SFX_CUES[1].lower()
    assert 2 in sfx.SFX_CUES
    # dialogue shots must NOT have SFX cues (they keep their voiceover)
    for spoken in (4, 5, 8, 9, 10, 11, 12, 13):
        assert spoken not in sfx.SFX_CUES


def test_render_shot_sfx_none_without_cue(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "x")
    assert sfx.render_shot_sfx(99, "/tmp/sfx") is None      # no cue -> None


def test_render_shot_sfx_none_without_key(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert sfx.render_shot_sfx(1, "/tmp/sfx") is None       # no key -> None, never raises


def test_pick_shot_audio_dialogue_for_spoken(tmp_path):
    (tmp_path / "shot4.mp3").write_bytes(b"x")
    shot = {"id": 4, "line": "Sheriff!!"}
    out = render_film.pick_shot_audio(shot, str(tmp_path), {4: "should_not_use.mp3"})
    assert out == str(tmp_path / "shot4.mp3")               # dialogue wins for spoken shots


def test_pick_shot_audio_sfx_for_silent(tmp_path):
    shot = {"id": 1, "line": None}
    out = render_film.pick_shot_audio(shot, str(tmp_path), {1: "train.mp3"})
    assert out == "train.mp3"                               # silent shot -> SFX bed


def test_pick_shot_audio_none_when_nothing(tmp_path):
    shot = {"id": 16, "line": None}
    assert render_film.pick_shot_audio(shot, str(tmp_path), {}) is None
