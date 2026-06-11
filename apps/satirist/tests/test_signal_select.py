import satirist
import satirist.config as cfg


def test_package_imports_and_config_defaults():
    assert satirist.__version__ == "0.1.0"
    # defaults exist and are strings
    assert cfg.BRAIN_URL.startswith("http")
    assert cfg.JUDGE_MODEL == "anthropic/claude-sonnet-4.6"
    assert cfg.LORA_S3_URI.endswith("nast_sdxl.safetensors")


import intake_core.store as store
from satirist.signal_select import select_signal


def _seed(db_path):
    store.init_db(db_path)
    mid = store.save_media_item(db_path, {"source_url": "u", "platform": "rss",
                                          "title": "Tammany Hall graft", "text": "x"})
    store.save_signal(db_path, mid, {"topic": "Tammany Hall graft",
                                     "entities": ["Tweed", "Tammany"], "summary": "Boss Tweed loots the city."})


def test_select_signal_returns_best_match(tmp_path):
    db = str(tmp_path / "intake.db")
    _seed(db)
    sig = select_signal("Tammany", db)
    assert sig is not None
    assert sig["topic"] == "Tammany Hall graft"
    assert "Tweed" in sig["entities"]
    assert sig["summary"].startswith("Boss Tweed")


def test_select_signal_none_when_no_match(tmp_path):
    db = str(tmp_path / "intake.db")
    _seed(db)
    assert select_signal("NoSuchTopicXYZ", db) is None
