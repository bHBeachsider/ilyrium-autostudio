from films.woods_of_west import keyframes, characters


def test_prompt_includes_style_aspect_and_visual():
    shot = {"id": 8, "visual": "wide two-shot down the street", "characters": ["cal", "pringle"]}
    p = keyframes.compose_keyframe_prompt(shot, "ballpoint")
    assert "ballpoint" in p
    assert "16:9" in p
    assert "wide two-shot down the street" in p
    assert "Cal Dalton" in p and "Sheriff Pringle" in p   # character looks injected


def test_prompt_handles_empty_cast():
    shot = {"id": 6, "visual": "empty dusty main street", "characters": []}
    p = keyframes.compose_keyframe_prompt(shot, "cinematic")
    assert "empty dusty main street" in p
    assert "on-model" not in p                              # no character clause when cast is empty


def test_keyframe_seeds_establishing_shot_from_first_sheet(monkeypatch):
    captured = {}

    def fake_edit(prompt, images, out_path, **k):
        captured.update(prompt=prompt, images=images, out_path=out_path)
        return [out_path]

    monkeypatch.setattr(keyframes, "edit_image_fal", fake_edit)
    shot = {"id": 6, "visual": "empty dusty main street", "characters": []}
    refs = {"shakes": "s.png", "pringle": "p.png", "cal": "c.png"}
    out = keyframes.generate_shot_keyframe(shot, "cartoon", refs, "/tmp/kf")
    assert captured["images"] == ["s.png"]                  # falls back to first available sheet
    assert out.endswith("shot6_keyframe.png")


def test_keyframe_uses_only_in_frame_character_refs(monkeypatch):
    captured = {}
    monkeypatch.setattr(keyframes, "edit_image_fal",
                        lambda prompt, images, out_path, **k: captured.update(images=images) or [out_path])
    shot = {"id": 12, "visual": "close-up of Cal", "characters": ["cal"]}
    refs = {"shakes": "s.png", "pringle": "p.png", "cal": "c.png"}
    keyframes.generate_shot_keyframe(shot, "cartoon", refs, "/tmp/kf")
    assert captured["images"] == ["c.png"]                  # only Cal's ref, not all three


def test_build_character_sheets_generates_all_three(monkeypatch):
    seen = {}

    def fake_gen(prompt, out_path, **k):
        seen[out_path] = prompt
        return out_path

    monkeypatch.setattr(characters, "_generate_still", fake_gen)
    refs = characters.build_character_sheets("ballpoint", "/tmp/chars")
    assert set(refs) == {"shakes", "pringle", "cal"}
    # each sheet prompt carries the style and that character's look text
    assert any("ballpoint" in p and "Cal Dalton" in p for p in seen.values())


def test_keyframe_reuses_existing_file(monkeypatch, tmp_path):
    # An existing keyframe must be reused, not regenerated (no Fal call).
    (tmp_path / "shot8_keyframe.png").write_bytes(b"x")
    calls = []
    monkeypatch.setattr(keyframes, "edit_image_fal", lambda *a, **k: calls.append(1) or ["x"])
    out = keyframes.generate_shot_keyframe({"id": 8, "visual": "v", "characters": ["cal"]},
                                           "cartoon", {"cal": "c.png"}, str(tmp_path))
    assert out.endswith("shot8_keyframe.png")
    assert calls == []   # reused, Fal not called


def test_edit_with_timeout_raises_on_hang(monkeypatch):
    import time
    monkeypatch.setattr(keyframes, "edit_image_fal",
                        lambda *a, **k: time.sleep(5) or ["x.png"])
    import pytest as _pt
    with _pt.raises(TimeoutError):
        keyframes._edit_with_timeout("p", ["r.png"], "out.png", timeout=0.3)


def test_edit_with_timeout_propagates_error(monkeypatch):
    def boom(*a, **k):
        raise ValueError("fal said no")
    monkeypatch.setattr(keyframes, "edit_image_fal", boom)
    import pytest as _pt
    with _pt.raises(ValueError, match="fal said no"):
        keyframes._edit_with_timeout("p", ["r.png"], "out.png", timeout=5)


def test_build_character_sheets_reuses_existing(monkeypatch, tmp_path):
    # A pre-existing sheet must be reused (not regenerated) for consistency + cost.
    (tmp_path / "cal_sheet.png").write_bytes(b"x")
    gen_calls = []
    monkeypatch.setattr(characters, "_generate_still",
                        lambda prompt, out_path, **k: gen_calls.append(out_path) or out_path)
    refs = characters.build_character_sheets("cartoon", str(tmp_path))
    assert refs["cal"].endswith("cal_sheet.png")
    assert not any("cal_sheet" in c for c in gen_calls)      # cal reused, not regenerated
    assert any("shakes_sheet" in c for c in gen_calls)        # others still generated
