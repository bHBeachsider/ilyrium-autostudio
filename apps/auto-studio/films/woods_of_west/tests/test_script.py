import pytest
from films.woods_of_west import script as s


def test_dialogue_is_verbatim():
    lines = {sh["line"] for sh in s.SHOTS if sh["line"]}
    assert "You wouldn't shoot a man with serious wood..." in lines
    assert "Sheriff Pringle... well well..." in lines
    assert "Oh yeah? Why's that?" in lines


def test_phases_partition():
    bake = s.shots_for_phase("bakeoff")
    film = s.shots_for_phase("film")
    assert all(sh["phase"] == "bakeoff" for sh in bake)
    assert len(bake) >= 2                      # signature beat is 2-3 shots
    assert len(film) > len(bake)               # full film is the superset
    assert {sh["id"] for sh in bake} <= {sh["id"] for sh in film}


def test_unknown_phase_raises():
    with pytest.raises(ValueError):
        s.shots_for_phase("nope")


def test_three_styles_present():
    assert set(s.STYLES) == {"ballpoint", "cartoon", "cinematic"}
    assert s.style_prefix("cartoon")
    with pytest.raises(KeyError):
        s.style_prefix("nope")


def test_every_shot_has_required_fields():
    for sh in s.SHOTS:
        assert set(sh) >= {"id", "beat", "phase", "speaker", "line", "characters", "visual", "motion"}
        assert sh["phase"] in {"film", "bakeoff"}
        assert all(c in s.CHARACTERS for c in sh["characters"])
        if sh["line"]:
            assert sh["speaker"] in s.CHARACTERS   # every spoken line has a known speaker
