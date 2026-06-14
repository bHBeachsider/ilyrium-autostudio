"""The style block must be PREPENDED (load-bearing on Flux/SDXL); the bare trigger is
not load-bearing (validated 2026-06-14 on the Broderick hands). Avatar description is
injected only for character panels."""
import json
from satirist.render import compose_prompt
from satirist.config import load_style_block


def test_prepends_style_block_before_image_prompt():
    out = compose_prompt("a man on the phone", style_block="ink comic, cross-hatching")
    assert out == "ink comic, cross-hatching, a man on the phone"


def test_injects_avatar_desc_between_style_and_scene_for_character_panel():
    out = compose_prompt("pointing angrily", style_block="ink comic",
                         avatar_desc="a bald bearded man with glasses")
    assert out == "ink comic, a bald bearded man with glasses, pointing angrily"
    assert out.index("ink comic") < out.index("bald") < out.index("pointing")


def test_skips_avatar_when_none():
    out = compose_prompt("a dog", style_block="ink comic")
    assert out == "ink comic, a dog"
    assert "None" not in out


def test_appends_trigger_as_harmless_tail():
    out = compose_prompt("a dog", style_block="ink comic", trigger="brdrck")
    assert out == "ink comic, a dog, brdrck"


def test_skips_empty_parts():
    out = compose_prompt("a dog", style_block="", avatar_desc="  ", trigger="")
    assert out == "a dog"


def test_load_style_block_reads_look_field(tmp_path):
    p = tmp_path / "style_kernel.json"
    p.write_text(json.dumps({"look": "bold confident ink linework", "register": "deadpan"}))
    assert load_style_block(str(p)) == "bold confident ink linework"
