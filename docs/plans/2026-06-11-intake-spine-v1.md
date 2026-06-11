# Intake Spine v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A standalone, reusable media-ingestion + signal-extraction tool — `intake-core` (framework-agnostic engine) wrapped by `intake-mcp` (an MCP server) — that turns feeds/URLs into structured "signals" (topic, entities, summary) usable as the event feed for any persona Brain.

**Architecture:** A URL **router** dispatches to **platform adapters** (RSS, YouTube transcript, web article). A **pipeline** orchestrates adapter → **SQLite store** (`media_items` + `signals`) → **signal extractor** (pluggable: keyword baseline default, optional LLM). The **MCP server** exposes four thin tools over the core: `ingest_url`, `ingest_feed`, `get_signals`, `query_media`. **Feed/URL-scoped only — no unbounded full-text search** (lesson from the Nast harvest). REST API + Claude Code plugin are later sub-projects.

**Tech Stack:** Python 3.11, `mcp` (FastMCP), `feedparser`, `youtube-transcript-api`, `trafilatura`, `requests`, stdlib `sqlite3`, `pytest`. Network calls isolated behind thin functions; unit tests run fully offline.

**Repo:** NEW standalone repo at `C:\Users\bradu\Documents\intake-spine`. Plan covers v1 only (spec §4, §5: `ilyrium-autostudio/docs/specs/2026-06-11-ilyrium-satirist-studio-program.md`).

---

## File Structure
```
intake-spine/
  conftest.py            # empty: puts repo root on sys.path
  pytest.ini             # testpaths = tests
  requirements.txt
  README.md
  intake_core/
    __init__.py
    router.py            # detect_platform(url)
    adapters/
      __init__.py
      rss.py             # parse_entries(parsed) [pure] + fetch_feed(url, max) [net]
      article.py         # extract_article(html, url) [pure] + fetch_article(url) [net]
      youtube.py         # video_id(url) [pure] + fetch_transcript(url) [net]
    store.py             # init_db, save_media_item, save_signal, query_media, get_signals
    signals.py           # extract_signal(text, title) [pure keyword baseline]
    pipeline.py          # ingest_url(url, db), ingest_feed(feed_url, max, db)
  intake_mcp/
    __init__.py
    server.py            # FastMCP server: ingest_url, ingest_feed, get_signals, query_media
  tests/
    test_router.py  test_rss.py  test_article.py  test_youtube.py
    test_store.py   test_signals.py  test_pipeline.py  test_server.py
```

---

## Task 1: Repo scaffold

**Files:** Create the repo skeleton.

- [ ] **Step 1: Create dirs + git init**
```bash
mkdir -p "C:/Users/bradu/Documents/intake-spine/intake_core/adapters" "C:/Users/bradu/Documents/intake-spine/intake_mcp" "C:/Users/bradu/Documents/intake-spine/tests"
cd "C:/Users/bradu/Documents/intake-spine" && git init
```

- [ ] **Step 2: Create `conftest.py` (repo root)**
```python
# Empty conftest: makes pytest put the repo root on sys.path so `import intake_core...` resolves.
```

- [ ] **Step 3: Create `pytest.ini`**
```ini
[pytest]
testpaths = tests
addopts = -q
```

- [ ] **Step 4: Create `requirements.txt`**
```
mcp>=1.2.0
feedparser>=6.0.11
youtube-transcript-api>=0.6.2
trafilatura>=1.12.0
requests>=2.32.0
pytest>=8.0.0
```

- [ ] **Step 5: Create empty package markers**
Create empty files: `intake_core/__init__.py`, `intake_core/adapters/__init__.py`, `intake_mcp/__init__.py`.

- [ ] **Step 6: Create `README.md`**
```markdown
# intake-spine
Reusable media ingestion + signal extraction. `intake_core` (engine) + `intake_mcp` (MCP server).
Feed/URL-scoped only. Turns feeds/URLs into structured signals (topic, entities, summary).
Install: `pip install -r requirements.txt`. Run MCP server: `python -m intake_mcp.server`.
```

- [ ] **Step 7: Commit**
```bash
git add -A && git commit -m "chore: scaffold intake-spine repo"
```

---

## Task 2: URL router (`intake_core/router.py`)

**Files:** Create `intake_core/router.py`, Test `tests/test_router.py`

- [ ] **Step 1: Write the failing test**
```python
# tests/test_router.py
from intake_core.router import detect_platform

def test_youtube_variants():
    assert detect_platform("https://www.youtube.com/watch?v=abc123") == "youtube"
    assert detect_platform("https://youtu.be/abc123") == "youtube"

def test_default_is_article():
    assert detect_platform("https://example.com/news/story-123") == "article"

def test_empty_raises():
    import pytest
    with pytest.raises(ValueError):
        detect_platform("")
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_router.py -v`
Expected: FAIL (no module `intake_core.router`)

- [ ] **Step 3: Write minimal implementation**
```python
# intake_core/router.py
"""Decide which adapter handles a URL. Single-item URLs only; RSS feeds use ingest_feed."""

def detect_platform(url: str) -> str:
    if not url or not url.strip():
        raise ValueError("empty url")
    u = url.lower()
    if "youtube.com/watch" in u or "youtu.be/" in u:
        return "youtube"
    return "article"
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_router.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**
```bash
git add intake_core/router.py tests/test_router.py && git commit -m "feat(core): URL platform router"
```

---

## Task 3: RSS adapter (`intake_core/adapters/rss.py`)

**Files:** Create `intake_core/adapters/rss.py`, Test `tests/test_rss.py`

- [ ] **Step 1: Write the failing test** (tests the pure parser on a feedparser-shaped object)
```python
# tests/test_rss.py
from types import SimpleNamespace
from intake_core.adapters.rss import parse_entries

def test_parse_entries_shapes_media_items():
    parsed = SimpleNamespace(entries=[
        SimpleNamespace(title="Senate passes bill", link="https://news.example/a",
                        summary="The Senate passed a tax bill today."),
        SimpleNamespace(title="No link item", summary="x"),  # missing link -> skipped
    ])
    items = parse_entries(parsed, max_items=10)
    assert len(items) == 1
    it = items[0]
    assert it["platform"] == "rss"
    assert it["title"] == "Senate passes bill"
    assert it["source_url"] == "https://news.example/a"
    assert "tax bill" in it["text"].lower()
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_rss.py -v`
Expected: FAIL (no module)

- [ ] **Step 3: Write minimal implementation**
```python
# intake_core/adapters/rss.py
"""RSS/Atom feed adapter. parse_entries is pure; fetch_feed does the network call."""

def parse_entries(parsed, max_items: int = 50) -> list[dict]:
    items = []
    for e in getattr(parsed, "entries", [])[:max_items]:
        link = getattr(e, "link", "") or ""
        if not link:
            continue
        items.append({
            "source_url": link,
            "platform": "rss",
            "title": getattr(e, "title", "") or "",
            "text": getattr(e, "summary", "") or getattr(e, "description", "") or "",
        })
    return items


def fetch_feed(feed_url: str, max_items: int = 50) -> list[dict]:
    import feedparser
    return parse_entries(feedparser.parse(feed_url), max_items=max_items)
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_rss.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add intake_core/adapters/rss.py tests/test_rss.py && git commit -m "feat(core): RSS feed adapter"
```

---

## Task 4: Article adapter (`intake_core/adapters/article.py`)

**Files:** Create `intake_core/adapters/article.py`, Test `tests/test_article.py`

- [ ] **Step 1: Write the failing test** (trafilatura extracts from an HTML *string* — fully offline)
```python
# tests/test_article.py
from intake_core.adapters.article import extract_article

def test_extract_article_from_html():
    html = "<html><head><title>Tax Bill Passes</title></head><body>" \
           "<article><h1>Tax Bill Passes</h1><p>The Senate approved the measure on Tuesday.</p>" \
           "<p>Opponents vowed to fight it.</p></article></body></html>"
    rec = extract_article(html, "https://news.example/tax")
    assert rec["platform"] == "article"
    assert rec["source_url"] == "https://news.example/tax"
    assert "Senate approved the measure" in rec["text"]
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_article.py -v`
Expected: FAIL (no module)

- [ ] **Step 3: Write minimal implementation**
```python
# intake_core/adapters/article.py
"""Web-article adapter. extract_article is pure (operates on HTML); fetch_article does the GET."""

def extract_article(html: str, url: str) -> dict:
    import trafilatura
    text = trafilatura.extract(html) or ""
    title = ""
    meta = trafilatura.extract_metadata(html)
    if meta and getattr(meta, "title", None):
        title = meta.title
    return {"source_url": url, "platform": "article", "title": title, "text": text}


def fetch_article(url: str) -> dict:
    import requests
    html = requests.get(url, timeout=30, headers={"User-Agent": "intake-spine/1.0"}).text
    return extract_article(html, url)
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_article.py -v`
Expected: PASS (trafilatura returns the body text)

- [ ] **Step 5: Commit**
```bash
git add intake_core/adapters/article.py tests/test_article.py && git commit -m "feat(core): web-article adapter"
```

---

## Task 5: YouTube adapter (`intake_core/adapters/youtube.py`)

**Files:** Create `intake_core/adapters/youtube.py`, Test `tests/test_youtube.py`

- [ ] **Step 1: Write the failing test** (pure `video_id` parser)
```python
# tests/test_youtube.py
from intake_core.adapters.youtube import video_id

def test_video_id_from_watch_and_short():
    assert video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_video_id_none_when_absent():
    assert video_id("https://example.com/x") is None
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_youtube.py -v`
Expected: FAIL (no module)

- [ ] **Step 3: Write minimal implementation**
```python
# intake_core/adapters/youtube.py
"""YouTube transcript adapter. video_id is pure; fetch_transcript does the network call."""
import re
import urllib.parse


def video_id(url: str):
    if "youtu.be/" in url:
        vid = url.split("youtu.be/")[1].split("?")[0].split("/")[0]
        return vid or None
    q = urllib.parse.urlparse(url)
    if "youtube.com" in q.netloc:
        v = urllib.parse.parse_qs(q.query).get("v", [None])[0]
        return v
    return None


def fetch_transcript(url: str) -> dict:
    from youtube_transcript_api import YouTubeTranscriptApi
    vid = video_id(url)
    if not vid:
        raise ValueError(f"no video id in {url}")
    fetched = YouTubeTranscriptApi().fetch(vid)
    text = " ".join(seg.text for seg in fetched)
    return {"source_url": url, "platform": "youtube", "title": vid, "text": text}
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_youtube.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add intake_core/adapters/youtube.py tests/test_youtube.py && git commit -m "feat(core): YouTube transcript adapter"
```

---

## Task 6: SQLite store (`intake_core/store.py`)

**Files:** Create `intake_core/store.py`, Test `tests/test_store.py`

- [ ] **Step 1: Write the failing test**
```python
# tests/test_store.py
from intake_core import store

def test_roundtrip(tmp_path):
    db = str(tmp_path / "t.db")
    store.init_db(db)
    mid = store.save_media_item(db, {"source_url": "u1", "platform": "rss",
                                     "title": "T", "text": "body text"})
    assert isinstance(mid, int)
    store.save_signal(db, mid, {"topic": "tax", "entities": ["Senate"], "summary": "s"})
    media = store.query_media(db, platform="rss")
    assert len(media) == 1 and media[0]["title"] == "T"
    sigs = store.get_signals(db, topic="tax")
    assert len(sigs) == 1 and sigs[0]["entities"] == ["Senate"] and sigs[0]["media_item_id"] == mid
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_store.py -v`
Expected: FAIL (no module)

- [ ] **Step 3: Write minimal implementation**
```python
# intake_core/store.py
"""SQLite store for media_items + signals (v1; swap for Postgres later if needed)."""
import sqlite3, json, datetime


def _conn(db_path):
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    return c


def init_db(db_path: str) -> None:
    with _conn(db_path) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS media_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT, source_url TEXT, platform TEXT,
            title TEXT, text TEXT, fetched_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS signals(
            id INTEGER PRIMARY KEY AUTOINCREMENT, media_item_id INTEGER,
            topic TEXT, entities TEXT, summary TEXT)""")


def save_media_item(db_path: str, item: dict) -> int:
    with _conn(db_path) as c:
        cur = c.execute(
            "INSERT INTO media_items(source_url,platform,title,text,fetched_at) VALUES(?,?,?,?,?)",
            (item.get("source_url"), item.get("platform"), item.get("title"),
             item.get("text"), datetime.datetime.utcnow().isoformat()))
        return cur.lastrowid


def save_signal(db_path: str, media_item_id: int, sig: dict) -> int:
    with _conn(db_path) as c:
        cur = c.execute(
            "INSERT INTO signals(media_item_id,topic,entities,summary) VALUES(?,?,?,?)",
            (media_item_id, sig.get("topic"), json.dumps(sig.get("entities", [])), sig.get("summary")))
        return cur.lastrowid


def query_media(db_path: str, platform: str = None, limit: int = 100) -> list[dict]:
    q, args = "SELECT * FROM media_items", []
    if platform:
        q += " WHERE platform=?"; args.append(platform)
    q += " ORDER BY id DESC LIMIT ?"; args.append(limit)
    with _conn(db_path) as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


def get_signals(db_path: str, topic: str = None, limit: int = 100) -> list[dict]:
    q, args = "SELECT * FROM signals", []
    if topic:
        q += " WHERE topic LIKE ?"; args.append(f"%{topic}%")
    q += " ORDER BY id DESC LIMIT ?"; args.append(limit)
    with _conn(db_path) as c:
        rows = [dict(r) for r in c.execute(q, args).fetchall()]
    for r in rows:
        r["entities"] = json.loads(r["entities"]) if r["entities"] else []
    return rows
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_store.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add intake_core/store.py tests/test_store.py && git commit -m "feat(core): SQLite store (media_items + signals)"
```

---

## Task 7: Signal extractor (`intake_core/signals.py`)

**Files:** Create `intake_core/signals.py`, Test `tests/test_signals.py`

- [ ] **Step 1: Write the failing test**
```python
# tests/test_signals.py
from intake_core.signals import extract_signal

def test_extract_signal_baseline():
    text = "Senator Smith proposed a new tax. The Senate debated it for hours. Smith defended the plan."
    sig = extract_signal(text, title="Tax Bill")
    assert sig["topic"] == "Tax Bill"
    assert sig["summary"].startswith("Senator Smith proposed a new tax.")
    assert any("Senate" in e for e in sig["entities"])

def test_extract_signal_topic_falls_back_to_entity():
    sig = extract_signal("Governor Lee vetoed the measure.", title="")
    assert sig["topic"]  # non-empty (entity or first words)
    assert "Governor Lee" in sig["entities"]
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_signals.py -v`
Expected: FAIL (no module)

- [ ] **Step 3: Write minimal implementation**
```python
# intake_core/signals.py
"""Pluggable signal extraction. Default = offline keyword/NER baseline. LLM extractor optional."""
import re

_SENT = re.compile(r"(?<=[.!?])\s+")
_PROPER = re.compile(r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b")


def extract_signal(text: str, title: str = "") -> dict:
    text = (text or "").strip()
    sents = _SENT.split(text) if text else []
    summary = " ".join(sents[:2]).strip()
    ents = []
    for m in _PROPER.findall(text):
        if m not in ents:
            ents.append(m)
    topic = (title.strip() or (ents[0] if ents else " ".join(text.split()[:5]))).strip()
    return {"topic": topic, "entities": ents[:10], "summary": summary}


def extract_signal_llm(text: str, title: str = "", model: str = "deepseek/deepseek-chat") -> dict:
    """Optional higher-quality extractor via OpenRouter. Falls back to baseline on any error."""
    import os, json, urllib.request
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return extract_signal(text, title)
    prompt = (f"Extract JSON {{\"topic\":..,\"entities\":[..],\"summary\":..}} from this text. "
              f"TITLE: {title}\nTEXT: {text[:4000]}")
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = json.loads(r.read())["choices"][0]["message"]["content"]
        s = raw[raw.find("{"):raw.rfind("}") + 1]
        obj = json.loads(s)
        return {"topic": obj.get("topic", title), "entities": obj.get("entities", []),
                "summary": obj.get("summary", "")}
    except Exception:
        return extract_signal(text, title)
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_signals.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add intake_core/signals.py tests/test_signals.py && git commit -m "feat(core): signal extractor (keyword baseline + optional LLM)"
```

---

## Task 8: Pipeline orchestration (`intake_core/pipeline.py`)

**Files:** Create `intake_core/pipeline.py`, Test `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing test** (adapters monkeypatched — no network)
```python
# tests/test_pipeline.py
from intake_core import pipeline, store

def test_ingest_url_routes_and_stores(tmp_path, monkeypatch):
    db = str(tmp_path / "p.db"); store.init_db(db)
    monkeypatch.setattr(pipeline, "fetch_article",
        lambda url: {"source_url": url, "platform": "article", "title": "Tax Bill",
                     "text": "Senator Smith proposed a new tax. The Senate debated it."})
    res = pipeline.ingest_url("https://news.example/tax", db)
    assert res["media_item_id"] > 0 and res["signal_id"] > 0
    sigs = store.get_signals(db)
    assert sigs[0]["topic"] == "Tax Bill"

def test_ingest_feed(tmp_path, monkeypatch):
    db = str(tmp_path / "f.db"); store.init_db(db)
    monkeypatch.setattr(pipeline, "fetch_feed",
        lambda url, max_items=50: [{"source_url": "u1", "platform": "rss", "title": "A",
                                    "text": "The Senate passed a bill."}])
    res = pipeline.ingest_feed("https://news.example/rss", db, max_items=5)
    assert res["ingested"] == 1
    assert len(store.query_media(db, platform="rss")) == 1
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_pipeline.py -v`
Expected: FAIL (no module)

- [ ] **Step 3: Write minimal implementation**
```python
# intake_core/pipeline.py
"""Orchestration: route -> adapter -> store media_item -> extract+store signal."""
from intake_core.router import detect_platform
from intake_core.adapters.article import fetch_article
from intake_core.adapters.youtube import fetch_transcript
from intake_core.adapters.rss import fetch_feed
from intake_core import store, signals


def _ingest_item(item: dict, db_path: str) -> dict:
    mid = store.save_media_item(db_path, item)
    sig = signals.extract_signal(item.get("text", ""), item.get("title", ""))
    sid = store.save_signal(db_path, mid, sig)
    return {"media_item_id": mid, "signal_id": sid, "topic": sig["topic"]}


def ingest_url(url: str, db_path: str) -> dict:
    platform = detect_platform(url)
    item = fetch_transcript(url) if platform == "youtube" else fetch_article(url)
    return _ingest_item(item, db_path)


def ingest_feed(feed_url: str, db_path: str, max_items: int = 50) -> dict:
    items = fetch_feed(feed_url, max_items=max_items)
    results = [_ingest_item(it, db_path) for it in items]
    return {"ingested": len(results), "items": results}
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_pipeline.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**
```bash
git add intake_core/pipeline.py tests/test_pipeline.py && git commit -m "feat(core): ingest pipeline (url + feed)"
```

---

## Task 9: MCP server (`intake_mcp/server.py`)

**Files:** Create `intake_mcp/server.py`, Test `tests/test_server.py`

- [ ] **Step 1: Write the failing test** (server imports + exposes the 4 tools; no network)
```python
# tests/test_server.py
import asyncio
from intake_mcp import server

def test_server_exposes_four_tools():
    tools = asyncio.run(server.mcp.list_tools())
    names = {t.name for t in tools}
    assert {"ingest_url", "ingest_feed", "get_signals", "query_media"} <= names
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_server.py -v`
Expected: FAIL (no module `intake_mcp.server`)

- [ ] **Step 3: Write minimal implementation**
```python
# intake_mcp/server.py
"""MCP server exposing the intake-core engine as tools. Run: python -m intake_mcp.server"""
import os
from mcp.server.fastmcp import FastMCP
from intake_core import pipeline, store

DB = os.environ.get("INTAKE_DB", os.path.expanduser("~/.intake-spine/intake.db"))
os.makedirs(os.path.dirname(DB), exist_ok=True)
store.init_db(DB)

mcp = FastMCP("intake-spine")


@mcp.tool()
def ingest_url(url: str) -> dict:
    """Ingest a single article or YouTube URL into the store and extract its signal."""
    return pipeline.ingest_url(url, DB)


@mcp.tool()
def ingest_feed(feed_url: str, max_items: int = 50) -> dict:
    """Ingest items from an RSS/Atom feed URL (capped at max_items)."""
    return pipeline.ingest_feed(feed_url, DB, max_items=max_items)


@mcp.tool()
def get_signals(topic: str = "", limit: int = 50) -> list:
    """Return extracted signals (topic, entities, summary), optionally filtered by topic substring."""
    return store.get_signals(DB, topic=topic or None, limit=limit)


@mcp.tool()
def query_media(platform: str = "", limit: int = 50) -> list:
    """Return stored media items, optionally filtered by platform (rss/youtube/article)."""
    return store.query_media(DB, platform=platform or None, limit=limit)


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_server.py -v`
Expected: PASS (FastMCP `list_tools()` returns the 4 registered tools)

- [ ] **Step 5: Commit**
```bash
git add intake_mcp/server.py tests/test_server.py && git commit -m "feat(mcp): intake-spine MCP server (4 tools over core)"
```

---

## Task 10: Full-suite green + README usage

**Files:** Modify `README.md`

- [ ] **Step 1: Run the full suite**
Run: `python -m pytest tests -q`
Expected: PASS (all of: router 3, rss 1, article 1, youtube 2, store 1, signals 2, pipeline 2, server 1)

- [ ] **Step 2: Append MCP usage to `README.md`**
```markdown
## MCP usage
Configure an MCP client to run: `python -m intake_mcp.server` (stdio).
Tools: `ingest_url(url)`, `ingest_feed(feed_url, max_items)`, `get_signals(topic, limit)`, `query_media(platform, limit)`.
DB path via `INTAKE_DB` env (default `~/.intake-spine/intake.db`). Optional LLM signals via `OPENROUTER_API_KEY`.
```

- [ ] **Step 3: Commit**
```bash
git add README.md && git commit -m "docs: intake-spine MCP usage"
```

---

## Exit criteria
- New `intake-spine` repo, `python -m pytest tests -q` green (13 tests).
- `intake_core` ingests RSS/YouTube/article → SQLite → signals, feed/URL-scoped (no full-text search).
- `intake_mcp.server` exposes the 4 tools and runs as an MCP server.

**Next sub-projects (later plans):** REST API wrapper + Claude Code plugin packaging (spec §4); then the ideation/render slices (spec §9) that consume these signals.
