# Nast Reference Pack — Phase 2 (The Hand) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]` checkboxes.

**Goal:** Train two Thomas Nast **style LoRAs** — one for **SDXL**, one for **Flux** — from public-domain Harper's Weekly scans, and serve them via Ilyrium's ComfyUI so any image renders in Nast's 1870s wood-engraving style.

**Architecture:** Shape B (vision). Pipeline: LOC image scrape → crop/clean → dual-style captioning (tag-style for SDXL, natural-language for Flux, both with a `thomas_nast_style` trigger) → Kohya/ai-toolkit LoRA training on the EC2 L4 → LoRA safetensors → S3 → ComfyUI.

**Tech Stack:** Library of Congress JSON API, Pillow, a vision LLM for captioning (via OpenRouter), Kohya_ss (SDXL) + ai-toolkit/Kohya-flux (Flux), SDXL 1.0 + Flux.1, AWS L4 + S3, ComfyUI.

**Scope:** Phase 2 only. Phase 3 (orchestration + template extraction) is a separate plan.

---

## DECISIONS / BLOCKERS to resolve before training (Tasks 5–6)
- **HF token:** SDXL 1.0 download is ungated; **Flux.1-dev is GATED** (must accept the license on Hugging Face + supply an HF token). **Recommendation:** use **Flux.1-schnell (Apache-2.0, ungated)** to avoid the gate, OR provide an HF token in `.env` (`HF_TOKEN=`) and accept the Flux.1-dev license. Flag at Task 6.
- **Flux VRAM:** Flux (12B) LoRA on the L4 (24 GB) requires fp8/low-VRAM settings and is slow; if it won't fit, run that one LoRA on a one-off L40S (48 GB). SDXL trains comfortably.
- **Captioning model:** use a **vision LLM via OpenRouter** (e.g. `anthropic/claude-sonnet-4.6`, which is vision-capable) to caption scans — avoids standing up local WD14/BLIP. Confirm the slug accepts image input.

---

## File Structure
- `src/data_sources/loc_fetch.py` — add `download_images()` (extends existing search/parse).
- `packs/nast/hand/caption.py` — dual-style captioner (tag + NL) via vision LLM.
- `packs/nast/hand/prepare_images.py` — crop/normalize scans → training folder.
- `infra/bootstrap_vision.sh` — install Kohya + deps on the box.
- `packs/nast/hand/sdxl_lora.toml` — Kohya SDXL LoRA config.
- `packs/nast/hand/flux_lora.yaml` — ai-toolkit/Kohya Flux LoRA config.
- `packs/nast/data/hand/` — scans + captions (gitignored → S3).
- Tests: `tests/test_loc_images.py`, `tests/test_caption.py`.

---

## Task 1: LOC image downloader (`src/data_sources/loc_fetch.py`)

**Files:** Modify `src/data_sources/loc_fetch.py`; Test `tests/test_loc_images.py`

- [ ] **Step 1: failing test**
```python
# tests/test_loc_images.py
from src.data_sources.loc_fetch import safe_filename

def test_safe_filename_from_item():
    it = {"id": "http://www.loc.gov/item/2002695175/", "title": "The Tammany Tiger Loose!"}
    fn = safe_filename(it, 3)
    assert fn.endswith(".jpg") and " " not in fn and fn.startswith("003_")
    assert "tammany" in fn.lower()
```

- [ ] **Step 2: run, confirm FAIL** — `python -m pytest tests\test_loc_images.py -v`

- [ ] **Step 3: implement** — add to `loc_fetch.py`:
```python
import re, urllib.request, pathlib

def safe_filename(item: dict, idx: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", item.get("title", "").lower()).strip("-")[:40] or "nast"
    return f"{idx:03d}_{slug}.jpg"

def download_images(items: list[dict], out_dir: str) -> int:
    out = pathlib.Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    n = 0
    for i, it in enumerate(items):
        if not it.get("image_url"):
            continue
        dest = out / safe_filename(it, i)
        try:
            req = urllib.request.Request(it["image_url"], headers={"User-Agent": "slm-foundry/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
                f.write(r.read())
            n += 1
        except Exception as e:
            print(f"  skip {dest.name}: {e}")
    return n
```

- [ ] **Step 4: run, confirm PASS** — `python -m pytest tests\test_loc_images.py -v`
- [ ] **Step 5: commit** — `git add src/data_sources/loc_fetch.py tests/test_loc_images.py && git commit -m "feat(data): LOC image downloader"`

## Task 2: Fetch + prepare scans
- [ ] **Step 1:** run the scraper to pull ~80 Nast scans (local, no GPU):
```bash
python -c "from src.data_sources.loc_fetch import search_loc, download_images; items=search_loc('Thomas Nast', pages=2); print('downloaded', download_images(items, 'packs/nast/data/hand/raw'))"
```
- [ ] **Step 2:** `packs/nast/hand/prepare_images.py` — center-crop/resize to 1024px, drop tiny/low-res, output to `packs/nast/data/hand/train/`. (Pillow; deterministic; testable on a synthetic image.)
- [ ] **Step 3:** manual cull — review thumbnails, keep 50–80 clean single-panel engravings. `log()` how many dropped.
- [ ] **Step 4:** S3: `aws s3 cp packs/nast/data/hand/train s3://ilyrium-slm-foundry/data/nast/hand/ --recursive`

## Task 3: Dual-style captioner (`packs/nast/hand/caption.py`)
- [ ] **Step 1: failing test** (`tests/test_caption.py`) for `build_caption(tags, trigger, style)`:
```python
from packs.nast.hand.caption import build_caption
def test_tag_style():
    c = build_caption(["roaring tiger","spiked collar"], "thomas_nast_style", "sdxl")
    assert c.startswith("thomas_nast_style, ") and "roaring tiger" in c
def test_nl_style():
    c = build_caption(["a roaring tiger with a spiked collar"], "thomas_nast_style", "flux")
    assert c.startswith("thomas_nast_style") and c.endswith(".")
```
- [ ] **Step 2–4:** implement `build_caption` (tag = trigger + comma tags; NL = trigger + sentence) + `caption_image(path, style)` that base64-encodes the image and calls a vision LLM via OpenRouter for raw tags/description; write `<image>.txt` next to each scan. Run twice (sdxl tag-style, flux NL-style) into separate caption sets. Commit.

## Task 4: Install Kohya on the box (`infra/bootstrap_vision.sh`)
- [ ] **Step 1:** write `bootstrap_vision.sh`: clone kohya_ss (sd-scripts), create venv `~/vlora`, `pip install` torch + kohya deps + ai-toolkit (for Flux). Commit.
- [ ] **Step 2:** start box, scp scans+captions (or `aws s3 sync` via the instance role), run bootstrap. Verify `accelerate` + `sd-scripts` import.

## Task 5: SDXL LoRA (`packs/nast/hand/sdxl_lora.toml`)
- [ ] **Step 1:** write Kohya SDXL config (base = `stabilityai/stable-diffusion-xl-base-1.0`, network_dim 16, 1024 res, ~10 epochs over the scan set, trigger in captions).
- [ ] **Step 2:** train on box: `accelerate launch sdxl_train_network.py --config_file packs/nast/hand/sdxl_lora.toml`. Verify a `.safetensors` LoRA (~100–200 MB) is produced.
- [ ] **Step 3:** smoke-test render in ComfyUI/diffusers with the LoRA + trigger; eyeball Nast style.
- [ ] **Step 4:** push to S3: `aws s3 cp <sdxl_lora>.safetensors s3://ilyrium-slm-foundry/models/nast/hand/sdxl/`.

## Task 6: Flux LoRA (`packs/nast/hand/flux_lora.yaml`)
- [ ] **Step 1 (BLOCKER CHECK):** resolve Flux base — Flux.1-schnell (ungated) or Flux.1-dev (needs HF token + license). Set the base accordingly.
- [ ] **Step 2:** write ai-toolkit/Kohya-flux config (fp8/low-VRAM for the L4; NL captions).
- [ ] **Step 3:** train; if OOM on the L4, relaunch the box as **g6e.2xlarge (L40S 48 GB)** for this run only.
- [ ] **Step 4:** smoke-test render; push LoRA to S3 `.../hand/flux/`.

## Task 7: Register + stop box
- [ ] Append two rows to `registry/models.csv` (nast-hand-sdxl, nast-hand-flux) with base, scan count, S3 paths.
- [ ] `aws ec2 stop-instances ...`.

## Exit criteria
- Two Nast style LoRAs in S3 (SDXL + Flux), each producing recognizably 1870s-wood-engraving output in ComfyUI, registered. Box stopped.

**Next plan:** Phase 3 — orchestration (`satirist.py`: event → Brain → Hand → cartoon) + extract `packs/_template/`.
