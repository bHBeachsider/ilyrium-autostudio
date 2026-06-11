import json
from PIL import Image
from satirist.caption import derive_caption, compose_caption_banner, save_artifact


def test_derive_caption_first_sentence_truncated():
    text = "Boss Tweed loots the city treasury. Then he flees to Spain."
    cap = derive_caption(text)
    assert cap == "Boss Tweed loots the city treasury."


def test_derive_caption_truncates_long_single_sentence():
    cap = derive_caption("x" * 300)
    assert len(cap) <= 160


def test_compose_adds_banner_below_image():
    img = Image.new("RGB", (64, 48), "white")
    out = compose_caption_banner(img, "A caption")
    assert out.width == 64
    assert out.height > 48           # banner added below
    assert out.mode == "RGB"


def test_save_artifact_writes_png_and_sidecar(tmp_path):
    img = Image.new("RGB", (32, 32), "white")
    meta = {"topic": "Tammany", "allegory_rationale": "a", "image_prompt": "b",
            "caption": "c", "signal": {"summary": "s"}}
    png = save_artifact(img, meta, str(tmp_path), "tammany_001")
    assert png.endswith("tammany_001.png")
    sidecar = png[:-4] + ".json"
    saved = json.loads(open(sidecar, encoding="utf-8").read())
    assert saved["topic"] == "Tammany"
    assert saved["caption"] == "c"
