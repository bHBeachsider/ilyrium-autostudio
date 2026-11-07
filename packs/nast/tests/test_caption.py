from packs.nast.hand.caption import clean_title, build_caption, TRIGGER

def test_clean_title_strips_ids_and_attribution():
    fn = "Compromise_with_the_South_-_Dedicated_to_the_Chicago_Convention_-_Th._Nast._LCCN2002723256.jpg"
    t = clean_title(fn)
    assert t == "Compromise with the South - Dedicated to the Chicago Convention"
    assert "LCCN" not in t and "Nast" not in t and ".jpg" not in t

def test_clean_title_strips_museum_codes():
    fn = "A_Group_of_Vultures_Waiting_for_the_Storm_to_Blow_Over_MET_DP809646.jpg"
    t = clean_title(fn)
    assert "MET" not in t and "DP809646" not in t
    assert t.startswith("A Group of Vultures")

def test_build_caption_has_trigger_and_style():
    c = build_caption("The Tammany Tiger Loose")
    assert c.startswith(TRIGGER + ", ")
    assert "The Tammany Tiger Loose" in c
    assert "wood engraving" in c.lower()
