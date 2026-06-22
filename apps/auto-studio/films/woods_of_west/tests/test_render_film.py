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
