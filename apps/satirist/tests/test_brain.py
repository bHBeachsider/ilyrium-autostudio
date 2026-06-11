import pytest
from satirist.brain import parse_brain_output, build_prompt


def test_parse_plain_json():
    raw = '{"allegory_rationale": "Tweed as a bloated tiger", "image_prompt": "a tiger labeled TAMMANY"}'
    out = parse_brain_output(raw)
    assert out["allegory_rationale"].startswith("Tweed")
    assert out["image_prompt"] == "a tiger labeled TAMMANY"


def test_parse_strips_markdown_fences_and_prose():
    raw = "Here you go:\n```json\n{\"allegory_rationale\":\"a\",\"image_prompt\":\"b\"}\n```\nHope that helps!"
    out = parse_brain_output(raw)
    assert out == {"allegory_rationale": "a", "image_prompt": "b"}


def test_parse_raises_on_no_json():
    with pytest.raises(ValueError):
        parse_brain_output("no json here at all")


def test_parse_raises_on_missing_required_key():
    with pytest.raises(ValueError):
        parse_brain_output('{"allegory_rationale": "a"}')  # image_prompt missing


def test_build_prompt_includes_event_and_revise_hint():
    p = build_prompt("Boss Tweed loots the city.", revise_hint="make the tiger angrier")
    assert "Boss Tweed loots the city." in p
    assert "make the tiger angrier" in p
