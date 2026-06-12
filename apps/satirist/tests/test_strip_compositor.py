from PIL import Image
from satirist.strip_compositor import (
    choose_layout, parse_lettering, find_whitespace_slot, compose_strip, letter_panel)


def test_choose_layout():
    assert choose_layout(1) == (1, 1)
    assert choose_layout(4) == (2, 2)
    assert choose_layout(6) == (2, 3)
    assert choose_layout(9) == (3, 3)


def test_parse_lettering_splits_caption_dialogue_and_skips_sign():
    t = "CAPTION: In 7th grade we took metals.\n<TEACHER>: THERE'S THE DOOR!\nSIGN: *fake name"
    L = parse_lettering(t)
    assert L["captions"] == ["In 7th grade we took metals."]
    assert L["balloons"] == [("TEACHER", "THERE'S THE DOOR!")]


def test_parse_lettering_handles_no_text():
    assert parse_lettering("(no text)") == {"captions": [], "balloons": []}


def test_find_whitespace_slot_prefers_white_region():
    img = Image.new("RGB", (200, 200), "black")
    for x in range(0, 80):
        for y in range(0, 80):
            img.putpixel((x, y), (255, 255, 255))
    x, y = find_whitespace_slot(img, 40, 20)
    assert x < 110 and y < 110  # slot lands in/near the white region, not the black


def test_letter_panel_returns_same_size_image():
    p = Image.new("RGB", (300, 300), "white")
    out = letter_panel(p, "CAPTION: hello\n<MAN>: HI THERE")
    assert out.size == (300, 300)


def test_compose_strip_produces_rgb_image_with_title_and_panels():
    comic = {"title": "Test — No. 1", "panels": [
        {"n": 1, "content": "a man at a desk", "dialogue": "CAPTION: setup\n<MAN>: HELLO"},
        {"n": 2, "content": "the man again", "dialogue": "<MAN>: GOODBYE"},
        {"n": 3, "content": "empty room", "dialogue": "CAPTION: the end"},
    ]}
    img = compose_strip(comic, {}, cell=(220, 220))  # no rendered art -> placeholders
    assert img.mode == "RGB"
    # 3 panels -> 1x3 layout + a title band => width spans 3 cells, height has title + 1 row
    assert img.width > img.height
    assert img.height > 220
