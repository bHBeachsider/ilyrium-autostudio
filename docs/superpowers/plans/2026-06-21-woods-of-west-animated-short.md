# "The Woods of the West" Animated Short — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the 6-panel comic into a ~2-minute 16:9 animated short, produced via a 3-style bake-off then a full render in the winning style, using local Wan 2.2 image-to-video (no content filter) + ElevenLabs voices.

**Architecture:** A self-contained film package at `apps/auto-studio/films/woods_of_west/` defines the script as data (characters, styles, shots, dialogue) and a driver that runs the pipeline: Fal nano-banana character sheets → per-shot Fal keyframe stills (style + character-locked) → Wan 2.2 i2v clips in local ComfyUI → ElevenLabs dialogue → `post_production.compile_final_video` master. The only change to existing code is extending `media/comfyui_renderer.py` to support image-to-video (upload a start image + inject it into the workflow); everything else is new, additive code that reuses existing renderer/audio/compile functions.

**Tech Stack:** Python 3.13 (auto-studio venv), ComfyUI + Wan 2.2 (self-hosted on EC2 g6.2xlarge via SSH tunnel at `http://127.0.0.1:8188`), fal.ai nano-banana-pro/edit (Gemini 3 Pro Image), ElevenLabs TTS, moviepy 2.x, pytest.

## Global Constraints

- **Working dir for all code/tests:** `apps/auto-studio/` — modules import as `from media.x import ...` and `from ec2_session import ...`; this only resolves when `apps/auto-studio` is on `sys.path` / is the cwd. The driver must `sys.path.insert(0, <auto-studio>)` and `os.chdir(<auto-studio>)` (mirror `studio_pipeline_service.py:42-44`).
- **Run tests with:** `cd apps/auto-studio && venv/Scripts/python -m pytest <path> -v` (Windows venv; Git-Bash path form).
- **Dialogue is verbatim** from the comic — never rewrite a line. The lines are fixed in `script.py` (Task 2).
- **Aspect ratio:** 16:9 for every still and clip.
- **Punchline renders as-is** — local Wan/ComfyUI only for video; never route the punchline shot through a filtered cloud renderer.
- **Output root:** `apps/auto-studio/outputs/woods_of_west/` (created by the driver, never committed).
- **No secrets in code:** `FAL_KEY`, `ELEVENLABS_API_KEY`, AWS creds come from `.env` (loaded by `dotenv`), never hardcoded.
- **Reuse, don't fork:** call existing `render_voiceover`, `edit_image_fal`, `compile_final_video`; extend (don't duplicate) `comfyui_renderer.py`.
- **Commit convention:** conventional commits; co-author trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## File Structure

| Path | Responsibility |
|---|---|
| `apps/auto-studio/media/comfyui_renderer.py` (modify) | Add image upload + `render_i2v_comfyui()`; refactor submit/poll/download into `_run_workflow()`. |
| `apps/auto-studio/comfyui_workflows/wan22_i2v_api.json` (new, generated in ComfyUI) | API-format Wan 2.2 i2v workflow with `__PROMPT__` and `__IMAGE__` tokens. |
| `apps/auto-studio/films/woods_of_west/__init__.py` (new) | Package marker. |
| `apps/auto-studio/films/woods_of_west/script.py` (new) | Pure data: `CHARACTERS`, `STYLES`, `SHOTS`; selectors `shots_for_phase`, `style_prefix`. |
| `apps/auto-studio/films/woods_of_west/characters.py` (new) | `build_character_sheets(style, out_dir)` via Fal. |
| `apps/auto-studio/films/woods_of_west/keyframes.py` (new) | `generate_shot_keyframe(shot, style, char_refs, out_dir)` via Fal edit. |
| `apps/auto-studio/films/woods_of_west/voices.py` (new) | `VOICE_CAST` map + `render_shot_dialogue(shot, out_dir)`. |
| `apps/auto-studio/films/woods_of_west/render_film.py` (new) | Driver: Phase 1 bake-off + Phase 2 full film; CLI. |
| `apps/auto-studio/films/woods_of_west/tests/` (new) | pytest unit tests for the pure logic. |

---

## Task 1: Extend ComfyUI renderer for image-to-video

**Files:**
- Modify: `apps/auto-studio/media/comfyui_renderer.py`
- Test: `apps/auto-studio/films/woods_of_west/tests/test_comfyui_i2v.py`

**Interfaces:**
- Consumes: existing module-level helpers `is_comfyui_up`, `COMFYUI_URL`, `_first_output_file`.
- Produces:
  - `upload_comfyui_image(image_path: str, base: str) -> str` — POSTs to `{base}/upload/image`, returns the stored filename ComfyUI reports.
  - `render_i2v_comfyui(image_path: str, visual_prompt: str, scene_number: int, output_dir: str = ".", output_name: str = None, workflow_path: str = None, url: str = None, timeout: int = 1200) -> str` — uploads `image_path`, injects `__IMAGE__`+`__PROMPT__`, runs the workflow, returns saved mp4 path.

- [ ] **Step 1: Write the failing test**

```python
# apps/auto-studio/films/woods_of_west/tests/test_comfyui_i2v.py
import json
import types
import builtins
import pytest
from media import comfyui_renderer as cr


def test_inject_tokens_replaces_image_and_prompt():
    wf = '{"6": {"inputs": {"text": "__PROMPT__"}}, "52": {"inputs": {"image": "__IMAGE__"}}}'
    out = cr._inject_tokens(wf, visual_prompt='a "smug" sheriff', image_name="kf_01.png")
    parsed = json.loads(out)
    assert parsed["6"]["inputs"]["text"] == 'a "smug" sheriff'   # quotes survive JSON-safe inject
    assert parsed["52"]["inputs"]["image"] == "kf_01.png"


def test_render_i2v_requires_image_file(tmp_path):
    with pytest.raises(RuntimeError, match="image"):
        cr.render_i2v_comfyui(str(tmp_path / "missing.png"), "prompt", 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/auto-studio && venv/Scripts/python -m pytest films/woods_of_west/tests/test_comfyui_i2v.py -v`
Expected: FAIL — `_inject_tokens` / `render_i2v_comfyui` do not exist (AttributeError).

- [ ] **Step 3: Refactor shared run logic + add token injection (no behavior change to existing fn)**

In `comfyui_renderer.py`, add these helpers above `render_scene_comfyui` (after `_first_output_file`):

```python
def _inject_tokens(wf_text: str, visual_prompt: str, image_name: str = None) -> str:
    """JSON-safe replacement of __PROMPT__ (and optionally __IMAGE__) tokens."""
    wf_text = wf_text.replace("__PROMPT__", json.dumps(visual_prompt)[1:-1])
    if image_name is not None:
        wf_text = wf_text.replace("__IMAGE__", json.dumps(image_name)[1:-1])
    return wf_text


def _run_workflow(workflow: dict, scene_number: int, base: str, output_dir: str,
                  output_name: str, timeout: int) -> str:
    """Submit a parsed workflow, poll history, download the produced file."""
    import requests
    client_id = str(uuid.uuid4())
    resp = requests.post(base + "/prompt", json={"prompt": workflow, "client_id": client_id}, timeout=30)
    resp.raise_for_status()
    prompt_id = resp.json()["prompt_id"]

    deadline = time.time() + timeout
    outputs = None
    while time.time() < deadline:
        hist = requests.get(f"{base}/history/{prompt_id}", timeout=15).json()
        if prompt_id in hist:
            outputs = hist[prompt_id].get("outputs")
            break
        time.sleep(2)
    if not outputs:
        raise RuntimeError(f"ComfyUI render timed out after {timeout}s for scene {scene_number}.")

    file_info = _first_output_file(outputs)
    if not file_info:
        raise RuntimeError(f"ComfyUI produced no output file for scene {scene_number}.")
    params = {
        "filename": file_info["filename"],
        "subfolder": file_info.get("subfolder", ""),
        "type": file_info.get("type", "output"),
    }
    data = requests.get(base + "/view", params=params, timeout=300)
    data.raise_for_status()
    os.makedirs(output_dir, exist_ok=True)
    ext = os.path.splitext(file_info["filename"])[1] or ".mp4"
    out = os.path.join(output_dir, output_name or f"scene_{scene_number}{ext}")
    with open(out, "wb") as f:
        f.write(data.content)
    print(f"✅ [COMFYUI] Scene {scene_number} saved as {out}")
    return out


def upload_comfyui_image(image_path: str, base: str) -> str:
    """Upload a start frame to ComfyUI's input store; return the stored filename."""
    import requests
    with open(image_path, "rb") as fh:
        files = {"image": (os.path.basename(image_path), fh, "image/png")}
        r = requests.post(base + "/upload/image", files={**files, "overwrite": (None, "true")}, timeout=60)
    r.raise_for_status()
    info = r.json()  # {"name": "...", "subfolder": "", "type": "input"}
    name = info["name"]
    sub = info.get("subfolder")
    return f"{sub}/{name}" if sub else name
```

- [ ] **Step 4: Add `render_i2v_comfyui`**

Append to `comfyui_renderer.py`:

```python
def render_i2v_comfyui(image_path: str, visual_prompt: str, scene_number: int,
                       output_dir: str = ".", output_name: str = None,
                       workflow_path: str = None, url: str = None, timeout: int = 1200) -> str:
    """Wan 2.2 image-to-video: upload `image_path` as the start frame, inject the
    motion prompt, run the workflow, return the saved clip path."""
    if not os.path.exists(image_path):
        raise RuntimeError(f"Start image not found: {image_path}")
    base = (url or COMFYUI_URL).rstrip("/")
    if not is_comfyui_up(base):
        raise RuntimeError(
            f"ComfyUI is not reachable at {base}. Start the EC2 GPU + open the tunnel "
            f"(ilyrium-ec2-session) and make sure ComfyUI is listening on 8188.")
    wf_path = workflow_path or os.getenv("COMFYUI_I2V_WORKFLOW", "comfyui_workflows/wan22_i2v_api.json")
    if not os.path.exists(wf_path):
        raise RuntimeError(
            f"Wan i2v workflow not found at '{wf_path}'. Export it from ComfyUI (Save API Format), "
            f"put __PROMPT__ in the positive CLIPTextEncode and __IMAGE__ in the LoadImage 'image' field.")
    image_name = upload_comfyui_image(image_path, base)
    with open(wf_path, "r", encoding="utf-8") as f:
        wf_text = f.read()
    workflow = json.loads(_inject_tokens(wf_text, visual_prompt, image_name))
    print(f"\n🎨 [COMFYUI-i2v] Scene {scene_number}: {os.path.basename(image_path)} → video on {base}…")
    return _run_workflow(workflow, scene_number, base, output_dir, output_name, timeout)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd apps/auto-studio && venv/Scripts/python -m pytest films/woods_of_west/tests/test_comfyui_i2v.py -v`
Expected: PASS (2 passed). The missing-image test raises `RuntimeError` matching "image"; injection test confirms token replacement.

- [ ] **Step 6: Sanity-check the existing text path still imports**

Run: `cd apps/auto-studio && venv/Scripts/python -c "import media.comfyui_renderer as c; print(c.render_scene_comfyui.__name__, c.render_i2v_comfyui.__name__)"`
Expected: `render_scene_comfyui render_i2v_comfyui`

- [ ] **Step 7: Commit**

```bash
git add apps/auto-studio/media/comfyui_renderer.py apps/auto-studio/films/woods_of_west/tests/test_comfyui_i2v.py
git commit -m "feat(comfyui): add Wan i2v image-to-video render path (upload + token inject)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Export & tokenize the Wan 2.2 i2v workflow (ComfyUI, manual)

**Files:**
- Create: `apps/auto-studio/comfyui_workflows/wan22_i2v_api.json`

This task is performed in the ComfyUI web UI on the GPU box; it has no unit test (it's a generated asset). It is gated by the EC2 box being up and the tunnel open.

- [ ] **Step 1: Bring the GPU box + ComfyUI up**

Run: `cd apps/auto-studio && venv/Scripts/python -c "import ec2_session as e; print(e.ensure_running()); print('comfyui_up', e.is_comfyui_up())"`
Expected: state `running`; then open the SSH tunnel via the `ilyrium-ec2-session` skill until `comfyui_up True`.

- [ ] **Step 2: Load the blueprint, set resolution to 16:9, add tokens**

In ComfyUI: Open `ComfyUI/blueprints/Image to Video (Wan 2.2).json`. Then:
1. Set the `WanImageToVideo` width/height to a 16:9 pair (e.g. 832×480 for bake-off speed; 1280×720 for final).
2. In the **positive** `CLIPTextEncode` node, replace its text with the literal token `__PROMPT__`.
3. In the **LoadImage** node, set its `image` field to the literal `__IMAGE__` (type the token as the filename).
4. Leave the negative `CLIPTextEncode` as a fixed quality-negative.

- [ ] **Step 3: Export API format**

ComfyUI menu → **Save (API Format)** → save as `apps/auto-studio/comfyui_workflows/wan22_i2v_api.json`.

- [ ] **Step 4: Verify the asset**

Run: `cd apps/auto-studio && venv/Scripts/python -c "import json; t=open('comfyui_workflows/wan22_i2v_api.json',encoding='utf-8').read(); import sys; assert '__PROMPT__' in t and '__IMAGE__' in t, 'missing tokens'; d=json.loads(t); assert any(n.get('class_type')=='WanImageToVideo' for n in d.values()), 'no WanImageToVideo node'; print('workflow OK', len(d), 'nodes')"`
Expected: `workflow OK <N> nodes` (no assertion error).

- [ ] **Step 5: Commit**

```bash
git add apps/auto-studio/comfyui_workflows/wan22_i2v_api.json
git commit -m "chore(comfyui): tokenized Wan 2.2 i2v API workflow for woods-of-west

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Film script as data

**Files:**
- Create: `apps/auto-studio/films/woods_of_west/__init__.py` (empty)
- Create: `apps/auto-studio/films/woods_of_west/script.py`
- Test: `apps/auto-studio/films/woods_of_west/tests/test_script.py`

**Interfaces:**
- Produces:
  - `CHARACTERS: dict[str, str]` — id → look description (shakes, pringle, cal).
  - `STYLES: dict[str, str]` — id → style prefix string (ballpoint, cartoon, cinematic).
  - `SHOTS: list[dict]` — each `{id:int, beat:str, phase:str, speaker:str|None, line:str|None, characters:list[str], visual:str, motion:str}`. `phase` is `"bakeoff"` for the signature beat shots, `"film"` otherwise.
  - `shots_for_phase(phase: str) -> list[dict]` — `"bakeoff"` returns only bakeoff shots; `"film"` returns ALL shots (bakeoff shots are part of the full film too).
  - `style_prefix(style: str) -> str` — raises `KeyError` if unknown.

- [ ] **Step 1: Write the failing test**

```python
# apps/auto-studio/films/woods_of_west/tests/test_script.py
import pytest
from films.woods_of_west import script as s


def test_dialogue_is_verbatim():
    lines = {sh["line"] for sh in s.SHOTS if sh["line"]}
    assert "You wouldn't shoot a man with serious wood..." in lines
    assert "Sheriff Pringle... well well..." in lines
    assert "Oh yeah? Why's that?" in lines


def test_phases_partition():
    bake = s.shots_for_phase("bakeoff")
    film = s.shots_for_phase("film")
    assert all(sh["phase"] == "bakeoff" for sh in bake)
    assert len(bake) >= 2                      # signature beat is 2-3 shots
    assert len(film) > len(bake)               # full film is the superset
    assert {sh["id"] for sh in bake} <= {sh["id"] for sh in film}


def test_three_styles_present():
    assert set(s.STYLES) == {"ballpoint", "cartoon", "cinematic"}
    assert s.style_prefix("cartoon")
    with pytest.raises(KeyError):
        s.style_prefix("nope")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/auto-studio && venv/Scripts/python -m pytest films/woods_of_west/tests/test_script.py -v`
Expected: FAIL — module `films.woods_of_west.script` does not exist (ModuleNotFoundError).

- [ ] **Step 3: Create the package marker + script module**

Create empty `apps/auto-studio/films/__init__.py` and `apps/auto-studio/films/woods_of_west/__init__.py`.

Create `apps/auto-studio/films/woods_of_west/script.py`:

```python
"""'The Woods of the West' — film script as data. Dialogue is verbatim from the comic."""

CHARACTERS = {
    "shakes": ("Shakes: scruffy grey-bearded old prospector, battered tan cowboy hat, "
               "gap-toothed, wiry, jabbing a bony finger; comic-relief informant"),
    "pringle": ("Sheriff Pringle: tall gaunt lawman, very long pointed nose, droopy "
                "half-lidded eyes, light shirt with tie, star-badge cowboy hat; deadpan"),
    "cal": ("Cal Dalton: lean villain, tall black stovepipe top hat, handlebar mustache, "
            "dark vest and trousers, weathered glare"),
}

STYLES = {
    "ballpoint": ("hand-drawn ballpoint-pen sketch on lined notebook paper, wobbly ink "
                  "lines, faint blue horizontal rule lines, white paper texture, crude "
                  "charming doodle style"),
    "cartoon": ("clean flat 2D cartoon, bold black outlines, simple cel shading, limited "
                "color palette, Saturday-morning animation look"),
    "cinematic": ("painterly stylized western illustration, warm dusty palette, dramatic "
                  "golden-hour light, cinematic depth, hand-painted texture"),
}

# phase: "bakeoff" = the signature beat rendered in all 3 styles; also part of the full film.
SHOTS = [
    {"id": 1, "beat": "cold_open", "phase": "film", "speaker": None, "line": None,
     "characters": [], "visual": "black screen fading to a distant steam train on the horizon at dusk, wide desert",
     "motion": "slow push-in, heat shimmer, faint smoke drifting"},
    {"id": 2, "beat": "cold_open", "phase": "film", "speaker": None, "line": None,
     "characters": [], "visual": "the 4:55 steam train hissing into a dusty wooden depot, steam billowing across the platform",
     "motion": "steam billows toward camera, train wheels slow to a stop"},
    {"id": 3, "beat": "cold_open", "phase": "film", "speaker": None, "line": None,
     "characters": ["cal"], "visual": "a stovepipe-top-hat silhouette (Cal Dalton) stepping down from the train onto the platform",
     "motion": "boot lands, dust puffs, the figure straightens to full height"},
    {"id": 4, "beat": "warning", "phase": "film", "speaker": "shakes",
     "line": "Sheriff!! Ol' Cal Dalton just arrived on the 4:55, says he's got an old score to settle with you!!",
     "characters": ["shakes"], "visual": "jail office interior, Shakes bursting through the door pointing urgently",
     "motion": "Shakes lurches forward, arm jabbing, mouth moving"},
    {"id": 5, "beat": "warning", "phase": "film", "speaker": "pringle",
     "line": "Well, Shakes, I guess the time has come to play this hand...",
     "characters": ["pringle"], "visual": "Sheriff Pringle at the office window, deadpan, looking out at the street",
     "motion": "slow turn of the head toward the window, faint squint"},
    {"id": 6, "beat": "walk", "phase": "film", "speaker": None, "line": None,
     "characters": [], "visual": "empty dusty main street, shutters closing, a tumbleweed rolling through",
     "motion": "tumbleweed rolls across frame, a shutter bangs closed"},
    {"id": 7, "beat": "walk", "phase": "film", "speaker": None, "line": None,
     "characters": [], "visual": "tight insert of spurred boots and a ticking wall clock reading near 5",
     "motion": "spur rowel spins, clock pendulum swings"},
    {"id": 8, "beat": "walk", "phase": "film", "speaker": "cal",
     "line": "Sheriff Pringle... well well...",
     "characters": ["cal", "pringle"], "visual": "wide two-shot down the street: Cal facing Sheriff Pringle at a distance",
     "motion": "Cal walks slowly forward, coat shifting in the wind"},
    {"id": 9, "beat": "walk", "phase": "film", "speaker": "pringle",
     "line": "H'lo, Cal...",
     "characters": ["pringle"], "visual": "medium of Sheriff Pringle, hand resting near his holster, calm",
     "motion": "slight nod, eyes narrowing"},
    {"id": 10, "beat": "faceoff", "phase": "film", "speaker": "cal",
     "line": "It's been a while, but now it's payback time...",
     "characters": ["cal"], "visual": "close-up of Cal Dalton, menacing under the top hat brim",
     "motion": "lips curl into a sneer, mustache twitches"},
    {"id": 11, "beat": "faceoff", "phase": "film", "speaker": "pringle",
     "line": "You wouldn't shoot me, Cal...",
     "characters": ["pringle"], "visual": "close-up of Sheriff Pringle, unbothered, droopy-eyed",
     "motion": "tiny smirk forming"},
    {"id": 12, "beat": "faceoff", "phase": "film", "speaker": "cal",
     "line": "Oh yeah? Why's that?",
     "characters": ["cal"], "visual": "close-up of Cal, eyebrow raised, gun hand twitching",
     "motion": "head tilts, eyes flick down then up"},
    # --- signature beat (bake-off) ---
    {"id": 13, "beat": "punchline", "phase": "bakeoff", "speaker": "pringle",
     "line": "You wouldn't shoot a man with serious wood...",
     "characters": ["cal", "pringle"], "visual": "two-shot standoff, Sheriff Pringle smug and confident facing Cal",
     "motion": "Pringle's smug grin widens, slight hip shift"},
    {"id": 14, "beat": "punchline", "phase": "bakeoff", "speaker": None, "line": None,
     "characters": ["cal", "pringle"], "visual": "the faithful comic reveal — a lumpy cartoon outline at the sheriff's trousers, framed exactly like the strip; Cal recoils",
     "motion": "Cal's eyes bulge, he flinches back; Pringle stands proud"},
    {"id": 15, "beat": "punchline", "phase": "bakeoff", "speaker": None, "line": None,
     "characters": ["cal"], "visual": "Cal Dalton flabbergasted, slowly lowering his pistol, defeated",
     "motion": "gun hand droops, shoulders slump"},
    {"id": 16, "beat": "end", "phase": "film", "speaker": None, "line": None,
     "characters": [], "visual": "freeze on the dusty street, hand-lettered 'END' card over the frame",
     "motion": "gentle freeze, slight film-grain flicker"},
]


def shots_for_phase(phase: str) -> list:
    if phase == "bakeoff":
        return [sh for sh in SHOTS if sh["phase"] == "bakeoff"]
    if phase == "film":
        return list(SHOTS)
    raise ValueError(f"unknown phase: {phase!r} (use 'bakeoff' or 'film')")


def style_prefix(style: str) -> str:
    return STYLES[style]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd apps/auto-studio && venv/Scripts/python -m pytest films/woods_of_west/tests/test_script.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/auto-studio/films/__init__.py apps/auto-studio/films/woods_of_west/__init__.py apps/auto-studio/films/woods_of_west/script.py apps/auto-studio/films/woods_of_west/tests/test_script.py
git commit -m "feat(film): woods-of-west script as data (characters, styles, shots)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Voice casting & dialogue audio

**Files:**
- Create: `apps/auto-studio/films/woods_of_west/voices.py`
- Test: `apps/auto-studio/films/woods_of_west/tests/test_voices.py`

**Interfaces:**
- Consumes: `media.audio_generator.render_voiceover(text, scene_number, output_dir, output_name, voice_id, stability, similarity, style)`; `script.SHOTS`.
- Produces:
  - `VOICE_CAST: dict[str, dict]` — speaker id → `{voice_id, stability, similarity}`.
  - `render_shot_dialogue(shot: dict, out_dir: str) -> str | None` — returns the mp3 path, or `None` when the shot has no spoken line (`shot["line"]` is falsy).

- [ ] **Step 1: Write the failing test**

```python
# apps/auto-studio/films/woods_of_west/tests/test_voices.py
from films.woods_of_west import voices


def test_cast_covers_all_speakers():
    from films.woods_of_west import script
    speakers = {sh["speaker"] for sh in script.SHOTS if sh["speaker"]}
    assert speakers <= set(voices.VOICE_CAST)


def test_silent_shot_returns_none(monkeypatch):
    called = {"n": 0}
    monkeypatch.setattr(voices, "render_voiceover", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or "x.mp3")
    out = voices.render_shot_dialogue({"id": 6, "speaker": None, "line": None}, "/tmp")
    assert out is None and called["n"] == 0


def test_spoken_shot_calls_tts_with_cast(monkeypatch):
    captured = {}
    def fake(text, scene_number, output_dir, output_name=None, voice_id=None, **k):
        captured.update(text=text, voice_id=voice_id, output_name=output_name)
        return f"{output_dir}/{output_name}"
    monkeypatch.setattr(voices, "render_voiceover", fake)
    shot = {"id": 13, "speaker": "pringle", "line": "You wouldn't shoot a man with serious wood..."}
    out = voices.render_shot_dialogue(shot, "/tmp/aud")
    assert captured["text"].startswith("You wouldn't shoot")
    assert captured["voice_id"] == voices.VOICE_CAST["pringle"]["voice_id"]
    assert out.endswith("shot13.mp3")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/auto-studio && venv/Scripts/python -m pytest films/woods_of_west/tests/test_voices.py -v`
Expected: FAIL — module `films.woods_of_west.voices` does not exist.

- [ ] **Step 3: Implement voices.py**

```python
"""ElevenLabs voice casting for the three characters. voice_ids are starting picks
from the ElevenLabs prebuilt library — audition and swap in Task 7 if needed."""

from media.audio_generator import render_voiceover

VOICE_CAST = {
    # Shakes: gravelly, frantic old-timer  (prebuilt "Clyde")
    "shakes": {"voice_id": "2EiwWnXFnvU5JabPnv8n", "stability": 0.45, "similarity": 0.85},
    # Pringle: dry, slow deadpan drawl, older  (prebuilt "Bill")
    "pringle": {"voice_id": "pqHfZKP75CvOlQylNhV4", "stability": 0.80, "similarity": 0.85},
    # Cal: low, menacing, smug  (prebuilt "Adam")
    "cal": {"voice_id": "pNInz6obpgDQGcFmaJgB", "stability": 0.70, "similarity": 0.85},
}


def render_shot_dialogue(shot: dict, out_dir: str):
    """Synthesize the shot's line with its cast voice. Returns the mp3 path, or
    None for silent shots."""
    if not shot.get("line"):
        return None
    cast = VOICE_CAST[shot["speaker"]]
    return render_voiceover(
        text=shot["line"],
        scene_number=shot["id"],
        output_dir=out_dir,
        output_name=f"shot{shot['id']}.mp3",
        voice_id=cast["voice_id"],
        stability=cast["stability"],
        similarity=cast["similarity"],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd apps/auto-studio && venv/Scripts/python -m pytest films/woods_of_west/tests/test_voices.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/auto-studio/films/woods_of_west/voices.py apps/auto-studio/films/woods_of_west/tests/test_voices.py
git commit -m "feat(film): ElevenLabs voice casting + per-shot dialogue render

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Character sheets & keyframe generation (Fal)

**Files:**
- Create: `apps/auto-studio/films/woods_of_west/characters.py`
- Create: `apps/auto-studio/films/woods_of_west/keyframes.py`
- Test: `apps/auto-studio/films/woods_of_west/tests/test_keyframes.py`

**Interfaces:**
- Consumes: `media.fal_image_edit.edit_image_fal(prompt, images, output_path, *, resolution, aspect_ratio, seed, num_images)`; `script.CHARACTERS`, `script.style_prefix`.
- Produces:
  - `characters.build_character_sheets(style: str, out_dir: str) -> dict[str, str]` — generates one reference PNG per character (front 3/4 portrait) in `style`; returns `{char_id: png_path}`.
  - `keyframes.compose_keyframe_prompt(shot: dict, style: str) -> str` — pure string builder: `style_prefix + ", 16:9, " + shot.visual + character look notes`.
  - `keyframes.generate_shot_keyframe(shot: dict, style: str, char_refs: dict, out_dir: str) -> str` — Fal-edit a still from the relevant character refs (or text-only when no characters), save `shot{N}_keyframe.png`, return path.

- [ ] **Step 1: Write the failing test (pure prompt logic only)**

```python
# apps/auto-studio/films/woods_of_west/tests/test_keyframes.py
from films.woods_of_west import keyframes


def test_prompt_includes_style_aspect_and_visual():
    shot = {"id": 8, "visual": "wide two-shot down the street", "characters": ["cal", "pringle"]}
    p = keyframes.compose_keyframe_prompt(shot, "ballpoint")
    assert "ballpoint" in p
    assert "16:9" in p
    assert "wide two-shot down the street" in p
    assert "Cal Dalton" in p and "Sheriff Pringle" in p   # character looks injected


def test_prompt_handles_empty_cast():
    shot = {"id": 6, "visual": "empty dusty main street", "characters": []}
    p = keyframes.compose_keyframe_prompt(shot, "cinematic")
    assert "empty dusty main street" in p
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/auto-studio && venv/Scripts/python -m pytest films/woods_of_west/tests/test_keyframes.py -v`
Expected: FAIL — module `films.woods_of_west.keyframes` does not exist.

- [ ] **Step 3: Implement keyframes.py**

```python
"""Per-shot keyframe stills via Fal nano-banana edit, style- and character-locked.
The still is the Wan i2v start frame — the cross-shot consistency mechanism."""

import os
from media.fal_image_edit import edit_image_fal
from films.woods_of_west import script


def compose_keyframe_prompt(shot: dict, style: str) -> str:
    looks = "; ".join(script.CHARACTERS[c] for c in shot.get("characters", []))
    parts = [script.style_prefix(style), "16:9", shot["visual"]]
    if looks:
        parts.append(f"characters on-model — {looks}")
    return ", ".join(parts)


def generate_shot_keyframe(shot: dict, style: str, char_refs: dict, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"shot{shot['id']}_keyframe.png")
    prompt = compose_keyframe_prompt(shot, style)
    refs = [char_refs[c] for c in shot.get("characters", []) if c in char_refs]
    if not refs:
        # No character in frame (establishing shot): seed the edit from the first
        # available sheet so the style stays consistent, or fall back to text-only.
        refs = [next(iter(char_refs.values()))] if char_refs else None
    saved = edit_image_fal(prompt, refs, out_path, resolution="2K", aspect_ratio="16:9")
    return saved[0] if isinstance(saved, list) else saved
```

- [ ] **Step 4: Implement characters.py**

```python
"""Generate the three character reference sheets in a given style (one PNG each).
These refs lock faces/wardrobe across every keyframe."""

import os
from media.fal_image_edit import edit_image_fal
from films.woods_of_west import script


def build_character_sheets(style: str, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    refs = {}
    for cid, look in script.CHARACTERS.items():
        out_path = os.path.join(out_dir, f"{cid}_sheet.png")
        prompt = (f"{script.style_prefix(style)}, 16:9, full-body and face character "
                  f"reference sheet on a plain background: {look}")
        # Text-driven generation: pass the look text as its own seed image is not
        # available, so use a neutral edit prompt from a blank — edit_image_fal accepts
        # a single source; we generate by editing a plain reference of the description.
        saved = edit_image_fal(prompt, None, out_path, resolution="2K", aspect_ratio="16:9")
        refs[cid] = saved[0] if isinstance(saved, list) else saved
    return refs
```

> NOTE for implementer: confirm `edit_image_fal` accepts `images=None` (text-to-image) by checking `tools/fal/nano_banana_edit.edit_image`. If it requires a source image, generate the sheet via the text-to-image entry in `nano_banana_edit` instead and keep this function's signature unchanged. Verify before running Step 5.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd apps/auto-studio && venv/Scripts/python -m pytest films/woods_of_west/tests/test_keyframes.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add apps/auto-studio/films/woods_of_west/characters.py apps/auto-studio/films/woods_of_west/keyframes.py apps/auto-studio/films/woods_of_west/tests/test_keyframes.py
git commit -m "feat(film): character sheets + style/character-locked keyframe prompts

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Film driver (Phase 1 bake-off + Phase 2 full film)

**Files:**
- Create: `apps/auto-studio/films/woods_of_west/render_film.py`
- Test: `apps/auto-studio/films/woods_of_west/tests/test_render_film.py`

**Interfaces:**
- Consumes: `script.shots_for_phase`, `characters.build_character_sheets`, `keyframes.generate_shot_keyframe`, `media.comfyui_renderer.render_i2v_comfyui`, `voices.render_shot_dialogue`, `media.post_production.compile_final_video`.
- Produces:
  - `build_media_list(shots, keyframe_dir, clip_dir, audio_dir, render_clip, render_audio) -> list[dict]` — pure orchestration that, for each shot, calls injected `render_clip(shot)` and `render_audio(shot)` and returns `[{scene_number, video, audio}]` (skips shots whose clip render returns None). Dependency-injected so it is unit-testable without GPU/API.
  - `run_bakeoff(out_root: str) -> dict[str, str]` — renders the bakeoff shots in all 3 styles; returns `{style: master_mp4}`.
  - `run_film(style: str, out_root: str, music_path: str | None) -> str` — renders the full film in `style`; returns master mp4 path.
  - `main()` — CLI: `--phase {bakeoff,final}`, `--style`, `--music`, `--out`.

- [ ] **Step 1: Write the failing test (pure assembly, fully mocked)**

```python
# apps/auto-studio/films/woods_of_west/tests/test_render_film.py
from films.woods_of_west import render_film


def test_build_media_list_pairs_clip_and_audio(tmp_path):
    shots = [{"id": 1, "line": None}, {"id": 13, "line": "x"}]
    ml = render_film.build_media_list(
        shots, str(tmp_path), str(tmp_path), str(tmp_path),
        render_clip=lambda sh: f"clip{sh['id']}.mp4",
        render_audio=lambda sh: (f"aud{sh['id']}.mp3" if sh["line"] else None),
    )
    assert ml == [
        {"scene_number": 1, "video": "clip1.mp4", "audio": None},
        {"scene_number": 13, "video": "clip13.mp4", "audio": "aud13.mp3"},
    ]


def test_build_media_list_skips_failed_clip(tmp_path):
    shots = [{"id": 1, "line": None}, {"id": 2, "line": None}]
    ml = render_film.build_media_list(
        shots, str(tmp_path), str(tmp_path), str(tmp_path),
        render_clip=lambda sh: None if sh["id"] == 1 else "clip2.mp4",
        render_audio=lambda sh: None,
    )
    assert [m["scene_number"] for m in ml] == [2]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/auto-studio && venv/Scripts/python -m pytest films/woods_of_west/tests/test_render_film.py -v`
Expected: FAIL — module `films.woods_of_west.render_film` does not exist.

- [ ] **Step 3: Implement render_film.py**

```python
"""Driver for 'The Woods of the West'.

Phase 1 (bakeoff): render the signature beat in all 3 styles → pick a winner.
Phase 2 (final):   render the full film in the chosen style.

Run from apps/auto-studio:
  venv/Scripts/python -m films.woods_of_west.render_film --phase bakeoff
  venv/Scripts/python -m films.woods_of_west.render_film --phase final --style cartoon --music score.mp3
"""

import os
import sys
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
_AUTOSTUDIO = os.path.dirname(os.path.dirname(_HERE))
if _AUTOSTUDIO not in sys.path:
    sys.path.insert(0, _AUTOSTUDIO)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_AUTOSTUDIO, ".env"), override=True)
except Exception:
    pass

from films.woods_of_west import script, keyframes, characters, voices
from media.comfyui_renderer import render_i2v_comfyui
from media.post_production import compile_final_video


def build_media_list(shots, keyframe_dir, clip_dir, audio_dir, render_clip, render_audio):
    """Pure orchestration: pair each shot's clip + audio into a compile manifest.
    Shots whose clip render returns None are skipped."""
    media = []
    for sh in shots:
        video = render_clip(sh)
        if not video:
            print(f"⚠️  shot {sh['id']}: no clip, skipping")
            continue
        audio = render_audio(sh)
        media.append({"scene_number": sh["id"], "video": video, "audio": audio})
    return media


def _render_one_style(shots, style, out_root, music_path=None):
    style_root = os.path.join(out_root, style)
    kf_dir = os.path.join(style_root, "keyframes")
    clip_dir = os.path.join(style_root, "clips")
    aud_dir = os.path.join(style_root, "audio")
    char_dir = os.path.join(style_root, "characters")
    for d in (kf_dir, clip_dir, aud_dir, char_dir):
        os.makedirs(d, exist_ok=True)

    print(f"\n=== building character sheets ({style}) ===")
    char_refs = characters.build_character_sheets(style, char_dir)

    def render_clip(sh):
        kf = keyframes.generate_shot_keyframe(sh, style, char_refs, kf_dir)
        try:
            return render_i2v_comfyui(kf, sh["motion"], sh["id"], output_dir=clip_dir,
                                      output_name=f"shot{sh['id']}.mp4")
        except Exception as e:
            print(f"❌ shot {sh['id']} i2v failed: {e}")
            return None

    def render_audio(sh):
        return voices.render_shot_dialogue(sh, aud_dir)

    media = build_media_list(shots, kf_dir, clip_dir, aud_dir, render_clip, render_audio)
    master = os.path.join(style_root, f"woods_of_west_{style}.mp4")
    return compile_final_video(media, output_filename=master, music_path=music_path)


def run_bakeoff(out_root):
    shots = script.shots_for_phase("bakeoff")
    results = {}
    for style in script.STYLES:
        print(f"\n########## BAKE-OFF STYLE: {style} ##########")
        results[style] = _render_one_style(shots, style, os.path.join(out_root, "bakeoff"))
    return results


def run_film(style, out_root, music_path=None):
    shots = script.shots_for_phase("film")
    return _render_one_style(shots, style, os.path.join(out_root, "final"), music_path=music_path)


def main():
    ap = argparse.ArgumentParser(description="Render 'The Woods of the West'.")
    ap.add_argument("--phase", choices=["bakeoff", "final"], required=True)
    ap.add_argument("--style", choices=list(script.STYLES), help="required for --phase final")
    ap.add_argument("--music", help="path to western score mp3 (optional)")
    ap.add_argument("--out", default=os.path.join(_AUTOSTUDIO, "outputs", "woods_of_west"))
    args = ap.parse_args()
    if args.phase == "bakeoff":
        print(run_bakeoff(args.out))
    else:
        if not args.style:
            ap.error("--style is required for --phase final")
        print(run_film(args.style, args.out, music_path=args.music))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd apps/auto-studio && venv/Scripts/python -m pytest films/woods_of_west/tests/test_render_film.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Run the full unit suite**

Run: `cd apps/auto-studio && venv/Scripts/python -m pytest films/woods_of_west/tests/ -v`
Expected: PASS — all tests across the 4 test files green.

- [ ] **Step 6: Commit**

```bash
git add apps/auto-studio/films/woods_of_west/render_film.py apps/auto-studio/films/woods_of_west/tests/test_render_film.py
git commit -m "feat(film): woods-of-west driver — bakeoff + full-film orchestration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Phase 1 bake-off — render & choose (live, gated)

**Files:** outputs only — `apps/auto-studio/outputs/woods_of_west/bakeoff/{ballpoint,cartoon,cinematic}/`

This task runs real renders. Gated by: `.env` with `FAL_KEY` + `ELEVENLABS_API_KEY`, EC2 box up, tunnel open, `wan22_i2v_api.json` present (Task 2).

- [ ] **Step 1: Preflight the rig**

Run: `cd apps/auto-studio && venv/Scripts/python -c "import os,ec2_session as e; print('FAL', bool(os.getenv('FAL_KEY')), 'XI', bool(os.getenv('ELEVENLABS_API_KEY'))); print(e.ensure_running()); print('comfyui', e.is_comfyui_up())"`
Expected: both keys `True`; instance `running`; `comfyui True` (open the tunnel if not).

- [ ] **Step 2: Audition the three voices (cheap, no GPU)**

Run: `cd apps/auto-studio && venv/Scripts/python -c "from films.woods_of_west import voices,script; import os; os.makedirs('outputs/woods_of_west/_voicetest',exist_ok=True); [print(voices.render_shot_dialogue(s,'outputs/woods_of_west/_voicetest')) for s in script.SHOTS if s['speaker']]"`
Expected: one mp3 per spoken shot. Listen; if a voice is wrong, swap its `voice_id` in `voices.py:VOICE_CAST`, re-run, re-commit.

- [ ] **Step 3: Render the bake-off (all 3 styles, signature beat only)**

Run: `cd apps/auto-studio && venv/Scripts/python -m films.woods_of_west.render_film --phase bakeoff`
Expected: three masters — `outputs/woods_of_west/bakeoff/{ballpoint,cartoon,cinematic}/woods_of_west_<style>.mp4`. Each ~10–15s.

- [ ] **Step 4: Review with the user and record the choice**

Present the three clips. Ask the user to pick the winning style. Record the decision (one line) at the top of this task in the plan and in the session notes. **GATE — do not start Task 8 until the user picks.**

---

## Task 8: Phase 2 — full film in the winning style (live, gated)

**Files:** outputs only — `apps/auto-studio/outputs/woods_of_west/final/<style>/`

- [ ] **Step 1: (Optional) source the western score**

Provide a royalty-free western/spaghetti-western cue as `apps/auto-studio/score.mp3` (tense build + comedic sting). If none is available, skip — the film still compiles with the clips' native Wan audio under dialogue. Do not block on music.

- [ ] **Step 2: Render the full film**

Run: `cd apps/auto-studio && venv/Scripts/python -m films.woods_of_west.render_film --phase final --style <WINNER> --music score.mp3`
(Drop `--music score.mp3` if no score.) Expected: `outputs/woods_of_west/final/<WINNER>/woods_of_west_<WINNER>.mp4`, ~2 min, 16:9, with dialogue (+ music bed).

- [ ] **Step 3: Spot-check for character drift / bad clips**

Review each clip in `final/<WINNER>/clips/`. For any shot where Wan warped a face or the motion failed, re-run just that shot:
Run (example for shot 14): `cd apps/auto-studio && venv/Scripts/python -c "from films.woods_of_west import render_film as r, script; sh=[s for s in script.SHOTS if s['id']==14][0]; print(r._render_one_style([sh],'<WINNER>','outputs/woods_of_west/final'))"`
Then re-run Step 2 to recompile. Expected: the re-rolled clip replaces the bad one.

- [ ] **Step 4: Final review + stop the GPU box (cost control)**

Confirm the master plays start-to-finish with synced dialogue and the punchline lands. Then:
Run: `cd apps/auto-studio && venv/Scripts/python -c "import ec2_session as e; print(e.stop())"`
Expected: instance `stopping` (the g6.2xlarge bills ~$1.20/hr — don't leave it running).

---

## Self-Review

**Spec coverage:**
- Bake-off-then-commit → Tasks 6 (`run_bakeoff`/`run_film`) + 7 + 8. ✓
- 3 candidate styles → `script.STYLES` (Task 3), rendered in Task 7. ✓
- Faithful bawdy punchline, local-only → shots 13–15 are `phase=bakeoff`, rendered exclusively via `render_i2v_comfyui` (Task 1), never a cloud renderer. ✓
- Voiced dialogue (ElevenLabs) → Task 4. ✓ Music + SFX → music bed in `compile_final_video` (Task 8 Step 1); SFX via Wan native clip audio ducked under dialogue (`post_production` already mixes it). ✓
- ~2 min / 16:9 → 16 shots @ ~5s, 16:9 enforced in keyframe prompt + workflow (Tasks 2,5). ✓
- Wan 2.2 i2v in local ComfyUI → Tasks 1,2. ✓
- Character consistency (bespoke-character-pipeline spirit) → character sheets as Fal refs (Tasks 5). ✓
- Deliverables under `outputs/woods_of_west/` → Task 6 paths. ✓

**Open items from spec carried as non-blocking:** music source (Task 8 Step 1, optional); concrete voice_ids (Task 4 defaults + Task 7 Step 2 audition).

**Placeholder scan:** Task 5 `characters.py` has one explicit implementer verification note about `edit_image_fal(images=None)` text-to-image support — flagged, not a silent TODO; resolve by reading `tools/fal/nano_banana_edit.py` before Step 5. No other placeholders.

**Type consistency:** `build_media_list` emits `{scene_number, video, audio}` exactly as `compile_final_video` consumes (`item["video"]`, `item["audio"]`, `item["scene_number"]`). `render_i2v_comfyui` signature matches the call in `_render_one_style`. `render_shot_dialogue` returns path|None, consumed as the `audio` field. ✓
