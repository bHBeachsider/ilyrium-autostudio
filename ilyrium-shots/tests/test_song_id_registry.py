"""Guard tests for the song-ID ownership registry.

Regression cover for the 2026-09-01 finding: shot_spec.schema.json hardcoded the NH-
prefix, so KING SIZE was scaffolded as NH-S05 into the same flat shots/ directory as
NEW HARNOMY. These tests keep the two facts that prevent a repeat - the schema accepts
any claimed prefix, and the registry refuses to let one project write another's IDs.
"""

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import song_id_registry as sir  # noqa: E402


def test_schema_accepts_non_nh_prefixes():
    schema = json.load(open(os.path.join(ROOT, "shot_spec.schema.json"), encoding="utf-8"))
    assert schema["properties"]["song_id"]["pattern"] == r"^[A-Z]{2,4}-S[0-9]{2,}$"
    assert schema["properties"]["shot_id"]["pattern"] == r"^[A-Z]{2,4}-S[0-9]{2,}-SH[0-9]{3,}$"


@pytest.mark.parametrize("song_id,prefix", [
    ("NH-S101", "NH"), ("NH-S05", "NH"), ("KS-S01", "KS"), ("BR-S12", "BR"),
])
def test_parse_song_id(song_id, prefix):
    assert sir.parse_song_id(song_id)[0] == prefix


@pytest.mark.parametrize("bad", ["nh-S101", "NH-101", "NHS101", "TOOLONG-S01", "", None])
def test_parse_song_id_rejects_junk(bad):
    with pytest.raises(ValueError):
        sir.parse_song_id(bad)


def test_legacy_claim_beats_prefix_rule():
    """NH-S05 is KING SIZE's despite the NH prefix belonging to New Harnomy."""
    assert sir.owner_of("NH-S05") == "king_size"
    assert sir.owner_of("NH-S101") == "new_harnomy_usa"


def test_assert_owned_blocks_cross_project_write():
    sir.assert_owned("NH-S101", "new_harnomy_usa")
    with pytest.raises(sir.SongIdConflict):
        sir.assert_owned("NH-S05", "new_harnomy_usa")


def test_unclaimed_prefix_is_refused():
    with pytest.raises(sir.SongIdConflict):
        sir.owner_of("ZZ-S01")


def test_live_shots_dir_has_no_conflicts():
    problems, summary = sir.check()
    assert problems == [], problems
    assert summary, "expected at least one song ID in shots/"


def test_new_harnomy_specs_are_all_new_harnomy():
    problems, _ = sir.check(project="new_harnomy_usa")
    offenders = [p for p in problems if "NH-S101" in p or "NH-S348" in p]
    assert offenders == [], offenders
