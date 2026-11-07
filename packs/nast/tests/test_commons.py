from packs.nast.data_sources.wikimedia_commons import split_members, pick_files, parse_search

def test_parse_search():
    payload = {"query": {"search": [{"title": "File:A.jpg"}, {"title": "File:B.jpg"}]}}
    assert parse_search(payload) == ["File:A.jpg", "File:B.jpg"]

def test_split_members():
    payload = {"query": {"categorymembers": [
        {"ns": 6, "title": "File:A.jpg"}, {"ns": 14, "title": "Category:Sub"},
        {"ns": 6, "title": "File:B.jpg"}]}}
    files, subcats = split_members(payload)
    assert files == ["File:A.jpg", "File:B.jpg"]
    assert subcats == ["Category:Sub"]

def test_pick_files_filters_minpx():
    payload = {"query": {"pages": {
        "1": {"title": "File:A.jpg", "imageinfo": [{"url": "http://x/A.jpg", "width": 4000, "height": 5000}]},
        "2": {"title": "File:B.jpg", "imageinfo": [{"url": "http://x/B.jpg", "width": 600, "height": 700}]}}}}
    kept = pick_files(payload, min_px=1200)
    assert len(kept) == 1 and kept[0]["title"] == "File:A.jpg" and kept[0]["url"].endswith("A.jpg")

def test_pick_files_handles_missing_imageinfo():
    payload = {"query": {"pages": {"1": {"title": "File:X.jpg"}}}}
    assert pick_files(payload, min_px=1200) == []
