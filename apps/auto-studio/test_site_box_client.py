"""Unit tests for site_box_client (pure logic + retry policy; no real network/boto3).

Run from apps/auto-studio:  venv/Scripts/python -m pytest test_site_box_client.py -q
"""
import pytest
import site_box_client as sb

# assemble_cut() return shape
RELEASED_RETURN = {
    "cut_id": "cut_1", "final_video": "/x/final.mp4",
    "public_url": "https://media.ilyrium.io/campaigns/c1/final_commercial.mp4",
    "published": True, "release_allowed": True, "blockers": [], "qa": {"passed": True},
}
# stored project["cuts"][-1] shape
STORED_CUT = {
    "cut_id": "cut_2", "output": "/x/cut2.mp4", "final_video": "/x/cut2.mp4",
    "public_url": "https://media.ilyrium.io/campaigns/c1/final_commercial.mp4",
    "release": {"published": True, "allowed": True, "enforced": True,
                "blockers": [], "checksum": "sha256:abc", "qa_passed": True},
}


def test_build_body_from_assemble_return():
    body = sb.build_attach_body(campaign_id="c1", cut=RELEASED_RETURN, article_id="a1")
    assert body["articleId"] == "a1"
    assert body["videoUrl"] == RELEASED_RETURN["public_url"]
    assert body["idempotencyKey"] == "c1:cut_1"
    assert body["meta"]["cut_id"] == "cut_1"
    assert body["meta"]["release"]["allowed"] is True
    assert body["meta"]["ai_disclosure"] == sb.DEFAULT_AI_DISCLOSURE


def test_build_body_from_stored_cut_reads_release_and_checksum():
    body = sb.build_attach_body(campaign_id="c1", cut=STORED_CUT, slug="my-slug")
    assert body["slug"] == "my-slug"
    assert "articleId" not in body
    assert body["idempotencyKey"] == "c1:cut_2"
    assert body["meta"]["checksum"] == "sha256:abc"


def test_build_body_refuses_unreleased():
    with pytest.raises(sb.AttachError):
        sb.build_attach_body(campaign_id="c1", cut={**RELEASED_RETURN, "release_allowed": False}, article_id="a1")


def test_build_body_refuses_missing_public_url():
    with pytest.raises(sb.AttachError):
        sb.build_attach_body(campaign_id="c1", cut={**RELEASED_RETURN, "public_url": None}, article_id="a1")


def test_build_body_requires_article_or_slug():
    with pytest.raises(sb.AttachError):
        sb.build_attach_body(campaign_id="c1", cut=RELEASED_RETURN)


def test_should_retry():
    assert sb._should_retry(None)
    assert sb._should_retry(503)
    assert sb._should_retry(429)
    assert not sb._should_retry(400)
    assert not sb._should_retry(404)
    assert not sb._should_retry(422)


class _Resp:
    def __init__(self, status, payload=None, text=""):
        self.status_code = status
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def test_post_attach_success(monkeypatch):
    monkeypatch.setattr(sb.requests, "post", lambda *a, **k: _Resp(200, {"updated": True}))
    out = sb.post_attach({"x": 1}, base_url="https://s", secret="k", _sleep=lambda _s: None)
    assert out == {"updated": True}


def test_post_attach_422_is_not_retried(monkeypatch):
    calls = {"n": 0}

    def fake(*a, **k):
        calls["n"] += 1
        return _Resp(422, text="release not passed")

    monkeypatch.setattr(sb.requests, "post", fake)
    with pytest.raises(sb.AttachError):
        sb.post_attach({"x": 1}, base_url="https://s", secret="k", _sleep=lambda _s: None)
    assert calls["n"] == 1


def test_post_attach_retries_5xx_then_succeeds(monkeypatch):
    seq = [_Resp(503, text="busy"), _Resp(200, {"ok": True})]
    monkeypatch.setattr(sb.requests, "post", lambda *a, **k: seq.pop(0))
    out = sb.post_attach({"x": 1}, base_url="https://s", secret="k", attempts=3, _sleep=lambda _s: None)
    assert out == {"ok": True}


def test_post_attach_network_error_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise sb.requests.ConnectionError("boom")
        return _Resp(200, {"ok": True})

    monkeypatch.setattr(sb.requests, "post", fake)
    out = sb.post_attach({"x": 1}, base_url="https://s", secret="k", attempts=3, _sleep=lambda _s: None)
    assert out == {"ok": True}
    assert calls["n"] == 2


def test_post_attach_requires_config(monkeypatch):
    monkeypatch.delenv("SITE_BOX_BASE_URL", raising=False)
    monkeypatch.delenv("SITE_BOX_INGEST_SECRET", raising=False)
    with pytest.raises(sb.AttachError):
        sb.post_attach({}, base_url=None, secret=None)
