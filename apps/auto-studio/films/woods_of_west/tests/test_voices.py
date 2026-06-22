from films.woods_of_west import voices


def test_cast_covers_all_speakers():
    from films.woods_of_west import script
    speakers = {sh["speaker"] for sh in script.SHOTS if sh["speaker"]}
    assert speakers <= set(voices.VOICE_CAST)


def test_silent_shot_returns_none(monkeypatch):
    called = {"n": 0}
    monkeypatch.setattr(voices, "render_voiceover", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or "x.mp3")
    out = voices.render_shot_dialogue({"id": 6, "speaker": None, "line": None}, "/tmp")
    assert out is None and called["n"] == 0


def test_spoken_shot_calls_tts_with_cast(monkeypatch):
    captured = {}

    def fake(text, scene_number, output_dir, output_name=None, voice_id=None, **k):
        captured.update(text=text, voice_id=voice_id, output_name=output_name,
                        stability=k.get("stability"), similarity=k.get("similarity"))
        return f"{output_dir}/{output_name}"

    monkeypatch.setattr(voices, "render_voiceover", fake)
    shot = {"id": 13, "speaker": "pringle", "line": "You wouldn't shoot a man with serious wood..."}
    out = voices.render_shot_dialogue(shot, "/tmp/aud")
    assert captured["text"].startswith("You wouldn't shoot")
    assert captured["voice_id"] == voices.VOICE_CAST["pringle"]["voice_id"]
    assert captured["stability"] == voices.VOICE_CAST["pringle"]["stability"]
    assert out.endswith("shot13.mp3")
