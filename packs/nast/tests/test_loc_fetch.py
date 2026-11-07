from packs.nast.data_sources.loc_fetch import parse_results

SAMPLE = {
    "results": [
        {"id": "http://www.loc.gov/item/2002695175/",
         "title": "The Tammany Tiger Loose",
         "date": "1871",
         "image_url": ["//tile.loc.gov/storage/.../small.jpg",
                       "//tile.loc.gov/storage/.../large.jpg"]},
        {"title": "no-image item"},
    ]
}

def test_parse_results_extracts_items():
    items = parse_results(SAMPLE)
    assert len(items) == 1
    it = items[0]
    assert it["title"] == "The Tammany Tiger Loose"
    assert it["date"] == "1871"
    assert it["image_url"].startswith("https://")
    assert it["image_url"].endswith("large.jpg")
