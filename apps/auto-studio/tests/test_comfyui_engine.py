"""Offline unit tests for media/comfyui_engine.py — no box, no HTTP.

Run from apps/auto-studio:  venv/Scripts/python -m pytest tests -q
"""
import json
import os

import pytest

from media import comfyui_engine as ce


ZIMAGE = ce.load_model("zimage")
RECIPE = ZIMAGE["recipe"]


# --------------------------------------------------------------------------- #
# registry
# --------------------------------------------------------------------------- #
def test_registry_has_the_three_models():
    ids = ce.available_model_ids()
    for want in ("zimage", "flux2", "flux2-klein-9b-uncensored"):
        assert want in ids


def test_load_model_accepts_prefixed_id():
    assert ce.load_model("comfyui:flux2")["id"] == "comfyui:flux2"


def test_load_model_unknown_raises_clear_error():
    with pytest.raises(ValueError, match="Unknown ComfyUI model 'comfyui:bogus'"):
        ce.load_model("comfyui:bogus")


# --------------------------------------------------------------------------- #
# build_graph — txt2img / img2img / inpaint / region
# --------------------------------------------------------------------------- #
def test_build_graph_txt2img():
    wf = ce.build_graph("zimage", "a red fox", seed=7, width=832, height=1216)
    assert wf["6"]["class_type"] == RECIPE["latent"]
    assert wf["6"]["inputs"] == {"width": 832, "height": 1216, "batch_size": 1}
    assert wf["1"]["inputs"]["unet_name"] == RECIPE["unet"]
    assert wf["2"]["inputs"] == {"clip_name": RECIPE["clip"], "type": RECIPE["clip_type"]}
    assert wf["4"]["inputs"]["text"] == "a red fox"
    ks = wf["7"]["inputs"]
    assert (ks["seed"], ks["steps"], ks["cfg"]) == (7, RECIPE["steps"], RECIPE["cfg"])
    assert ks["denoise"] == 0.65  # default arg; txt2img callers pass 1.0
    assert "10" not in wf and "12" not in wf


def test_build_graph_weight_dtype_from_recipe():
    wf = ce.build_graph("flux2-klein-9b-uncensored", "x", seed=1)
    assert wf["1"]["inputs"]["weight_dtype"] == "fp8_e4m3fn"
    wf2 = ce.build_graph("flux2", "x", seed=1)
    assert wf2["1"]["inputs"]["weight_dtype"] == "default"


def test_build_graph_img2img():
    wf = ce.build_graph("flux2", "watercolor", seed=3, img="ref.png", denoise=0.4)
    assert wf["10"]["class_type"] == "LoadImage"
    assert wf["10"]["inputs"]["image"] == "ref.png"
    assert wf["11"]["class_type"] == "ImageScale"
    assert wf["6"]["class_type"] == "VAEEncode"
    assert wf["6"]["inputs"]["pixels"] == ["11", 0]
    assert wf["7"]["inputs"]["denoise"] == 0.4
    assert "12" not in wf


def test_build_graph_inpaint_forces_full_denoise_inside_mask():
    wf = ce.build_graph("zimage", "add a hat", seed=3, img="ref.png",
                        mask="mask.png", denoise=0.4)
    assert wf["12"]["class_type"] == "LoadImageMask"
    assert wf["12"]["inputs"]["image"] == "mask.png"
    assert wf["6"]["class_type"] == "VAEEncodeForInpaint"
    assert wf["6"]["inputs"]["mask"] == ["12", 0]
    assert wf["7"]["inputs"]["denoise"] == 1.0  # mask limits the area instead


def test_build_graph_region_builds_mask(tmp_path, monkeypatch):
    # Point the "ComfyUI input dir" at a temp dir so the region mask lands there.
    monkeypatch.setattr(ce, "comfy_input_dir", lambda: str(tmp_path))
    wf = ce.build_graph("zimage", "recolor", seed=3, img="ref.png",
                        region="0.5,0.0,1.0,0.5", width=100, height=100)
    assert wf["6"]["class_type"] == "VAEEncodeForInpaint"
    assert wf["12"]["inputs"]["image"] == "region_mask.png"
    from PIL import Image
    m = Image.open(tmp_path / "region_mask.png")
    assert m.size == (100, 100)
    assert m.getpixel((75, 25)) == (255, 255, 255)   # inside the region: white
    assert m.getpixel((25, 75)) == (0, 0, 0)         # outside: black


def test_build_graph_random_seed_when_none():
    wf1 = ce.build_graph("zimage", "x")
    wf2 = ce.build_graph("zimage", "x")
    assert isinstance(wf1["7"]["inputs"]["seed"], int)
    assert wf1["7"]["inputs"]["seed"] != wf2["7"]["inputs"]["seed"]


# --------------------------------------------------------------------------- #
# template workflows + token injection
# --------------------------------------------------------------------------- #
def test_build_graph_template_workflow(tmp_path):
    entry = {"id": "comfyui:tpl",
             "workflow": "comfyui_workflows/flux2_klein_txt2img_api.json"}
    wf = ce.build_graph(entry, 'a "smug" sheriff', seed=99)
    assert wf["4"]["inputs"]["text"] == 'a "smug" sheriff'
    assert wf["7"]["inputs"]["seed"] == 99


def test_build_graph_template_rejects_img2img():
    entry = {"id": "comfyui:tpl",
             "workflow": "comfyui_workflows/flux2_klein_txt2img_api.json"}
    with pytest.raises(ValueError, match="recipe"):
        ce.build_graph(entry, "x", img="ref.png")


def test_inject_tokens_seed_and_image():
    wf = '{"a": {"inputs": {"text": "__PROMPT__", "image": "__IMAGE__", "seed": __SEED__}}}'
    out = json.loads(ce.inject_tokens(wf, 'p "q"', image_name="i.png", seed=5))
    assert out["a"]["inputs"] == {"text": 'p "q"', "image": "i.png", "seed": 5}


def test_make_region_mask_pixel_coords(tmp_path):
    p = ce.make_region_mask("10,10,20,20", 64, 64, save_dir=str(tmp_path))
    assert os.path.exists(p)


def test_make_region_mask_bad_spec(tmp_path):
    with pytest.raises(ValueError, match="x1,y1,x2,y2"):
        ce.make_region_mask("1,2,3", 64, 64, save_dir=str(tmp_path))


# --------------------------------------------------------------------------- #
# renderer wrappers keep their contract (import + raise, no fallback files)
# --------------------------------------------------------------------------- #
def test_renderer_wrappers_importable_and_raise(tmp_path):
    from media import comfyui_renderer as cr
    assert callable(cr.render_scene_comfyui)
    assert callable(cr.render_i2v_comfyui)
    assert callable(cr.upload_comfyui_image)
    with pytest.raises(RuntimeError, match="image"):
        cr.render_i2v_comfyui(str(tmp_path / "missing.png"), "prompt", 1)
    assert list(tmp_path.iterdir()) == []  # no fallback/sentinel files written
