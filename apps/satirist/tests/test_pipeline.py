import json
from PIL import Image
import intake_core.store as store
from satirist.pipeline import run, slugify


def _seed(db_path):
    store.init_db(db_path)
    mid = store.save_media_item(db_path, {"source_url": "u", "platform": "rss",
                                          "title": "Tammany graft", "text": "x"})
    store.save_signal(db_path, mid, {"topic": "Tammany graft",
                                     "entities": ["Tweed"], "summary": "Boss Tweed loots the city."})


def _fake_render(image_prompt, out_path):
    Image.new("RGB", (40, 40), "white").save(out_path)
    return out_path


def test_slugify():
    assert slugify("Tammany Hall: Graft!") == "tammany_hall_graft"


def test_run_happy_path_no_judge(tmp_path):
    db = str(tmp_path / "intake.db"); _seed(db)
    out = str(tmp_path / "out")
    brain_calls = []

    def fake_brain(event, revise_hint=""):
        brain_calls.append((event, revise_hint))
        return {"allegory_rationale": "Tweed as a bloated tiger.", "image_prompt": "tiger labeled TAMMANY"}

    res = run("Tammany", render_fn=_fake_render, brain_fn=fake_brain,
              judge_fn=None, db_path=db, out_dir=out)
    assert res["status"] == "ok"
    assert res["png"].endswith(".png")
    meta = json.loads(open(res["png"][:-4] + ".json", encoding="utf-8").read())
    assert meta["topic"] == "Tammany graft"
    assert meta["caption"].startswith("Tweed as a bloated tiger")
    assert meta["signal"]["entities"] == ["Tweed"]
    assert len(brain_calls) == 1                      # no judge -> no revise


def test_run_revises_once_when_judge_below_threshold(tmp_path):
    db = str(tmp_path / "intake.db"); _seed(db)
    out = str(tmp_path / "out")
    calls = {"brain": 0}

    def fake_brain(event, revise_hint=""):
        calls["brain"] += 1
        return {"allegory_rationale": f"draft {calls['brain']}", "image_prompt": "p"}

    scores = iter([{"score": 2.0, "rationale": "weak"}, {"score": 4.0, "rationale": "better"}])

    def fake_judge(concept):
        return next(scores)

    res = run("Tammany", render_fn=_fake_render, brain_fn=fake_brain,
              judge_fn=fake_judge, db_path=db, out_dir=out, threshold=3.5)
    assert res["status"] == "ok"
    assert calls["brain"] == 2                         # one revise round
    assert res["verdict"]["score"] == 4.0


def test_run_no_signal_returns_error(tmp_path):
    db = str(tmp_path / "intake.db"); _seed(db)
    res = run("NoSuchTopic", render_fn=_fake_render, brain_fn=lambda e, revise_hint="": {},
              judge_fn=None, db_path=db, out_dir=str(tmp_path / "out"))
    assert res["status"] == "no_signal"
