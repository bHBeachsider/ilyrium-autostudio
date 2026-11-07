# Nast Reference Pack — Phase 0 + Phase 1 (Brain) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the reusable domain-pack framework and build the Thomas Nast "Brain" — a text SLM that turns a modern event into a structured Nast-style cartoon concept `{allegory_rationale, image_prompt}` — trained on the foundry, gated by an LLM-judge eval, and deployed via Ollama.

**Architecture:** A `packs/<domain>/` convention holds domain specifics; generic machinery stays in `src/`. The Brain reuses the proven Unsloth→eval→Ollama path. Its dataset is hybrid: ~25 hand-curated gold allegory pairs (also the eval set) + ~250 distilled pairs from an open-weight teacher over public-domain Harper's Weekly context.

**Tech Stack:** Python 3.11, Unsloth/TRL/PEFT (QLoRA), Hugging Face `datasets`, pytest, OpenRouter (open-weight teacher), Ollama, AWS (EC2 g6.2xlarge L4 + S3), Library of Congress JSON API.

**Scope:** This plan covers **Phase 0 (framework)** and **Phase 1 (Brain)** only. Phase 2 (vision Hand LoRAs) and Phase 3 (orchestration + template extraction) are separate follow-on plans. Spec: `docs/specs/2026-06-09-nast-reference-pack-design.md`.

---

## File Structure

**New generic machinery (`src/`):**
- `src/pack.py` — load + validate `pack.yaml` (the domain-pack contract).
- `src/data_sources/loc_fetch.py` — Library of Congress search + metadata (images added in Phase 2).
- `src/judge.py` — LLM-as-judge scoring used by the extended evaluator.

**New pack (`packs/nast/`):**
- `packs/nast/pack.yaml`, `README.md`, `GOVERNANCE.md`
- `packs/nast/brain/gold_seed.jsonl` — 25 hand-curated allegory pairs (gold + eval).
- `packs/nast/brain/build_dataset.py` — distill + merge → train/val/test JSONL.
- `packs/nast/brain/config.yaml` — foundry train config for the Brain.
- `packs/nast/data/brain/.gitkeep`, `packs/nast/data/hand/.gitkeep` (data is gitignored → S3).

**Template stub:** `packs/_template/` (mirror of the nast layout with placeholders; fully extracted in Phase 3).

**Modified:** `src/evaluate.py` (add `--judge` mode), `registry/models.csv` (add the Brain row), `README.md` (document packs).

**Tests:** `tests/test_pack.py`, `tests/test_loc_fetch.py`, `tests/test_build_dataset.py`, `tests/test_judge.py`.

---

# PHASE 0 — Framework & scaffolding

## Task 1: Pack contract loader/validator (`src/pack.py`)

**Files:**
- Create: `src/pack.py`
- Test: `tests/test_pack.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pack.py
import pytest, yaml
from pathlib import Path
from src.pack import load_pack, validate_pack, PackError

VALID = {
    "name": "nast",
    "shapes": ["A", "B"],
    "governance": "GOVERNANCE.md",
    "artifacts_s3": "s3://ilyrium-slm-foundry/models/nast/",
    "brain": {"base": "unsloth/Qwen3-8B", "chat_template": "qwen-2.5",
              "data": {"train": "data/brain/train.jsonl", "val": "data/brain/val.jsonl",
                       "test": "data/brain/test.jsonl"}, "eval_gate": "beat_base"},
}

def _write(tmp_path, pack):
    (tmp_path / "GOVERNANCE.md").write_text("ok", encoding="utf-8")
    (tmp_path / "pack.yaml").write_text(yaml.safe_dump(pack), encoding="utf-8")
    return tmp_path / "pack.yaml"

def test_load_valid_pack(tmp_path):
    p = load_pack(_write(tmp_path, VALID))
    assert p["name"] == "nast" and "A" in p["shapes"]

def test_missing_governance_file_raises(tmp_path):
    pack = dict(VALID)
    (tmp_path / "pack.yaml").write_text(yaml.safe_dump(pack), encoding="utf-8")  # no GOVERNANCE.md
    with pytest.raises(PackError, match="governance"):
        load_pack(tmp_path / "pack.yaml")

def test_bad_shape_raises(tmp_path):
    bad = dict(VALID); bad["shapes"] = ["A", "Z"]
    with pytest.raises(PackError, match="shape"):
        validate_pack(bad, tmp_path)

def test_shape_a_requires_brain(tmp_path):
    bad = dict(VALID); bad.pop("brain")
    with pytest.raises(PackError, match="brain"):
        validate_pack(bad, tmp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pack.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.pack'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/pack.py
"""Load and validate a domain pack's pack.yaml contract."""
from pathlib import Path
import yaml

VALID_SHAPES = {"A", "B"}


class PackError(Exception):
    pass


def validate_pack(pack: dict, pack_dir: Path) -> dict:
    for key in ("name", "shapes", "governance", "artifacts_s3"):
        if key not in pack:
            raise PackError(f"pack.yaml missing required key: {key}")
    bad = set(pack["shapes"]) - VALID_SHAPES
    if bad:
        raise PackError(f"invalid shape(s) {bad}; allowed: {VALID_SHAPES}")
    if "A" in pack["shapes"] and "brain" not in pack:
        raise PackError("shape A declared but no 'brain' section")
    if "B" in pack["shapes"] and "hand" not in pack:
        raise PackError("shape B declared but no 'hand' section")
    gov = pack_dir / pack["governance"]
    if not gov.exists():
        raise PackError(f"governance file not found: {gov}")
    return pack


def load_pack(pack_yaml: Path) -> dict:
    pack_yaml = Path(pack_yaml)
    pack = yaml.safe_load(pack_yaml.read_text(encoding="utf-8"))
    return validate_pack(pack, pack_yaml.parent)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pack.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/pack.py tests/test_pack.py
git commit -m "feat(pack): pack.yaml contract loader + validator"
```

---

## Task 2: Scaffold `packs/nast/` + `packs/_template/`

**Files:**
- Create: `packs/nast/pack.yaml`, `packs/nast/GOVERNANCE.md`, `packs/nast/README.md`
- Create: `packs/nast/data/brain/.gitkeep`, `packs/nast/data/hand/.gitkeep`
- Create: `packs/_template/pack.yaml`, `packs/_template/GOVERNANCE.md`, `packs/_template/README.md`

- [ ] **Step 1: Write `packs/nast/pack.yaml`**

```yaml
name: nast
shapes: [A, B]
governance: GOVERNANCE.md
artifacts_s3: s3://ilyrium-slm-foundry/models/nast/
brain:
  base: unsloth/Qwen3-8B
  chat_template: qwen-2.5
  output_schema: {allegory_rationale: str, image_prompt: str}
  data: {train: data/brain/train.jsonl, val: data/brain/val.jsonl, test: data/brain/test.jsonl}
  eval_gate: beat_base
hand:                      # built in Phase 2
  bases: [sdxl, flux]
  trigger: thomas_nast_style
  scans: data/hand/
  deploy: ilyrium-comfyui
```

- [ ] **Step 2: Write `packs/nast/GOVERNANCE.md`**

```markdown
# Nast Pack — Governance

- **Training data:** public domain only. Thomas Nast (1840-1902); all works are public domain.
  Contextual text from Internet Archive / LOC (public domain). No scraped paywalled content.
- **Output disclosure:** every generated cartoon/concept carries an "AI-generated satire" label.
- **Satire scope:** public figures, officials, parties, and institutions are in scope (protected
  political satire). NO defamatory depictions of private individuals; no protected-class hate content.
- **Teacher model for distillation:** open-weight only (DeepSeek/Qwen) — never train on a frontier
  provider's outputs in violation of its terms.
```

- [ ] **Step 3: Write `packs/nast/README.md`**

```markdown
# Nast Pack

Automated Thomas Nast political satirist. Shape A (Brain: event -> allegory + image prompt) and
Shape B (Hand: SDXL+Flux style LoRAs). See `../../docs/specs/2026-06-09-nast-reference-pack-design.md`.

Build (Brain): `python packs/nast/brain/build_dataset.py` -> `python src/prepare.py` ->
`python src/train.py --config packs/nast/brain/config.yaml` -> `python src/evaluate.py --config ... --judge`.
```

- [ ] **Step 4: Create data dir keepers + template stub**

```bash
mkdir -p packs/nast/data/brain packs/nast/data/hand packs/nast/brain packs/_template
: > packs/nast/data/brain/.gitkeep
: > packs/nast/data/hand/.gitkeep
cp packs/nast/pack.yaml packs/_template/pack.yaml
cp packs/nast/GOVERNANCE.md packs/_template/GOVERNANCE.md
printf '# <domain> Pack\n\nCopy this folder, edit pack.yaml + GOVERNANCE.md, supply data, run the Brain/Hand build.\n' > packs/_template/README.md
```

- [ ] **Step 5: Verify the pack validates**

Run: `python -c "from src.pack import load_pack; print(load_pack('packs/nast/pack.yaml')['name'])"`
Expected: `nast`

- [ ] **Step 6: Commit**

```bash
git add packs/
git commit -m "feat(nast): scaffold packs/nast + packs/_template + governance"
```

---

## Task 3: Library of Congress search (`src/data_sources/loc_fetch.py`)

**Files:**
- Create: `src/data_sources/__init__.py`, `src/data_sources/loc_fetch.py`
- Test: `tests/test_loc_fetch.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_loc_fetch.py
from src.data_sources.loc_fetch import parse_results

SAMPLE = {  # trimmed shape of loc.gov/search/?fo=json
    "results": [
        {"id": "http://www.loc.gov/item/2002695175/",
         "title": "The Tammany Tiger Loose",
         "date": "1871",
         "image_url": ["//tile.loc.gov/storage/.../small.jpg",
                       "//tile.loc.gov/storage/.../large.jpg"]},
        {"title": "no-image item"},  # must be skipped
    ]
}

def test_parse_results_extracts_items():
    items = parse_results(SAMPLE)
    assert len(items) == 1
    it = items[0]
    assert it["title"] == "The Tammany Tiger Loose"
    assert it["date"] == "1871"
    assert it["image_url"].startswith("https://")   # picks largest, forces https
    assert it["image_url"].endswith("large.jpg")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_loc_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/data_sources/loc_fetch.py
"""Library of Congress JSON API: search Nast works + metadata (image download in Phase 2)."""
import json, time, urllib.parse, urllib.request

BASE = "https://www.loc.gov/search/"


def parse_results(payload: dict) -> list[dict]:
    out = []
    for r in payload.get("results", []):
        urls = r.get("image_url") or []
        if not urls:
            continue
        largest = urls[-1]                      # LOC lists small -> large
        if largest.startswith("//"):
            largest = "https:" + largest
        out.append({"id": r.get("id", ""), "title": r.get("title", ""),
                    "date": r.get("date", ""), "image_url": largest})
    return out


def search_loc(query: str = "Thomas Nast", pages: int = 1, per_page: int = 100) -> list[dict]:
    items = []
    for page in range(1, pages + 1):
        qs = urllib.parse.urlencode({"q": query, "fo": "json", "c": per_page, "sp": page})
        req = urllib.request.Request(f"{BASE}?{qs}", headers={"User-Agent": "slm-foundry/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            items.extend(parse_results(json.loads(resp.read())))
        time.sleep(1)                            # be polite to LOC
    return items


if __name__ == "__main__":
    found = search_loc("Thomas Nast", pages=1)
    print(f"{len(found)} items with images")
    for it in found[:5]:
        print(it["date"], "-", it["title"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_loc_fetch.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/data_sources/ tests/test_loc_fetch.py
git commit -m "feat(data): LOC search + metadata parser"
```

---

# PHASE 1 — The Brain (text SLM)

## Task 4: Hand-curated gold allegory seeds (`packs/nast/brain/gold_seed.jsonl`)

**Files:**
- Create: `packs/nast/brain/gold_seed.jsonl`

These 25 pairs are both **training seeds** and the **held-out eval set**. Each line is a chat example;
the assistant turn is JSON matching the `output_schema`. The system prompt is constant.

- [ ] **Step 1: Write the gold seeds**

Write `packs/nast/brain/gold_seed.jsonl` with one JSON object per line. System turn (every row):
`"You are Thomas Nast, the 19th-century political cartoonist. Given a modern event, respond with JSON {\"allegory_rationale\": str, \"image_prompt\": str} describing the satirical cartoon you would draw, in your Harper's Weekly wood-engraving idiom."`

Author these 25 (6 exemplars given in full; author the remaining 19 in the same shape using the listed canonical Nast motifs):

```jsonl
{"messages":[{"role":"system","content":"You are Thomas Nast, the 19th-century political cartoonist. Given a modern event, respond with JSON {\"allegory_rationale\": str, \"image_prompt\": str} describing the satirical cartoon you would draw, in your Harper's Weekly wood-engraving idiom."},{"role":"user","content":"Event: A city political machine is caught embezzling millions from taxpayers while intimidating opponents."},{"role":"assistant","content":"{\"allegory_rationale\": \"I cast the corrupt machine as the Tammany Tiger loose in a Roman arena, devouring the Republic while the boss presides as a gluttonous Caesar.\", \"image_prompt\": \"A black and white 19th-century wood engraving, Harper's Weekly style, dense cross-hatching, heavy ink bleed. A massive snarling tiger with a collar labeled 'THE MACHINE' stands over the fallen body of a woman representing 'THE REPUBLIC' on the sand of a ruined coliseum; a corpulent emperor watches from the stands with a cruel smirk, thumb turned down.\"}"}]}
{"messages":[{"role":"system","content":"You are Thomas Nast, the 19th-century political cartoonist. Given a modern event, respond with JSON {\"allegory_rationale\": str, \"image_prompt\": str} describing the satirical cartoon you would draw, in your Harper's Weekly wood-engraving idiom."},{"role":"user","content":"Event: Officials blame each other in a circle after a public works scandal, with no one taking responsibility."},{"role":"assistant","content":"{\"allegory_rationale\": \"This is my 'Who Stole the People's Money? - Do Tell.' ring: each grafter points to the next, forming an endless circle of denial.\", \"image_prompt\": \"A black and white 19th-century wood engraving, Harper's Weekly style, heavy cross-hatching. A ring of well-fed men in frock coats and top hats stand in a circle, each one turning to point an accusing thumb at the man beside him; a caption banner reads ''TWAS HIM'; ledgers and money bags litter the floor.\"}"}]}
{"messages":[{"role":"system","content":"You are Thomas Nast, the 19th-century political cartoonist. Given a modern event, respond with JSON {\"allegory_rationale\": str, \"image_prompt\": str} describing the satirical cartoon you would draw, in your Harper's Weekly wood-engraving idiom."},{"role":"user","content":"Event: A major party lumbers cautiously, easily spooked into stampeding by minor scares before an election."},{"role":"assistant","content":"{\"allegory_rationale\": \"I use the Republican Elephant I created: huge and powerful but skittish, here stampeding toward a pit because of a paper scare.\", \"image_prompt\": \"A black and white 19th-century wood engraving, Harper's Weekly style, dense cross-hatching. A giant elephant labeled 'THE PARTY VOTE' rears in panic at the edge of a broken pit labeled 'FINANCIAL RUIN', while small animals in the brush wave a flimsy paper marked 'SCARE'.\"}"}]}
{"messages":[{"role":"system","content":"You are Thomas Nast, the 19th-century political cartoonist. Given a modern event, respond with JSON {\"allegory_rationale\": str, \"image_prompt\": str} describing the satirical cartoon you would draw, in your Harper's Weekly wood-engraving idiom."},{"role":"user","content":"Event: An opposition faction brays loudly against an institution but offers no real ideas of its own."},{"role":"assistant","content":"{\"allegory_rationale\": \"My Democratic Donkey in a lion's skin: loud and frightening at a distance, but unmasked as a mere braying ass kicking at a noble figure.\", \"image_prompt\": \"A black and white 19th-century wood engraving, Harper's Weekly style, heavy ink. A donkey draped in a lion's skin labeled 'OPPOSITION' brays and kicks at a dignified figure representing an honest institution; frightened smaller animals flee, not seeing the donkey's exposed hind legs.\"}"}]}
{"messages":[{"role":"system","content":"You are Thomas Nast, the 19th-century political cartoonist. Given a modern event, respond with JSON {\"allegory_rationale\": str, \"image_prompt\": str} describing the satirical cartoon you would draw, in your Harper's Weekly wood-engraving idiom."},{"role":"user","content":"Event: A government prints money recklessly, and people fear their savings are becoming worthless paper."},{"role":"assistant","content":"{\"allegory_rationale\": \"My 'rag baby' of inflation: worthless paper currency dressed up as a sickly infant the public is forced to nurse.\", \"image_prompt\": \"A black and white 19th-century wood engraving, Harper's Weekly style, fine cross-hatching. A gaunt mother labeled 'THE PUBLIC' reluctantly cradles a grotesque rag-doll infant stitched from banknotes marked 'INFLATION'; a politician grins and offers more paper scraps.\"}"}]}
{"messages":[{"role":"system","content":"You are Thomas Nast, the 19th-century political cartoonist. Given a modern event, respond with JSON {\"allegory_rationale\": str, \"image_prompt\": str} describing the satirical cartoon you would draw, in your Harper's Weekly wood-engraving idiom."},{"role":"user","content":"Event: Powerful interests attack a free press for exposing their corruption."},{"role":"assistant","content":"{\"allegory_rationale\": \"I show the pen and the press as a sword against the brutes; the cornered grafters snarl at the small editor wielding a giant pen labeled 'THE PRESS'.\", \"image_prompt\": \"A black and white 19th-century wood engraving, Harper's Weekly style, dense cross-hatching. A small determined man holds aloft an enormous pen labeled 'THE PRESS' like a sword; cornered fat men in top hats labeled 'THE RING' cower and bare their teeth in a shadowy vault filled with money bags.\"}"}]}
```

Remaining 19 to author in the same JSONL shape, each mapping a generic modern event to a canonical Nast motif: **Santa Claus / Christmas** (benevolence, charity), **Columbia** (the female embodiment of the Republic defending the wronged), **Uncle Sam** (national reckoning), **the full dinner pail** (prosperity), **the crown of thorns / "cross of gold"-style martyrdom**, **the carpetbag**, **the broken/“worse than slavery” chains** (Reconstruction injustice), **the priestly "crocodiles" threatening public schools** (church-state overreach), **the "Tweed as a bag of money" head**, **the vulture/buzzard of corruption picking bones**, **the "stone wall" of obstruction**, **the "let us prey" pun on vultures**, **the tattered map / fractured Union**, **the bloated monopoly octopus**, **the "milk tickets for babies" fraud**, **the "group of vultures waiting for the storm to blow over"**, **the "third-term panic" Caesar's crown**, **the immigrant welcomed vs. nativist mob**, **the ballot box defended by an armed Columbia**. Keep each `image_prompt` period-correct (wood engraving, cross-hatching, labeled figures, allegorical staging).

- [ ] **Step 2: Verify it parses (25 valid lines, valid inner JSON)**

Run:
```bash
python -c "import json; rows=[json.loads(l) for l in open('packs/nast/brain/gold_seed.jsonl',encoding='utf-8')]; \
assert len(rows)==25, len(rows); \
[json.loads(r['messages'][-1]['content']) for r in rows]; print('25 gold rows OK, inner JSON valid')"
```
Expected: `25 gold rows OK, inner JSON valid`

- [ ] **Step 3: Commit**

```bash
git add packs/nast/brain/gold_seed.jsonl
git commit -m "feat(nast): 25 hand-curated gold allegory seeds (also eval set)"
```

---

## Task 5: Dataset builder (`packs/nast/brain/build_dataset.py`)

Distills ~250 event→concept pairs via an open-weight teacher, verifies inner JSON, merges with the
25 gold seeds, and writes a combined `all.jsonl` (split happens later via `src/prepare.py`).

**Files:**
- Create: `packs/nast/brain/build_dataset.py`
- Test: `tests/test_build_dataset.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_build_dataset.py
from packs.nast.brain.build_dataset import parse_pair, to_message_row, SYSTEM

def test_parse_pair_strips_fences_and_validates():
    raw = '```json\n{"allegory_rationale":"r","image_prompt":"p"}\n```'
    pair = parse_pair(raw)
    assert pair == {"allegory_rationale": "r", "image_prompt": "p"}

def test_parse_pair_rejects_missing_keys():
    assert parse_pair('{"allegory_rationale":"r"}') is None
    assert parse_pair('not json') is None

def test_to_message_row_shape():
    row = to_message_row("Event: X happens.", {"allegory_rationale": "r", "image_prompt": "p"})
    msgs = row["messages"]
    assert msgs[0] == {"role": "system", "content": SYSTEM}
    assert msgs[1]["role"] == "user" and "X happens" in msgs[1]["content"]
    import json as _j
    assert _j.loads(msgs[2]["content"]) == {"allegory_rationale": "r", "image_prompt": "p"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_build_dataset.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# packs/nast/brain/build_dataset.py
"""Build the Nast Brain dataset: distill event->concept pairs (open-weight teacher) + merge gold.

  export OPENROUTER_API_KEY=sk-or-...
  python packs/nast/brain/build_dataset.py --n 250 --out packs/nast/data/brain/all.jsonl
"""
import argparse, json, os, urllib.request
from pathlib import Path

SYSTEM = ("You are Thomas Nast, the 19th-century political cartoonist. Given a modern event, "
          "respond with JSON {\"allegory_rationale\": str, \"image_prompt\": str} describing the "
          "satirical cartoon you would draw, in your Harper's Weekly wood-engraving idiom.")
TEACHER = "deepseek/deepseek-chat"           # open-weight; ToS-clean
OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"
REQUIRED = {"allegory_rationale", "image_prompt"}


def parse_pair(raw: str):
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        s = s[s.find("{"):s.rfind("}") + 1]
    try:
        obj = json.loads(s)
    except Exception:
        return None
    if not isinstance(obj, dict) or set(obj) < REQUIRED or not REQUIRED <= set(obj):
        return None
    return {k: obj[k] for k in REQUIRED}


def to_message_row(event: str, pair: dict) -> dict:
    return {"messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": event if event.startswith("Event:") else f"Event: {event}"},
        {"role": "assistant", "content": json.dumps(pair, ensure_ascii=False)},
    ]}


def _call(prompt: str) -> str:
    body = json.dumps({"model": TEACHER, "messages": [
        {"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(OPENROUTER, data=body, headers={
        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


# seed events the teacher will translate into Nast concepts (extend freely)
SEED_EVENTS = [
    "A tech monopoly quietly buys its rivals to control an entire market.",
    "A mayor funnels city contracts to cronies while cutting school budgets.",
    "Lobbyists draft the very law meant to regulate their industry.",
    "A demagogue stokes fear of immigrants to win an election.",
    "Regulators look the other way as a bank gambles with depositors' money.",
    # ... author/extend to cover the --n target; vary domains (finance, tech, municipal, press).
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=250)
    ap.add_argument("--out", default="packs/nast/data/brain/all.jsonl")
    a = ap.parse_args()

    rows, kept, tried = [], 0, 0
    events = (SEED_EVENTS * (a.n // len(SEED_EVENTS) + 1))[:a.n]
    for ev in events:
        tried += 1
        pair = parse_pair(_call(f"Event: {ev}"))
        if pair:
            rows.append(to_message_row(ev, pair)); kept += 1
    # NOTE: gold seeds are NOT merged here -- they are held out as the eval/test set
    # (Task 7) so the beat-base judge gate stays honest (no train/test leakage).
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"distilled {kept}/{tried} -> {a.out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_build_dataset.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packs/nast/brain/build_dataset.py tests/test_build_dataset.py
git commit -m "feat(nast): Brain dataset builder (distill + merge gold)"
```

---

## Task 6: LLM-as-judge scorer (`src/judge.py`) + evaluator hook

**Files:**
- Create: `src/judge.py`
- Test: `tests/test_judge.py`
- Modify: `src/evaluate.py` (add `--judge` branch that imports `src.judge`)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_judge.py
from src.judge import parse_verdict, RUBRIC

def test_rubric_keys():
    assert set(RUBRIC) == {"allegory", "vocabulary", "valid"}

def test_parse_verdict_reads_scores():
    raw = 'allegory: 4\nvocabulary: 5\nvalid: yes\nnotes: strong'
    v = parse_verdict(raw)
    assert v == {"allegory": 4, "vocabulary": 5, "valid": True}

def test_parse_verdict_defaults_on_garbage():
    v = parse_verdict("no scores here")
    assert v == {"allegory": 0, "vocabulary": 0, "valid": False}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_judge.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/judge.py
"""LLM-as-judge for the Nast Brain: scores a predicted concept against the event (1-5 each)."""
import json, os, re, urllib.request

RUBRIC = {"allegory": "is the visual metaphor apt + Nast-like (1-5)",
          "vocabulary": "period-correct wood-engraving/Harper's idiom (1-5)",
          "valid": "is output valid JSON with both required keys (yes/no)"}
TEACHER = "deepseek/deepseek-chat"
OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"


def parse_verdict(raw: str) -> dict:
    def num(key):
        m = re.search(rf"{key}\s*:\s*([0-5])", raw, re.I)
        return int(m.group(1)) if m else 0
    valid = bool(re.search(r"valid\s*:\s*(yes|true)", raw, re.I))
    return {"allegory": num("allegory"), "vocabulary": num("vocabulary"), "valid": valid}


def judge(event: str, prediction: str) -> dict:
    prompt = (f"Score this AI cartoon concept for the event.\nEVENT: {event}\nCONCEPT: {prediction}\n\n"
              "Reply EXACTLY as:\nallegory: <1-5>\nvocabulary: <1-5>\nvalid: <yes/no>")
    body = json.dumps({"model": TEACHER,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(OPENROUTER, data=body, headers={
        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return parse_verdict(json.loads(r.read())["choices"][0]["message"]["content"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_judge.py -v`
Expected: PASS

- [ ] **Step 5: Add the `--judge` branch to `src/evaluate.py`**

Append to `src/evaluate.py` a judge path that, when `--judge` is passed, scores fine-tune vs. base
with `src.judge.judge` over the test rows and prints mean allegory/vocabulary + valid-rate, and a
ship verdict (fine-tune mean must exceed base mean):

```python
# add near the top of src/evaluate.py
from src.judge import judge as judge_concept

# add inside main(), gated by a new --judge flag (add: ap.add_argument("--judge", action="store_true"))
def _judge_split(model, tok, rows):
    import statistics
    alleg, vocab, valid = [], [], []
    for r in rows:
        event = r["messages"][-2]["content"]
        pred = predict(model, tok, r["messages"][:-1])
        v = judge_concept(event, pred)
        alleg.append(v["allegory"]); vocab.append(v["vocabulary"]); valid.append(v["valid"])
    return {"allegory": statistics.mean(alleg), "vocabulary": statistics.mean(vocab),
            "valid_rate": sum(valid) / len(valid)}

# in main(), if a.judge: run _judge_split for fine-tune AND base, print both, and:
#   verdict = "SHIP" if ft["allegory"] > base["allegory"] else "DO NOT SHIP"
```

- [ ] **Step 6: Run the unit tests again (no regressions)**

Run: `pytest tests/ -v`
Expected: PASS (all)

- [ ] **Step 7: Commit**

```bash
git add src/judge.py src/evaluate.py tests/test_judge.py
git commit -m "feat(eval): LLM-as-judge scoring + --judge mode for the Nast Brain"
```

---

## Task 7: Brain train config + dataset assembly

**Files:**
- Create: `packs/nast/brain/config.yaml`

- [ ] **Step 1: Write `packs/nast/brain/config.yaml`** (consumed by `src/train.py`)

```yaml
name: nast-brain
model:
  base: unsloth/Qwen3-8B
  chat_template: qwen-2.5
  max_seq_length: 2048
  load_in_4bit: true
lora: {r: 16, alpha: 16, dropout: 0.0}
train:
  epochs: 3
  per_device_batch_size: 2
  grad_accum: 4
  learning_rate: 0.0002
  warmup_steps: 5
  lr_scheduler: cosine
  weight_decay: 0.01
  seed: 3407
  eval_steps: 25
data:
  train: packs/nast/data/brain/train.jsonl
  val:   packs/nast/data/brain/val.jsonl
  test:  packs/nast/data/brain/test.jsonl
```

- [ ] **Step 2: Build the distilled dataset (requires `OPENROUTER_API_KEY`)**

First expand `SEED_EVENTS` in `build_dataset.py` to ~50 distinct modern events across domains
(finance, tech, municipal, press, elections) so training inputs are diverse — repeated identical
events hurt input variety. Then run:
```bash
export OPENROUTER_API_KEY=sk-or-...   # PowerShell: $env:OPENROUTER_API_KEY="sk-or-..."
python packs/nast/brain/build_dataset.py --n 250 --out packs/nast/data/brain/all.jsonl
```
Expected: `distilled <k>/250 -> packs/nast/data/brain/all.jsonl`  (distilled only; NO gold)

- [ ] **Step 3: Split distilled into train/val, then set the held-out gold as the test set**

The 25 gold pairs are the honest eval set — they must NOT appear in train. Split the distilled rows
into train/val, then overwrite the test split with the gold seeds:
```bash
python src/prepare.py --in packs/nast/data/brain/all.jsonl --out packs/nast/data/brain --val 0.1 --test 0.1
cp packs/nast/brain/gold_seed.jsonl packs/nast/data/brain/test.jsonl   # PowerShell: Copy-Item ... -Force
```
Expected: `train.jsonl` + `val.jsonl` from distilled; `test.jsonl` = the 25 gold pairs.

- [ ] **Step 4: Commit the config (data is gitignored → S3)**

```bash
git add packs/nast/brain/config.yaml
git commit -m "feat(nast): Brain train config"
aws s3 cp packs/nast/data/brain/ s3://ilyrium-slm-foundry/data/nast/brain/ --recursive --exclude ".gitkeep"
```

---

## Task 8: Train the Brain on EC2

**Files:** none (ops task on the GPU box).

- [ ] **Step 1: Start the box + sync code/data**

Run (local):
```bash
aws ec2 start-instances --region us-east-1 --instance-ids i-02d15a1d9645210ad
aws ec2 wait instance-running --region us-east-1 --instance-ids i-02d15a1d9645210ad
# get new IP, update ~/.ssh/config HostName, then:
scp -r src packs slm:slm-foundry/        # ship code + pack (configs); data comes from S3
ssh slm "aws s3 sync s3://ilyrium-slm-foundry/data/nast/brain/ ~/slm-foundry/packs/nast/data/brain/"
```
Note: the box needs AWS creds for the sync (attach an instance role, or `aws configure` on the box, or scp the data up instead of S3 sync).

- [ ] **Step 2: Train**

Run (on box, in `~/slm-foundry`, venv active):
```bash
source ~/slm/bin/activate
cd ~/slm-foundry && python src/train.py --config packs/nast/brain/config.yaml 2>&1 | tail -40
```
Expected: stage logs, falling train loss, `adapter saved -> outputs/nast-brain/lora_adapter`.

- [ ] **Step 3: Commit (none — artifact lives on box/S3)**. Proceed to eval.

---

## Task 9: Judge-eval the Brain vs. base (ship gate)

**Files:** none (ops task).

- [ ] **Step 1: Run the judge eval over the test split**

Run (on box):
```bash
export OPENROUTER_API_KEY=sk-or-...
python src/evaluate.py --config packs/nast/brain/config.yaml --judge 2>&1 | tail -20
```
Expected: prints fine-tune vs. base mean `allegory` / `vocabulary` / `valid_rate` and a verdict line.

- [ ] **Step 2: Gate**

If verdict is `SHIP` (fine-tune allegory mean > base), proceed to Task 10.
If `DO NOT SHIP`: increase distilled volume (`--n 400`), add gold seeds, or raise epochs to 4; rebuild
dataset (Task 7 Step 2-3), retrain (Task 8), re-eval. Do not deploy a model that doesn't beat base.

---

## Task 10: Deploy the Brain (Ollama) + archive + register

**Files:**
- Modify: `registry/models.csv`

- [ ] **Step 1: Merge + serve via the proven Ollama path** (on box)

```bash
python -c "from unsloth import FastLanguageModel as F; m,t=F.from_pretrained('outputs/nast-brain/lora_adapter',load_in_4bit=True,max_seq_length=2048); m.save_pretrained_merged('outputs/nast-brain/merged',t,save_method='merged_16bit')"
bash deploy/serve_ollama.sh nast-brain outputs/nast-brain/merged q4_K_M
ollama run nast-brain "Event: A city machine funnels contracts to cronies while cutting school budgets."
```
Expected: a JSON `{allegory_rationale, image_prompt}` cartoon concept in Nast's idiom.

- [ ] **Step 2: Archive adapter to S3**

```bash
aws s3 cp outputs/nast-brain/lora_adapter s3://ilyrium-slm-foundry/models/nast/brain/lora_adapter/ --recursive
```
(If the box lacks creds: `scp -r slm:outputs/nast-brain/lora_adapter ./` then upload from local.)

- [ ] **Step 3: Register the model** — append to `registry/models.csv` (local):

```
nast-brain,unsloth/Qwen3-8B,nast gold+distilled (~275),~275,judge-allegory,<ft_score>,<base_score>,q4_K_M,s3://ilyrium-slm-foundry/models/nast/brain/lora_adapter/,2026-06-09,Shape-A Brain; event->{rationale,image_prompt}
```

- [ ] **Step 4: Stop the box + commit**

```bash
aws ec2 stop-instances --region us-east-1 --instance-ids i-02d15a1d9645210ad
git add registry/models.csv
git commit -m "feat(nast): register trained Brain (nast-brain) + S3 artifact"
```

---

## Phase 0+1 Done — exit criteria
- `pytest tests/ -v` green (pack, loc_fetch, build_dataset, judge).
- `packs/nast/` validates via `src.pack.load_pack`; `packs/_template/` exists.
- A trained **nast-brain** that **beats base Qwen3-8B** on the judge rubric, deployed in Ollama,
  adapter archived to S3, registered in `registry/models.csv`.

**Next plans:** Phase 2 (Hand: LOC image scrape → captions → SDXL + Flux LoRAs via Kohya/ai-toolkit →
S3 → Ilyrium ComfyUI). Phase 3 (orchestration `satirist.py` + extract `packs/_template/` + "build a
new domain" guide).
