import pytest
from satirist.judge import parse_verdict, should_revise, build_judge_prompt, NAST_RUBRIC


def test_parse_verdict_extracts_score_and_rationale():
    raw = 'Assessment: ```{"score": 4.2, "rationale": "strong allegory"}```'
    v = parse_verdict(raw)
    assert v["score"] == 4.2
    assert v["rationale"] == "strong allegory"


def test_parse_verdict_clamps_and_defaults_rationale():
    v = parse_verdict('{"score": 9}')          # out of 1-5 range -> clamped
    assert v["score"] == 5.0
    assert v["rationale"] == ""


def test_parse_verdict_raises_on_no_score():
    with pytest.raises(ValueError):
        parse_verdict("the cartoon is nice")


def test_should_revise_below_threshold():
    assert should_revise({"score": 3.0}, threshold=3.5) is True
    assert should_revise({"score": 3.5}, threshold=3.5) is False
    assert should_revise({"score": 4.9}, threshold=3.5) is False


def test_rubric_and_prompt_mention_allegory():
    assert "allegory" in NAST_RUBRIC.lower()
    p = build_judge_prompt({"allegory_rationale": "a tiger", "image_prompt": "b"})
    assert "a tiger" in p
    assert "score" in p.lower()
