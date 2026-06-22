import json
import pytest
from media import comfyui_renderer as cr


def test_inject_tokens_replaces_image_and_prompt():
    wf = '{"6": {"inputs": {"text": "__PROMPT__"}}, "52": {"inputs": {"image": "__IMAGE__"}}}'
    out = cr._inject_tokens(wf, visual_prompt='a "smug" sheriff', image_name="kf_01.png")
    parsed = json.loads(out)
    assert parsed["6"]["inputs"]["text"] == 'a "smug" sheriff'   # quotes survive JSON-safe inject
    assert parsed["52"]["inputs"]["image"] == "kf_01.png"


def test_inject_tokens_prompt_only_leaves_image_token():
    wf = '{"6": {"inputs": {"text": "__PROMPT__"}}, "52": {"inputs": {"image": "__IMAGE__"}}}'
    out = cr._inject_tokens(wf, visual_prompt="dusty street")
    parsed = json.loads(out)
    assert parsed["6"]["inputs"]["text"] == "dusty street"
    assert parsed["52"]["inputs"]["image"] == "__IMAGE__"   # untouched when no image given


def test_render_i2v_requires_image_file(tmp_path):
    with pytest.raises(RuntimeError, match="image"):
        cr.render_i2v_comfyui(str(tmp_path / "missing.png"), "prompt", 1)


def test_text_and_i2v_render_callable():
    # The text path must survive the refactor; both entry points exist.
    assert callable(cr.render_scene_comfyui)
    assert callable(cr.render_i2v_comfyui)
