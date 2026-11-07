from packs.nast.data_sources.loc_fetch import safe_filename

def test_safe_filename_from_item():
    it = {"id": "http://www.loc.gov/item/2002695175/", "title": "The Tammany Tiger Loose!"}
    fn = safe_filename(it, 3)
    assert fn.endswith(".jpg") and " " not in fn and fn.startswith("003_")
    assert "tammany" in fn.lower()
