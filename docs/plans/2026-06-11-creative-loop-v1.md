# Creative Loop v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first end-to-end Nast cartoon vertical — a current event/signal flows through the Nast Brain (allegory + image prompt), an optional one-round taste judge, the SDXL Hand LoRA (GPU render), and a PIL caption composite, producing a saved PNG + sidecar JSON.

**Architecture:** A new `apps/satirist/` module in the ilyrium-autostudio repo. All orchestration logic is pure and unit-tested (signal selection over the pip-installed `intake_core`, Brain JSON parsing, judge verdict parsing, PIL caption compositing). The two network calls (Ollama Brain, OpenRouter judge) and the one GPU call (diffusers SDXL render) are thin wrappers, injected into the pipeline so tests pass fakes. The render is the ONLY GPU-dependent piece — everything else runs and tests locally, offline, on the dev machine.

**Tech Stack:** Python 3.11/3.13, `intake_core` (pip-installed from intake-spine), Pillow (caption), `urllib`/`requests` (Ollama + OpenRouter HTTP), diffusers + torch (GPU, render only), boto3/aws-cli (pull LoRA from S3), pytest.

**Key external facts (verified):**
- `intake_core.store.get_signals(db_path, topic=None, limit=100) -> list[dict]`; each signal row is `{"id", "media_item_id", "topic", "entities": list, "summary"}` (most recent first; `topic` matched with SQL `LIKE %topic%`).
- `intake_core.pipeline.ingest_feed(feed_url, db_path, max_items=50) -> dict` and `init_db(db_path)` populate the store.
- The Nast Brain is served by Ollama as model `nast-brain`; `POST http://<host>:11434/api/generate` with `{"model","prompt","stream":false}` returns `{"response": "<text>"}`. The Brain emits JSON `{"allegory_rationale": str, "image_prompt": str}` (no separate labels/caption field; labels are embedded in `image_prompt` text).
- Trained SDXL Hand LoRA: `s3://ilyrium-slm-foundry/models/nast/hand/sdxl/nast_sdxl.safetensors`; trigger token `thomas_nast_style`.
- Judge model on OpenRouter: `anthropic/claude-sonnet-4.6`.
- The studio already manages a ComfyUI GPU box via `apps/auto-studio/ec2_session.py` (instance `i-030994c5371ee5de9`); the render step runs on any CUDA box — that box or a fresh one — NOT in CI.

---

## File Structure

```
apps/satirist/
  satirist/
    __init__.py
    config.py          # paths/env defaults (DB, OUT, BRAIN_URL, model ids)
    signal_select.py   # select_signal(query, db_path) -> dict|None   (RAG step)
    brain.py           # parse_brain_output(raw) [pure]; ideate(event, brain_url) [net]
    judge.py           # NAST_RUBRIC; parse_verdict(raw) [pure]; should_revise(v, thr) [pure]; score_concept(concept) [net]
    caption.py         # derive_caption(text) [pure]; compose_caption_banner(img, text) [pure]; save_artifact(img, meta, out_dir, slug) [io]
    render.py          # GPU ONLY: fetch_lora(s3_uri, dest); render_sdxl(image_prompt, lora_path, out_path)
    pipeline.py        # run(topic, *, render_fn, brain_fn, judge_fn, db_path, out_dir, threshold) orchestration
    cli.py             # python -m satirist.cli --topic "..." [--ingest-feed URL] [--dry-run] [--no-judge]
  tests/
    test_signal_select.py
    test_brain.py
    test_judge.py
    test_caption.py
    test_pipeline.py
  conftest.py          # makes `satirist` importable when running pytest from apps/satirist/
  pytest.ini
  requirements.txt
  README.md
```

Each file has one responsibility. `pipeline.run` is pure orchestration: it receives the Brain/judge/render as injected callables (with real defaults wired in `cli.py`), so the whole flow is unit-testable with fakes and only `cli.py` touches the network/GPU by default.

---

### Task 1: Scaffold the satirist module

**Files:**
- Create: `apps/satirist/satirist/__init__.py`
- Create: `apps/satirist/satirist/config.py`
- Create: `apps/satirist/conftest.py`
- Create: `apps/satirist/pytest.ini`
- Create: `apps/satirist/requirements.txt`
- Create: `apps/satirist/README.md`
- Test: `apps/satirist/tests/test_signal_select.py` (placeholder import test first)

- [ ] **Step 1: Write the failing test**

```python
# apps/satirist/tests/test_signal_select.py
import satirist
import satirist.config as cfg


def test_package_imports_and_config_defaults():
    assert satirist.__version__ == "0.1.0"
    # defaults exist and are strings
    assert cfg.BRAIN_URL.startswith("http")
    assert cfg.JUDGE_MODEL == "anthropic/claude-sonnet-4.6"
    assert cfg.LORA_S3_URI.endswith("nast_sdxl.safetensors")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/satirist && python -m pytest tests/test_signal_select.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'satirist'`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/satirist/satirist/__init__.py
"""Nast satirist creative loop (v1): signal -> Brain -> judge -> Hand render -> caption."""
__version__ = "0.1.0"
```

```python
# apps/satirist/satirist/config.py
"""Paths and provider defaults for the satirist creative loop. Override via env."""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_VAR = os.path.join(os.path.dirname(_HERE), "var")  # apps/satirist/var

# intake-spine SQLite store the RAG step reads from
DB_PATH = os.environ.get("INTAKE_DB", os.path.join(_VAR, "intake.db"))
# where finished cartoons + sidecar JSON land
OUT_DIR = os.environ.get("SATIRIST_OUT", os.path.join(_VAR, "output"))

# Nast Brain (Ollama). Host configurable; model name is fixed by the deploy.
BRAIN_URL = os.environ.get("BRAIN_URL", "http://localhost:11434")
BRAIN_MODEL = os.environ.get("BRAIN_MODEL", "nast-brain")

# Taste judge (OpenRouter)
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "anthropic/claude-sonnet-4.6")
JUDGE_THRESHOLD = float(os.environ.get("JUDGE_THRESHOLD", "3.5"))

# SDXL Hand LoRA (GPU render step)
LORA_S3_URI = os.environ.get(
    "NAST_LORA_S3", "s3://ilyrium-slm-foundry/models/nast/hand/sdxl/nast_sdxl.safetensors")
SDXL_BASE = os.environ.get("SDXL_BASE", "stabilityai/stable-diffusion-xl-base-1.0")
STYLE_TRIGGER = os.environ.get("NAST_STYLE_TRIGGER", "thomas_nast_style")
```

```python
# apps/satirist/conftest.py
"""Make the `satirist` package importable when pytest runs from apps/satirist/."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
```

```ini
# apps/satirist/pytest.ini
[pytest]
testpaths = tests
addopts = -q
```

```text
# apps/satirist/requirements.txt
intake-spine
Pillow>=10.0.0
requests>=2.32.0
# render-only (install on the GPU box, not needed for tests):
#   diffusers>=0.30.0
#   torch
#   transformers
#   accelerate
#   safetensors
#   boto3
```

```markdown
<!-- apps/satirist/README.md -->
# satirist — Nast Creative Loop v1

End-to-end: a current event/signal -> Nast Brain (allegory + image prompt) ->
optional taste judge (one revise round) -> SDXL Hand LoRA render (GPU) ->
PIL caption banner -> saved PNG + sidecar JSON.

## Run (dev machine, no GPU)
```
cd apps/satirist
python -m pytest          # all logic tests, offline
python -m satirist.cli --topic "Tammany" --dry-run   # skips GPU render, emits concept + caption on a placeholder image
```

## Run the real render (GPU box only)
See "GPU Runbook" at the bottom of this README (added in the render task).
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/satirist && python -m pytest tests/test_signal_select.py -q`
Expected: PASS (1 passed). If `intake-spine` import is needed later it is already pip-installed; this test only imports `satirist`.

- [ ] **Step 5: Commit**

```bash
git add apps/satirist/
git commit -m "feat(satirist): scaffold creative-loop module (config, conftest, pytest, readme)"
```

---

### Task 2: Signal selection (RAG step)

**Files:**
- Create: `apps/satirist/satirist/signal_select.py`
- Test: `apps/satirist/tests/test_signal_select.py` (extend)

- [ ] **Step 1: Write the failing test**

```python
# append to apps/satirist/tests/test_signal_select.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/satirist && python -m pytest tests/test_signal_select.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'satirist.signal_select'`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/satirist/satirist/signal_select.py
"""RAG step: pick the best current signal for a topic from the intake-spine store."""
import intake_core.store as store


def select_signal(query: str, db_path: str) -> dict | None:
    """Return the most recent signal whose topic matches `query`, or None.

    Shape: {"id","media_item_id","topic","entities":list,"summary"}.
    `get_signals` already orders most-recent-first and LIKE-matches the topic.
    """
    rows = store.get_signals(db_path, topic=query, limit=1)
    return rows[0] if rows else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/satirist && python -m pytest tests/test_signal_select.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/satirist/satirist/signal_select.py apps/satirist/tests/test_signal_select.py
git commit -m "feat(satirist): RAG signal selection over intake_core store"
```

---

### Task 3: Brain client (ideate)

**Files:**
- Create: `apps/satirist/satirist/brain.py`
- Test: `apps/satirist/tests/test_brain.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/satirist/tests/test_brain.py
import pytest
from satirist.brain import parse_brain_output, build_prompt


def test_parse_plain_json():
    raw = '{"allegory_rationale": "Tweed as a bloated tiger", "image_prompt": "a tiger labeled TAMMANY"}'
    out = parse_brain_output(raw)
    assert out["allegory_rationale"].startswith("Tweed")
    assert out["image_prompt"] == "a tiger labeled TAMMANY"


def test_parse_strips_markdown_fences_and_prose():
    raw = "Here you go:\n```json\n{\"allegory_rationale\":\"a\",\"image_prompt\":\"b\"}\n```\nHope that helps!"
    out = parse_brain_output(raw)
    assert out == {"allegory_rationale": "a", "image_prompt": "b"}


def test_parse_raises_on_no_json():
    with pytest.raises(ValueError):
        parse_brain_output("no json here at all")


def test_parse_raises_on_missing_required_key():
    with pytest.raises(ValueError):
        parse_brain_output('{"allegory_rationale": "a"}')  # image_prompt missing


def test_build_prompt_includes_event_and_revise_hint():
    p = build_prompt("Boss Tweed loots the city.", revise_hint="make the tiger angrier")
    assert "Boss Tweed loots the city." in p
    assert "make the tiger angrier" in p
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/satirist && python -m pytest tests/test_brain.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'satirist.brain'`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/satirist/satirist/brain.py
"""Nast Brain client: build the prompt, call Ollama, parse the JSON concept."""
import json
import urllib.request

from . import config

_REQUIRED = ("allegory_rationale", "image_prompt")


def build_prompt(event_summary: str, revise_hint: str = "") -> str:
    """The Brain was trained to map an event -> {allegory_rationale, image_prompt}."""
    base = (
        "Event: " + event_summary.strip() + "\n"
        "Respond ONLY with JSON: {\"allegory_rationale\": str, \"image_prompt\": str}. "
        "image_prompt must be a 19th-century Harper's Weekly wood-engraving cartoon description."
    )
    if revise_hint:
        base += "\nRevision note: " + revise_hint.strip()
    return base


def parse_brain_output(raw: str) -> dict:
    """Extract the JSON object from the Brain's response text. Raises ValueError if absent/invalid."""
    if not raw or "{" not in raw or "}" not in raw:
        raise ValueError("no JSON object in Brain output")
    blob = raw[raw.find("{"):raw.rfind("}") + 1]
    try:
        obj = json.loads(blob)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON in Brain output: {e}") from e
    for k in _REQUIRED:
        if k not in obj or not str(obj[k]).strip():
            raise ValueError(f"Brain output missing required key: {k}")
    return {k: obj[k] for k in _REQUIRED} | (
        {"caption": obj["caption"]} if obj.get("caption") else {})


def ideate(event_summary: str, brain_url: str = None, revise_hint: str = "", timeout: int = 120) -> dict:
    """Call the Ollama-served Nast Brain; return the parsed concept dict. Network call."""
    url = (brain_url or config.BRAIN_URL).rstrip("/") + "/api/generate"
    body = json.dumps({"model": config.BRAIN_MODEL,
                       "prompt": build_prompt(event_summary, revise_hint),
                       "stream": False}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read())
    return parse_brain_output(resp.get("response", ""))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/satirist && python -m pytest tests/test_brain.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/satirist/satirist/brain.py apps/satirist/tests/test_brain.py
git commit -m "feat(satirist): Nast Brain client (prompt build + robust JSON parse + ideate)"
```

---

### Task 4: Taste judge (one critique→revise round)

**Files:**
- Create: `apps/satirist/satirist/judge.py`
- Test: `apps/satirist/tests/test_judge.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/satirist/tests/test_judge.py
import pytest
from satirist.judge import parse_verdict, should_revise, build_judge_prompt, NAST_RUBRIC


def test_parse_verdict_extracts_score_and_rationale():
    raw = 'Assessment: ```{"score": 4.2, "rationale": "strong allegory"}```'
    v = parse_verdict(raw)
    assert v["score"] == 4.2
    assert v["rationale"] == "strong allegory"


def test_parse_verdict_clamps_and_defaults_rationale():
    v = parse_verdict('{"score": 9}')          # out of 1-5 range -> clamped
    assert v["score"] == 5.0
    assert v["rationale"] == ""


def test_parse_verdict_raises_on_no_score():
    with pytest.raises(ValueError):
        parse_verdict("the cartoon is nice")


def test_should_revise_below_threshold():
    assert should_revise({"score": 3.0}, threshold=3.5) is True
    assert should_revise({"score": 3.5}, threshold=3.5) is False
    assert should_revise({"score": 4.9}, threshold=3.5) is False


def test_rubric_and_prompt_mention_allegory():
    assert "allegory" in NAST_RUBRIC.lower()
    p = build_judge_prompt({"allegory_rationale": "a tiger", "image_prompt": "b"})
    assert "a tiger" in p
    assert "score" in p.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/satirist && python -m pytest tests/test_judge.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'satirist.judge'`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/satirist/satirist/judge.py
"""Taste judge: score a Nast concept against a small rubric; decide whether to revise once."""
import json
import urllib.request

from . import config

NAST_RUBRIC = (
    "Score 1-5 how well this concept captures Thomas Nast's editorial taste:\n"
    "- A single dominant allegory/visual metaphor (Tammany Tiger, the Ring, a bloated boss).\n"
    "- Heavy-handed moral framing with a clear villain and victim.\n"
    "- Concrete, labeled symbols rather than abstract description.\n"
    "- Reads as a 19th-century Harper's Weekly cartoon, not a modern comic."
)


def build_judge_prompt(concept: dict) -> str:
    return (
        NAST_RUBRIC + "\n\n"
        "CONCEPT:\n"
        f"allegory_rationale: {concept.get('allegory_rationale', '')}\n"
        f"image_prompt: {concept.get('image_prompt', '')}\n\n"
        "Respond ONLY with JSON: {\"score\": <float 1-5>, \"rationale\": <str>}."
    )


def parse_verdict(raw: str) -> dict:
    """Extract {score: float(1-5), rationale: str}. Raises ValueError if no score found."""
    if not raw or "{" not in raw or "}" not in raw:
        raise ValueError("no JSON verdict in judge output")
    blob = raw[raw.find("{"):raw.rfind("}") + 1]
    try:
        obj = json.loads(blob)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON verdict: {e}") from e
    if "score" not in obj:
        raise ValueError("verdict missing score")
    score = max(1.0, min(5.0, float(obj["score"])))
    return {"score": score, "rationale": str(obj.get("rationale", "") or "")}


def should_revise(verdict: dict, threshold: float = None) -> bool:
    thr = config.JUDGE_THRESHOLD if threshold is None else threshold
    return float(verdict.get("score", 0.0)) < thr


def score_concept(concept: dict, model: str = None, timeout: int = 120) -> dict:
    """Network call to OpenRouter. Returns parse_verdict(...). Requires OPENROUTER_API_KEY."""
    import os
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set; cannot run the taste judge")
    body = json.dumps({"model": model or config.JUDGE_MODEL,
                       "messages": [{"role": "user", "content": build_judge_prompt(concept)}]}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = json.loads(r.read())["choices"][0]["message"]["content"]
    return parse_verdict(raw)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/satirist && python -m pytest tests/test_judge.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/satirist/satirist/judge.py apps/satirist/tests/test_judge.py
git commit -m "feat(satirist): Nast taste judge (rubric + verdict parse + revise gate)"
```

---

### Task 5: Caption compositor + artifact save

**Files:**
- Create: `apps/satirist/satirist/caption.py`
- Test: `apps/satirist/tests/test_caption.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/satirist/tests/test_caption.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/satirist && python -m pytest tests/test_caption.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'satirist.caption'`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/satirist/satirist/caption.py
"""Caption banner composite (PIL) + artifact save. v1 does NOT overlay in-image labels
(SDXL can't render legible text); it adds a legible caption strip below the render."""
import json
import os
import re
import textwrap

from PIL import Image, ImageDraw, ImageFont

_SENT = re.compile(r"(?<=[.!?])\s+")
_MAX = 160
_BANNER_PAD = 12
_LINE_H = 16


def derive_caption(text: str) -> str:
    """First sentence of the allegory rationale, truncated to <=160 chars."""
    text = (text or "").strip()
    first = _SENT.split(text)[0] if text else ""
    return first if len(first) <= _MAX else first[:_MAX - 1].rstrip() + "…"


def compose_caption_banner(image: Image.Image, caption: str) -> Image.Image:
    """Return a new RGB image = the render with a white caption strip appended below."""
    img = image.convert("RGB")
    try:
        font = ImageFont.load_default()
    except Exception:                                   # pragma: no cover - font always present
        font = None
    wrap_cols = max(10, img.width // 7)
    lines = textwrap.wrap(caption, width=wrap_cols) or [""]
    banner_h = _BANNER_PAD * 2 + _LINE_H * len(lines)
    out = Image.new("RGB", (img.width, img.height + banner_h), "white")
    out.paste(img, (0, 0))
    draw = ImageDraw.Draw(out)
    y = img.height + _BANNER_PAD
    for line in lines:
        draw.text((_BANNER_PAD, y), line, fill="black", font=font)
        y += _LINE_H
    return out


def save_artifact(image: Image.Image, meta: dict, out_dir: str, slug: str) -> str:
    """Write <slug>.png and <slug>.json into out_dir; return the PNG path."""
    os.makedirs(out_dir, exist_ok=True)
    png = os.path.join(out_dir, f"{slug}.png")
    image.save(png)
    with open(png[:-4] + ".json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return png
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/satirist && python -m pytest tests/test_caption.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/satirist/satirist/caption.py apps/satirist/tests/test_caption.py
git commit -m "feat(satirist): PIL caption banner + artifact (png + sidecar json) save"
```

---

### Task 6: Pipeline orchestration

**Files:**
- Create: `apps/satirist/satirist/pipeline.py`
- Test: `apps/satirist/tests/test_pipeline.py`

The pipeline is pure orchestration. Brain, judge, and render are injected callables so tests pass fakes; `cli.py` (next task) wires the real ones.

- [ ] **Step 1: Write the failing test**

```python
# apps/satirist/tests/test_pipeline.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/satirist && python -m pytest tests/test_pipeline.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'satirist.pipeline'`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/satirist/satirist/pipeline.py
"""Orchestrate the creative loop. Brain/judge/render are injected callables (real ones wired in cli.py)."""
import os
import re

from . import caption as cap_mod
from . import config
from .signal_select import select_signal

_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    return _SLUG.sub("_", (text or "").lower()).strip("_")


def run(topic, *, render_fn, brain_fn, judge_fn=None, db_path=None, out_dir=None,
        threshold=None):
    """Run signal -> ideate -> (judge -> one revise) -> render -> caption -> save.

    render_fn(image_prompt, out_path) -> out_path   (writes a PNG; GPU in prod)
    brain_fn(event_summary, revise_hint="") -> {"allegory_rationale","image_prompt"[, "caption"]}
    judge_fn(concept) -> {"score","rationale"} or None to skip the judge.

    Returns {"status": "ok"|"no_signal", ...}.
    """
    db_path = db_path or config.DB_PATH
    out_dir = out_dir or config.OUT_DIR
    thr = config.JUDGE_THRESHOLD if threshold is None else threshold

    signal = select_signal(topic, db_path)
    if signal is None:
        return {"status": "no_signal", "topic": topic}

    event = signal["summary"] or signal["topic"]
    concept = brain_fn(event)
    verdict = None
    if judge_fn is not None:
        verdict = judge_fn(concept)
        if float(verdict.get("score", 0.0)) < thr:
            concept = brain_fn(event, revise_hint="Sharpen the central allegory; "
                                                  "make the villain and the labeled symbols unmistakable.")

    caption = concept.get("caption") or cap_mod.derive_caption(concept["allegory_rationale"])
    slug = slugify(signal["topic"]) or "cartoon"

    os.makedirs(out_dir, exist_ok=True)
    raw_png = os.path.join(out_dir, f"{slug}_raw.png")
    render_fn(concept["image_prompt"] + ", " + config.STYLE_TRIGGER, raw_png)

    from PIL import Image
    final = cap_mod.compose_caption_banner(Image.open(raw_png), caption)
    meta = {"topic": signal["topic"], "allegory_rationale": concept["allegory_rationale"],
            "image_prompt": concept["image_prompt"], "caption": caption,
            "verdict": verdict, "signal": signal}
    png = cap_mod.save_artifact(final, meta, out_dir, slug)
    return {"status": "ok", "png": png, "concept": concept, "verdict": verdict,
            "signal": signal}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/satirist && python -m pytest tests/test_pipeline.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/satirist/satirist/pipeline.py apps/satirist/tests/test_pipeline.py
git commit -m "feat(satirist): pipeline orchestration (signal->brain->judge->render->caption)"
```

---

### Task 7: Render module (GPU) + S3 LoRA fetch

**Files:**
- Create: `apps/satirist/satirist/render.py`
- Test: `apps/satirist/tests/test_render_smoke.py`

This is the ONLY GPU-dependent code. It is NOT exercised in CI. The test only asserts the module imports and exposes the right callables; the actual diffusers run happens on the GPU box (runbook in Task 9).

- [ ] **Step 1: Write the failing test**

```python
# apps/satirist/tests/test_render_smoke.py
import inspect
import satirist.render as render


def test_render_exposes_callables_with_expected_signatures():
    assert callable(render.render_sdxl)
    assert callable(render.fetch_lora)
    # render_sdxl(image_prompt, out_path, lora_path=None) — image_prompt + out_path required
    params = list(inspect.signature(render.render_sdxl).parameters)
    assert params[:2] == ["image_prompt", "out_path"]
    fp = list(inspect.signature(render.fetch_lora).parameters)
    assert fp[:2] == ["s3_uri", "dest"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/satirist && python -m pytest tests/test_render_smoke.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'satirist.render'`

- [ ] **Step 3: Write minimal implementation**

Heavy imports (torch/diffusers) are done INSIDE the functions so the module imports fine on the dev machine (where torch is absent) and the smoke test passes.

```python
# apps/satirist/satirist/render.py
"""GPU render: SDXL base + Nast Hand LoRA via diffusers. Runs on a CUDA box only.
Heavy imports are lazy so this module imports on machines without torch/diffusers."""
import os
import subprocess

from . import config


def fetch_lora(s3_uri: str = None, dest: str = None) -> str:
    """Download the LoRA safetensors from S3 to `dest` (skips if already present). Returns dest."""
    s3_uri = s3_uri or config.LORA_S3_URI
    dest = dest or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "var",
                                "nast_sdxl.safetensors")
    dest = os.path.abspath(dest)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    subprocess.run(["aws", "s3", "cp", s3_uri, dest, "--only-show-errors"], check=True)
    return dest


def render_sdxl(image_prompt: str, out_path: str, lora_path: str = None,
                steps: int = 30, guidance: float = 6.0, seed: int = 0) -> str:
    """Load SDXL + the Nast LoRA, generate one image from image_prompt, save to out_path. GPU only."""
    import torch
    from diffusers import StableDiffusionXLPipeline

    lora_path = lora_path or fetch_lora()
    pipe = StableDiffusionXLPipeline.from_pretrained(
        config.SDXL_BASE, torch_dtype=torch.float16, use_safetensors=True).to("cuda")
    pipe.load_lora_weights(lora_path)
    gen = torch.Generator(device="cuda").manual_seed(seed)
    image = pipe(prompt=image_prompt, num_inference_steps=steps,
                 guidance_scale=guidance, generator=gen).images[0]
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    image.save(out_path)
    return out_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/satirist && python -m pytest tests/test_render_smoke.py -q`
Expected: PASS (1 passed) — torch/diffusers are not imported at module load, so this passes without a GPU.

- [ ] **Step 5: Commit**

```bash
git add apps/satirist/satirist/render.py apps/satirist/tests/test_render_smoke.py
git commit -m "feat(satirist): GPU SDXL+LoRA render module (lazy imports) + S3 LoRA fetch"
```

---

### Task 8: CLI

**Files:**
- Create: `apps/satirist/satirist/cli.py`
- Test: `apps/satirist/tests/test_pipeline.py` (extend with a `--dry-run`-style placeholder render test)

`--dry-run` swaps the GPU render for a placeholder image so the full loop runs end-to-end on the dev machine. `--no-judge` skips the taste judge. `--ingest-feed URL` populates the store first.

- [ ] **Step 1: Write the failing test**

```python
# append to apps/satirist/tests/test_pipeline.py
from satirist.cli import placeholder_render
from PIL import Image


def test_placeholder_render_writes_png(tmp_path):
    out = str(tmp_path / "p.png")
    placeholder_render("a tiger labeled TAMMANY, thomas_nast_style", out)
    img = Image.open(out)
    assert img.size[0] > 0 and img.size[1] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/satirist && python -m pytest tests/test_pipeline.py::test_placeholder_render_writes_png -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'satirist.cli'`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/satirist/satirist/cli.py
"""CLI for the satirist creative loop.

  python -m satirist.cli --topic "Tammany" [--ingest-feed URL] [--no-judge] [--dry-run]

--dry-run swaps the GPU render for a placeholder image so the loop runs without a GPU.
"""
import argparse
import json
import sys
import textwrap

from PIL import Image, ImageDraw

from . import config
from .brain import ideate
from .judge import score_concept
from .pipeline import run


def placeholder_render(image_prompt: str, out_path: str) -> str:
    """Non-GPU stand-in: writes the image_prompt as text onto a gray canvas."""
    img = Image.new("RGB", (768, 768), (210, 210, 210))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "PLACEHOLDER RENDER (no GPU)\n\n" + "\n".join(
        textwrap.wrap(image_prompt, width=70)[:24]), fill=(20, 20, 20))
    img.save(out_path)
    return out_path


def main(argv=None):
    ap = argparse.ArgumentParser(prog="satirist")
    ap.add_argument("--topic", required=True)
    ap.add_argument("--ingest-feed", default=None, help="RSS/Atom URL to ingest before selecting")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="placeholder render (no GPU)")
    ap.add_argument("--db", default=config.DB_PATH)
    ap.add_argument("--out", default=config.OUT_DIR)
    args = ap.parse_args(argv)

    if args.ingest_feed:
        import intake_core.pipeline as ip
        import intake_core.store as store
        store.init_db(args.db)
        ip.ingest_feed(args.ingest_feed, args.db)

    if args.dry_run:
        render_fn = placeholder_render
    else:
        from .render import render_sdxl
        render_fn = lambda prompt, out_path: render_sdxl(prompt, out_path)

    judge_fn = None if args.no_judge else score_concept
    res = run(args.topic, render_fn=render_fn, brain_fn=ideate,
              judge_fn=judge_fn, db_path=args.db, out_dir=args.out)
    print(json.dumps({k: v for k, v in res.items() if k != "signal"}, indent=2, default=str))
    return 0 if res["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/satirist && python -m pytest tests/test_pipeline.py -q`
Expected: PASS (all pipeline tests, incl. the new placeholder test).

- [ ] **Step 5: Commit**

```bash
git add apps/satirist/satirist/cli.py apps/satirist/tests/test_pipeline.py
git commit -m "feat(satirist): CLI with --dry-run placeholder render + --ingest-feed + --no-judge"
```

---

### Task 9: Full suite green + GPU runbook

**Files:**
- Modify: `apps/satirist/README.md` (append the GPU runbook)

- [ ] **Step 1: Run the full suite**

Run: `cd apps/satirist && python -m pytest -q`
Expected: PASS — all tests across signal_select, brain, judge, caption, pipeline, render_smoke. (Render's actual diffusers path is intentionally NOT run here.)

- [ ] **Step 2: Append the GPU runbook to the README**

```markdown
<!-- append to apps/satirist/README.md -->

## GPU Runbook (real render)

The render step needs a CUDA box (the studio ComfyUI box `i-030994c5371ee5de9`,
or any g6.2xlarge). The dev machine and CI never run it.

1. On the box: `pip install diffusers torch transformers accelerate safetensors boto3 Pillow`
   and `pip install intake-spine` (or `pip install -e` the intake-spine repo).
2. Ensure the box's role/credentials can read `s3://ilyrium-slm-foundry/...` (the LoRA).
3. Ensure the Nast Brain is reachable: either run Ollama on the box (`ollama serve` + the
   `nast-brain` model imported) or set `BRAIN_URL` to a reachable host.
4. Set `OPENROUTER_API_KEY` if you want the taste judge (omit / pass `--no-judge` to skip).
5. Run:
   ```
   python -m satirist.cli --topic "Tammany" --ingest-feed https://example.com/politics.rss
   ```
   Output PNG + sidecar JSON land in `apps/satirist/var/output/`.

Cost note: stop or terminate the GPU box when done (see slm-foundry infra scripts) —
the volume bills even when stopped.
```

- [ ] **Step 3: Commit**

```bash
git add apps/satirist/README.md
git commit -m "docs(satirist): GPU render runbook + full suite green"
```

- [ ] **Step 4: Push**

```bash
git push origin <branch>
```

---

## Spec Coverage Self-Review

- **§10 step 1 (select signal / RAG):** Task 2 (`select_signal` over `intake_core.store.get_signals`); CLI `--ingest-feed` populates the store (Task 8). ✓
- **§10 step 2 (ideate via Nast Brain):** Task 3 (`ideate` → Ollama `nast-brain`, robust JSON parse). ✓
- **§10 step 3 (render via SDXL Hand LoRA):** Task 7 (`render_sdxl` + `fetch_lora` from S3, trigger `thomas_nast_style`), GPU-only. ✓
- **§10 step 4 (composite/caption + save):** Task 5 (`compose_caption_banner`, `save_artifact` PNG + sidecar JSON). In-image label overlay explicitly deferred. ✓
- **§3B per-artifact eval loop (critique→revise):** Task 4 (judge rubric + verdict) wired into Task 6 (one revise round below threshold). ✓
- **Manual-publish governance gate:** v1 saves artifacts to disk only; no auto-publish — manual review is the gate. ✓ (No publish code is in scope.)
- **Separation of pure logic vs network/GPU:** Brain/judge/render injected into `pipeline.run`; all logic unit-tested with fakes; only `cli.py` touches network/GPU by default. ✓

**Placeholder scan:** none — every code step is complete.

**Type consistency:** concept dict `{allegory_rationale, image_prompt[, caption]}` consistent across brain/judge/pipeline; verdict `{score, rationale}` consistent across judge/pipeline; signal `{id, media_item_id, topic, entities, summary}` consistent with `intake_core.store`. `render_fn(image_prompt, out_path)`, `brain_fn(event, revise_hint="")`, `judge_fn(concept)` signatures match between `pipeline.run`, the tests, and `cli.py`. ✓
