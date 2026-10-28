"""
Higgsfield adapter — the `higgsfield` CLI as an Ilyrium render engine.

Wraps the Higgsfield CLI (installed via npm/curl, authenticated with `higgsfield auth login`,
workspace selected with `higgsfield workspace set <id>`) so the studio can dispatch shots to the
Higgsfield catalog the same way it dispatches to fal / runway / comfyui:

  stills   : soul_cinematic (cinematic, 21:9), text2image_soul_v2 (Soul 2.0), soul_location
             (no-people plates), nano_banana_pro / seedream_v5_pro (reference-driven edits)
  video    : seedance_2_0 (default; start/end image, up to 9 image refs, audio refs for lip-sync,
             genre=drama), kling3_0 (cheap start/end-frame i2v), veo3_1, seedance_2_5 (edit/extend),
             workflow cinematic_studio_video_4_0 ("cinema4": camera/lens/era/light controls)
  audio    : seed_audio (SFX / ambience / voice-style), text2speech_v2 (elevenlabs|minimax|... voices)
  identity : soul-id (train a Soul Character from 5-20 photos -> reference id -> --soul-id on stills)

Everything goes through subprocess + `--json`; nothing here imports a Higgsfield SDK.

Higgsfield-process rules folded in (from the higgsfield-* skills + the live CLI review, 2026-08-15):
  * COST FIRST  - `generate cost` before `generate create`; refuse when the estimate exceeds
                  HIGGSFIELD_MAX_CREDITS_PER_JOB (default 40) unless HIGGSFIELD_ALLOW_EXPENSIVE=1.
                  This is Ilyrium's confirm_cost gate applied per job.
  * ONE SHOT    - `generate create <job_type> ... --wait --json`; never the two-step create/wait.
  * CONTRACT    - `model get <job_type> --json` is cached and used to (a) reject unknown params
                  before spending, (b) snap aspect/duration/resolution to the model's closed enums.
  * CHAIN IDS   - media flags accept a local path OR a UUID (upload id / previous job id). Pass the
                  previous job id as the next shot's start_image instead of re-uploading.
  * DRY RUN     - HIGGSFIELD_DRY_RUN=1 records the exact command in LAST_COMMANDS and returns a
                  synthetic result (used by tests; use it to preview a batch before spending).
  * RETRY ONCE  - transient failures (timeout / network / 5xx) retry once with identical args; a
                  second identical failure raises (Higgsfield rule: "two identical failures mean the
                  prompt or parameters must change").

Result-shape note: the completed-job JSON printed by `--wait --json` was NOT exercised live in this
session (no spend). `_extract_result_urls` therefore walks the object for media URLs generically and
`_extract_job_id` tries the usual keys; if a first live run shows a different shape, tighten both
helpers (they are the only place that knows the shape). `higgsfield generate get <id> --json` is the
fallback to re-fetch a job.

Environment:
  HIGGSFIELD_CLI               explicit path to the CLI (else `higgsfield` / `higgs` on PATH; `hf` is skipped: HuggingFace collision)
  HIGGSFIELD_DRY_RUN=1         do not execute; record commands
  HIGGSFIELD_MAX_CREDITS_PER_JOB   float, default 40
  HIGGSFIELD_ALLOW_EXPENSIVE=1 bypass the cost cap
  HIGGSFIELD_SKIP_COST_CHECK=1 skip the estimate entirely (not recommended)
  HIGGSFIELD_WAIT_TIMEOUT      e.g. "20m" (default "15m")
  HIGGSFIELD_DEFAULT_VIDEO     default video job_type for model="higgsfield" (default seedance_2_0)
  HIGGSFIELD_DEFAULT_STILL     default still job_type (default soul_cinematic)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time

# --------------------------------------------------------------------------- #
# Model routing: studio model name -> Higgsfield job_type (+ kind)
# --------------------------------------------------------------------------- #
# kind: "still" | "video" | "audio" | "workflow"
ROUTES = {
    "higgsfield":                ("__default_video__", "video"),
    "higgsfield:seedance":       ("seedance_2_0", "video"),
    "higgsfield:seedance_2_0":   ("seedance_2_0", "video"),
    "higgsfield:seedance_2_5":   ("seedance_2_5", "video"),
    "higgsfield:kling":          ("kling3_0", "video"),
    "higgsfield:kling3_0":       ("kling3_0", "video"),
    "higgsfield:kling_turbo":    ("kling3_0_turbo", "video"),
    "higgsfield:veo3_1":         ("veo3_1", "video"),
    "higgsfield:veo3":           ("veo3", "video"),
    "higgsfield:hailuo":         ("minimax_hailuo", "video"),
    "higgsfield:gemini_omni":    ("gemini_omni", "video"),
    "higgsfield:cinema4":        ("cinematic_studio_video_4_0", "workflow"),
    "higgsfield:soul_cinematic": ("soul_cinematic", "still"),
    "higgsfield:soul":           ("text2image_soul_v2", "still"),
    "higgsfield:soul_location":  ("soul_location", "still"),
    "higgsfield:nano_banana_pro": ("nano_banana_pro", "still"),
    "higgsfield:seedream":       ("seedream_v5_pro", "still"),
    "higgsfield:gpt_image_2":    ("gpt_image_2", "still"),
    "higgsfield:seed_audio":     ("seed_audio", "audio"),
    "higgsfield:tts":            ("text2speech_v2", "audio"),
}
STILL_JOB_TYPES = {"soul_cinematic", "text2image_soul_v2", "soul_location", "soul_cast",
                   "nano_banana_pro", "nano_banana_flash", "nano_banana_2_lite", "seedream_v5_pro",
                   "seedream_v4_5", "gpt_image_2", "flux_2", "z_image", "recraft_v4_1", "kling_omni_image"}
AUDIO_JOB_TYPES = {"seed_audio", "text2speech_v2", "sonilo_music", "mirelo_text_to_audio",
                   "qwen_audio_tts", "inworld_text_to_speech"}
WORKFLOW_JOB_TYPES = {"cinematic_studio_video_4_0", "cinematic_studio_3_0", "cinematic_studio_video_3_5",
                      "kling3_0_motion_control", "draw_to_video", "reframe", "dubbing", "voice_change",
                      "soul_cinema_studio", "cinematic_studio_soul_location", "cinematic_studio_soul_cast"}

# Live cost snapshot (2026-08-15, free workspace, measured with `generate cost`) — planning only;
# guard_cost() always re-estimates. Rates: kling3_0 std i2v 2 cr/s (min 3 s); seedance_2_0 720p std
# 4.5 cr/s (min 4 s; 1080p ~2x); veo3_1 high 2.75 cr/s (4/6/8 s only).
COST_SNAPSHOT = {
    "seedance_2_0 8s 1080p std": 72, "seedance_2_0 8s 720p std": 36, "seedance_2_0 per_s 720p": 4.5,
    "kling3_0 8s pro": 20, "kling3_0 8s std i2v": 16, "kling3_0 per_s std": 2.0,
    "veo3_1 8s high": 22, "veo3_1 per_s high": 2.75,
    "soul_cinematic 2k": 0.12, "soul_location": 0.12, "nano_banana_pro 2k": 2.0,
    "seed_audio": 0.1, "text2speech_v2": 0.15,
}

LAST_COMMANDS: list = []          # dry-run / debugging: every argv we (would have) executed
_MODEL_CACHE: dict = {}


class HiggsfieldError(RuntimeError):
    pass


class HiggsfieldCostRefused(HiggsfieldError):
    pass


# --------------------------------------------------------------------------- #
# CLI plumbing
# --------------------------------------------------------------------------- #
def cli_path() -> str:
    """Resolve the CLI executable. Windows npm installs `higgsfield.cmd`; shutil.which finds it via PATHEXT."""
    p = os.getenv("HIGGSFIELD_CLI")
    if p:
        return p
    # NOTE: deliberately not probing `hf` — on Windows that name collides with the HuggingFace CLI
    # (C:\Users\<user>\.local\bin\hf.exe). Set HIGGSFIELD_CLI explicitly if `higgsfield` is not on PATH.
    for name in ("higgsfield", "higgs"):
        found = shutil.which(name)
        if found:
            return found
    raise HiggsfieldError(
        "higgsfield CLI not found on PATH. Install: "
        "`curl -fsSL https://raw.githubusercontent.com/higgsfield-ai/cli/main/install.sh | sh` "
        "(or npm), then `higgsfield auth login` and `higgsfield workspace set <id>`. "
        "Or set HIGGSFIELD_CLI to the executable.")


def dry_run() -> bool:
    return os.getenv("HIGGSFIELD_DRY_RUN", "").strip() not in ("", "0", "false", "False")


def _run(args: list, timeout: int = 1800, dry_ok: bool = True) -> tuple[int, str, str]:
    """Run the CLI with the given argv (list, no shell). Returns (rc, stdout, stderr)."""
    argv = [cli_path()] if not dry_run() else ["higgsfield"]
    argv = argv + [str(a) for a in args]
    LAST_COMMANDS.append(argv)
    if dry_run() and dry_ok:
        return 0, _dry_stdout(args), ""
    proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _dry_stdout(args: list) -> str:
    """Synthetic JSON for dry runs so callers can exercise the parse path."""
    if args[:2] == ["generate", "cost"]:
        return json.dumps({"credits": 1.0})
    if args[:2] == ["generate", "create"]:
        return json.dumps([{"id": "dry-run-job-id", "status": "completed",
                            "results": [{"url": "https://dry.run/output.mp4"}]}])
    if args[:2] == ["model", "get"]:
        return json.dumps({"job_type": args[2], "params": [], "rules": []})
    if args[:2] == ["soul-id", "create"]:
        return json.dumps({"id": "dry-run-soul-id", "status": "in_progress"})
    if args[:2] == ["soul-id", "wait"]:
        return json.dumps({"id": args[2], "status": "completed"})
    if args[:2] == ["account", "status"]:
        return json.dumps({"plan": "dry", "credits": 0})
    return "{}"


def _parse_json(text: str):
    """The CLI prints raw JSON with --json; be tolerant of a leading 'Note:' line."""
    t = (text or "").strip()
    if not t:
        return None
    for i, ch in enumerate(t):
        if ch in "{[":
            try:
                return json.loads(t[i:])
            except json.JSONDecodeError:
                break
    return None


def _json(args: list, timeout: int = 1800):
    rc, out, err = _run(args + ["--json"], timeout=timeout)
    if rc != 0:
        raise HiggsfieldError(_friendly_error(err or out))
    data = _parse_json(out)
    if data is None:
        raise HiggsfieldError(f"higgsfield returned no JSON for {' '.join(map(str, args))}: {out[:300]!r}")
    return data


def _friendly_error(msg: str) -> str:
    m = (msg or "").strip()
    if "No workspace selected" in m:
        return m + "  -> run: higgsfield workspace list; higgsfield workspace set <workspace_id>"
    if "Session expired" in m or "Not authenticated" in m:
        return m + "  -> run: higgsfield auth login (interactive)"
    if "Unknown params" in m:
        return m + "  -> the model schema does not accept that flag; see `higgsfield model get <job_type>`"
    if "Minimum Basic plan required" in m:
        return m + "  -> Soul-ID training needs a paid plan (Basic+)"
    return m or "higgsfield CLI failed"


_TRANSIENT = re.compile(r"(timeout|timed out|temporar|connection|EOF|5\d\d|rate limit|try again)", re.I)


# --------------------------------------------------------------------------- #
# Account / model contract
# --------------------------------------------------------------------------- #
def account_status() -> dict:
    return _json(["account", "status"])


def model_get(job_type: str) -> dict:
    """Cached model contract (params + rules)."""
    if job_type not in _MODEL_CACHE:
        _MODEL_CACHE[job_type] = _json(["model", "get", job_type])
    return _MODEL_CACHE[job_type]


def _param_index(job_type: str) -> dict:
    """{param_name: {enum:[...], type:...}} from the cached contract; {} if unavailable."""
    try:
        contract = model_get(job_type)
    except HiggsfieldError:
        return {}
    idx = {}
    for p in (contract or {}).get("params", []) or []:
        if isinstance(p, dict) and p.get("name"):
            idx[p["name"]] = p
    return idx


_MEDIA_PARAMS = {"image_references", "video_references", "audio_references", "start_image", "end_image",
                 "image", "video", "audio", "input_video", "medias"}


def validate_params(job_type: str, params: dict) -> dict:
    """Reject unknown params before spending; snap enum values (aspect_ratio/resolution/duration).
    Returns the (possibly adjusted) params. If the contract is not available (dry run without a
    cache), returns params unchanged."""
    idx = _param_index(job_type)
    if not idx:
        return dict(params)
    out = {}
    unknown = []
    for k, v in params.items():
        if v is None:
            continue
        if k not in idx and k not in _MEDIA_PARAMS:
            unknown.append(k)
            continue
        spec = idx.get(k) or {}
        enum = spec.get("enum")
        if enum:
            sv = str(v)
            if sv not in [str(e) for e in enum]:
                v = _snap(k, sv, [str(e) for e in enum])
        out[k] = v
    if unknown:
        raise HiggsfieldError(f"Unknown params for {job_type}: {unknown}. Allowed: {sorted(idx)}")
    return out


_ASPECT_ORDER = ["21:9", "16:9", "4:3", "3:2", "1:1", "2:3", "3:4", "9:16"]


def _snap(name: str, value: str, enum: list) -> str:
    """Closest allowed value (mirrors the CLI's 'adjustments' behaviour but decided locally so we
    can log it)."""
    if name == "aspect_ratio":
        # walk outward from the wanted aspect in the canonical order
        if value in _ASPECT_ORDER:
            i = _ASPECT_ORDER.index(value)
            for d in range(1, len(_ASPECT_ORDER)):
                for j in (i - d, i + d):
                    if 0 <= j < len(_ASPECT_ORDER) and _ASPECT_ORDER[j] in enum:
                        return _ASPECT_ORDER[j]
        return "16:9" if "16:9" in enum else enum[0]
    if name in ("duration",) or value.replace(".", "", 1).isdigit():
        try:
            want = float(value)
            nums = [(abs(float(e) - want), e) for e in enum if str(e).replace(".", "", 1).isdigit()]
            if nums:
                return sorted(nums)[0][1]
        except ValueError:
            pass
    return enum[0]


# --------------------------------------------------------------------------- #
# Argument building
# --------------------------------------------------------------------------- #
def _flag(name: str) -> str:
    return "--" + name.replace("_", "-") if name in ("start_image", "end_image", "wait_timeout") else "--" + name


def build_args(job_type: str, prompt: str | None, params: dict | None = None,
               media: dict | None = None, wait: bool = True, workflow: bool = False) -> list:
    """argv for `generate create` (or `generate workflow`). media = {role: path|uuid|[...]} with roles
    start_image / end_image / image (image_references) / video / audio."""
    argv = ["generate", "workflow" if workflow else "create", job_type]
    if prompt:
        argv += ["--prompt", prompt]
    for k, v in (params or {}).items():
        if v is None or v == "":
            continue
        if isinstance(v, bool):
            v = "true" if v else "false"
        argv += [_flag(k), str(v)]
    for role, val in (media or {}).items():
        if not val:
            continue
        flag = {"start_image": "--start-image", "end_image": "--end-image", "image": "--image",
                "image_references": "--image-references", "video": "--video",
                "video_references": "--video-references", "audio": "--audio",
                "audio_references": "--audio-references"}.get(role, "--" + role.replace("_", "-"))
        vals = val if isinstance(val, (list, tuple)) else [val]
        for item in vals:
            argv += [flag, str(item)]
    if wait:
        argv += ["--wait", "--wait-timeout", os.getenv("HIGGSFIELD_WAIT_TIMEOUT", "15m")]
    return argv


# --------------------------------------------------------------------------- #
# Cost guard
# --------------------------------------------------------------------------- #
def estimate_cost(job_type: str, prompt: str | None, params: dict | None = None,
                  media: dict | None = None, workflow: bool = False) -> float:
    """`generate cost ...` -> credits (float). Local file paths are auto-uploaded by the CLI for the
    estimate; pass UUIDs to avoid the upload."""
    argv = build_args(job_type, prompt, params, media, wait=False, workflow=False)
    argv = ["generate", "cost"] + (["workflow"] if workflow else []) + argv[2:]
    data = _json(argv, timeout=300)
    if isinstance(data, dict):
        for k in ("credits", "cost", "estimated_credits"):
            if k in data:
                return float(data[k])
    if isinstance(data, (int, float)):
        return float(data)
    raise HiggsfieldError(f"could not read credits from cost response: {data!r}")


def cost_cap() -> float:
    try:
        return float(os.getenv("HIGGSFIELD_MAX_CREDITS_PER_JOB", "40"))
    except ValueError:
        return 40.0


def guard_cost(job_type: str, prompt: str | None, params: dict | None, media: dict | None,
               workflow: bool = False) -> float | None:
    """Estimate and enforce the per-job credit cap. Returns the estimate (or None if skipped)."""
    if os.getenv("HIGGSFIELD_SKIP_COST_CHECK", "") not in ("", "0"):
        return None
    credits = estimate_cost(job_type, prompt, params, media, workflow=workflow)
    cap = cost_cap()
    allow = os.getenv("HIGGSFIELD_ALLOW_EXPENSIVE", "") not in ("", "0")
    print(f"[HIGGSFIELD] cost estimate {job_type}: {credits} credits (cap {cap})")
    if credits > cap and not allow:
        raise HiggsfieldCostRefused(
            f"{job_type} would cost {credits} credits > cap {cap}. Lower duration/resolution, pick a "
            f"cheaper route (higgsfield:kling3_0 std), raise HIGGSFIELD_MAX_CREDITS_PER_JOB, or set "
            f"HIGGSFIELD_ALLOW_EXPENSIVE=1 to confirm.")
    return credits


# --------------------------------------------------------------------------- #
# Generate + result handling
# --------------------------------------------------------------------------- #
_MEDIA_EXT = re.compile(r"\.(mp4|mov|webm|png|jpg|jpeg|webp|gif|mp3|wav|m4a|ogg|glb)(\?|$)", re.I)


def _walk(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{path}[{i}]")
    else:
        yield path, obj


def _extract_result_urls(obj) -> list:
    """All media URLs in a job object, best first (keys containing 'url'/'result'/'output' rank higher)."""
    scored = []
    for path, val in _walk(obj):
        if isinstance(val, str) and val.startswith("http"):
            score = 0
            lp = path.lower()
            if "result" in lp or "output" in lp:
                score += 2
            if "url" in lp:
                score += 1
            if _MEDIA_EXT.search(val):
                score += 2
            if "thumb" in lp or "preview" in lp:
                score -= 3
            scored.append((score, val))
    scored.sort(key=lambda t: t[0], reverse=True)
    seen, out = set(), []
    for _, u in scored:
        if u not in seen:
            seen.add(u); out.append(u)
    return out


def _extract_job_id(obj) -> str | None:
    if isinstance(obj, list) and obj:
        return _extract_job_id(obj[0])
    if isinstance(obj, dict):
        for k in ("id", "job_id", "job_set_id", "jobId"):
            if isinstance(obj.get(k), str):
                return obj[k]
    return None


def _status(obj) -> str:
    if isinstance(obj, list) and obj:
        obj = obj[0]
    if isinstance(obj, dict):
        return str(obj.get("status") or obj.get("state") or "").lower()
    return ""


def download(url: str, output_path: str) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    if dry_run():
        with open(output_path, "wb") as f:
            f.write(b"")
        return output_path
    import requests
    d = requests.get(url, timeout=900)
    d.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(d.content)
    return output_path


def generate(job_type: str, prompt: str | None, params: dict | None = None, media: dict | None = None,
             output_path: str | None = None, workflow: bool = False, check_cost: bool = True,
             timeout: int = 1800) -> dict:
    """Submit one job (--wait --json), download the primary result to output_path (if given).
    Returns {job_id, status, urls, path, credits, argv}. Raises HiggsfieldError on failure."""
    params = validate_params(job_type, params or {}) if not workflow else dict(params or {})
    credits = guard_cost(job_type, prompt, params, media, workflow=workflow) if check_cost else None
    argv = build_args(job_type, prompt, params, media, wait=True, workflow=workflow)
    print(f"[HIGGSFIELD] {'workflow' if workflow else 'create'} {job_type} "
          f"({', '.join(f'{k}={v}' for k, v in params.items())})")
    last_err = None
    for attempt in (1, 2):
        try:
            data = _json(argv, timeout=timeout)
            break
        except HiggsfieldError as e:
            last_err = e
            if attempt == 1 and _TRANSIENT.search(str(e)):
                print(f"[HIGGSFIELD] transient failure, retrying once: {e}")
                time.sleep(3)
                continue
            raise
    else:  # pragma: no cover
        raise last_err
    status = _status(data)
    if status and status not in ("completed", "succeeded", "success", "done", "finished"):
        if status in ("nsfw", "ip_detected", "failed", "error", "rejected"):
            raise HiggsfieldError(f"{job_type} job ended with status={status}: {json.dumps(data)[:400]}")
    urls = _extract_result_urls(data)
    job_id = _extract_job_id(data)
    if not urls:
        raise HiggsfieldError(f"{job_type} returned no result URL (job {job_id}). Re-fetch with "
                              f"`higgsfield generate get {job_id} --json`. Raw: {json.dumps(data)[:400]}")
    path = download(urls[0], output_path) if output_path else None
    return {"job_id": job_id, "status": status or "completed", "urls": urls, "path": path,
            "credits": credits, "argv": argv, "raw": data}


# --------------------------------------------------------------------------- #
# Soul-ID (character identity lock) — Stage 3 asset, registered per project
# --------------------------------------------------------------------------- #
SOUL_REGISTRY_REL = os.path.join("03_design", "characters", "soul_ids.json")


def soul_registry_path(project_dir: str) -> str:
    return os.path.join(project_dir, SOUL_REGISTRY_REL)


def load_soul_registry(project_dir: str) -> dict:
    p = soul_registry_path(project_dir)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {"version": "1.0", "souls": {}}


def save_soul_registry(project_dir: str, reg: dict) -> str:
    p = soul_registry_path(project_dir)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2)
    return p


def resolve_soul_id(character: str, project_dir: str | None) -> str | None:
    """casting-canon key -> trained Soul reference id, or None."""
    if not (character and project_dir):
        return None
    reg = load_soul_registry(project_dir)
    entry = (reg.get("souls") or {}).get(character.lower())
    return (entry or {}).get("soul_id") or None


def soul_create(name: str, images: list, cinematic: bool = True, wait: bool = True,
                timeout_min: int = 45) -> dict:
    """Train a Soul Character. images = 5-20 local paths or upload ids (varied angles/lighting).
    cinematic=True -> --soul-cinematic (for cinematic/video work); else --soul-2 (stills).
    Requires a paid Higgsfield plan (Basic+)."""
    if not (5 <= len(images) <= 20):
        raise HiggsfieldError(f"Soul training needs 5-20 images (got {len(images)}); 8-12 is the sweet spot.")
    argv = ["soul-id", "create", "--name", name, "--soul-cinematic" if cinematic else "--soul-2"]
    for im in images:
        argv += ["--image", str(im)]
    data = _json(argv, timeout=600)
    soul_id = _extract_job_id(data)
    if wait and soul_id:
        rc, out, err = _run(["soul-id", "wait", soul_id, "--timeout", f"{timeout_min}m", "--json"],
                            timeout=timeout_min * 60 + 60)
        if rc != 0:
            raise HiggsfieldError(_friendly_error(err or out))
        data = _parse_json(out) or data
    return {"soul_id": soul_id, "raw": data}


def soul_list() -> list:
    data = _json(["soul-id", "list"])
    return data if isinstance(data, list) else [data]


def register_soul(project_dir: str, character: str, soul_id: str, variant: str = "soul-cinematic",
                  photos: int | None = None, notes: str = "") -> str:
    reg = load_soul_registry(project_dir)
    reg.setdefault("souls", {})[character.lower()] = {
        "soul_id": soul_id, "variant": variant, "photos": photos, "notes": notes,
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    return save_soul_registry(project_dir, reg)


# --------------------------------------------------------------------------- #
# Kernel integration
# --------------------------------------------------------------------------- #
def kernel_defaults(kernel: dict | None) -> dict:
    """Per-engine default params from the kernel: engine_tails.higgsfield may be a dict
    (e.g. {"genre": "drama", "aspect_ratio": "21:9", "quality": "2k", "resolution": "720p"})."""
    tails = (kernel or {}).get("engine_tails") or {}
    hf = tails.get("higgsfield")
    return dict(hf) if isinstance(hf, dict) else {}


def _compose(prompt: str, kernel: dict | None) -> str:
    if not kernel:
        return prompt
    try:
        from style_kernel import compose_prompt
        return compose_prompt(prompt, kernel, engine="higgsfield")
    except Exception:
        return prompt


def _pick(params: dict, allowed: set) -> dict:
    return {k: v for k, v in params.items() if k in allowed}


# --------------------------------------------------------------------------- #
# Renderers (studio-facing)
# --------------------------------------------------------------------------- #
def render_still_higgsfield(prompt: str, output_path: str, model: str = None, aspect_ratio: str = "21:9",
                            quality: str = "2k", soul_id: str = None, image_refs: list = None,
                            kernel: dict = None, seed: int = None, extra: dict = None) -> dict:
    """Still: soul_cinematic (default) / text2image_soul_v2 / soul_location / nano_banana_pro / ...
    soul_id -> --custom_reference_id (the trained Soul Character; both --soul-id and
    --custom_reference_id are accepted by CLI 1.1.23). image_refs -> --image (<=1 for Soul models)."""
    job_type = model or os.getenv("HIGGSFIELD_DEFAULT_STILL", "soul_cinematic")
    kd = kernel_defaults(kernel)
    params = {"aspect_ratio": kd.get("aspect_ratio", aspect_ratio)}
    if job_type in ("soul_cinematic", "text2image_soul_v2"):
        params["quality"] = kd.get("quality", quality)
        if soul_id:
            params["custom_reference_id"] = soul_id
        if seed is not None and job_type == "text2image_soul_v2":
            params["seed"] = seed
    elif job_type in ("nano_banana_pro", "gpt_image_2", "seedream_v5_pro", "seedream_v4_5"):
        params["resolution"] = kd.get("still_resolution", "2k")
    params.update(extra or {})
    media = {}
    if image_refs and job_type not in ("soul_location", "soul_cast", "z_image", "recraft_v4_1"):
        media["image"] = list(image_refs)[:1] if job_type in ("soul_cinematic", "text2image_soul_v2") else list(image_refs)
    return generate(job_type, _compose(prompt, kernel), params, media, output_path=output_path)


def render_i2v_higgsfield(prompt: str, output_path: str, start_image: str, model: str = None,
                          duration: int = 8, aspect_ratio: str = "16:9", resolution: str = None,
                          end_image: str = None, audio_refs: list = None, image_refs: list = None,
                          kernel: dict = None, extra: dict = None) -> dict:
    """Image-to-video from a locked keyframe. start_image/end_image = local path or UUID (upload or a
    previous job id). audio_refs (seedance only) = reference audio for lip-sync / soundtrack match.
    Default model seedance_2_0 (genre=drama from the kernel), or kling3_0 / veo3_1 / seedance_2_5."""
    job_type = model or os.getenv("HIGGSFIELD_DEFAULT_VIDEO", "seedance_2_0")
    workflow = job_type in WORKFLOW_JOB_TYPES
    kd = kernel_defaults(kernel)
    params = {"aspect_ratio": kd.get("aspect_ratio", aspect_ratio), "duration": int(duration)}
    if job_type in ("seedance_2_0", "seedance_2_5", "cinematic_studio_video_4_0", "flux_3_video", "kling3_0_turbo"):
        params["resolution"] = resolution or kd.get("resolution", "720p")
    if job_type == "seedance_2_0":
        params["genre"] = kd.get("genre", "drama")
        params["mode"] = kd.get("mode", "std")
        params["generate_audio"] = kd.get("generate_audio", False if audio_refs is None else True)
    if job_type == "seedance_2_5":
        params["mode"] = "omni_reference"       # start/end images only allowed in omni_reference
    if job_type == "kling3_0":
        params["mode"] = kd.get("kling_mode", "std")
        params["sound"] = kd.get("kling_sound", "off")
    if job_type == "veo3_1":
        params["quality"] = kd.get("veo_quality", "high")
        params["variant"] = kd.get("veo_variant", "veo-3-1-fast")
    if job_type == "cinematic_studio_video_4_0":
        params["mode"] = "omni_reference"
        params["genre_id"] = kd.get("genre_id")
    params.update(extra or {})
    media = {"start_image": start_image}
    if end_image and job_type in ("seedance_2_0", "kling3_0", "seedance_2_5", "cinematic_studio_video_4_0",
                                  "flux_3_video", "minimax_h3", "marketing_studio_video"):
        media["end_image"] = end_image
    if image_refs and job_type in ("seedance_2_0", "seedance_2_5", "cinematic_studio_video_4_0", "gemini_omni"):
        media["image_references"] = list(image_refs)
    if audio_refs and job_type in ("seedance_2_0", "seedance_2_5", "cinematic_studio_video_4_0", "minimax_h3"):
        media["audio_references"] = list(audio_refs)
    return generate(job_type, _compose(prompt, kernel), params, media, output_path=output_path, workflow=workflow)


def render_t2v_higgsfield(prompt: str, output_path: str, model: str = None, duration: int = 8,
                          aspect_ratio: str = "16:9", resolution: str = None, kernel: dict = None,
                          extra: dict = None) -> dict:
    """Text-to-video (no locked frame). Prefer render_i2v_higgsfield for continuity."""
    job_type = model or os.getenv("HIGGSFIELD_DEFAULT_VIDEO", "seedance_2_0")
    workflow = job_type in WORKFLOW_JOB_TYPES
    kd = kernel_defaults(kernel)
    params = {"aspect_ratio": kd.get("aspect_ratio", aspect_ratio), "duration": int(duration)}
    if job_type in ("seedance_2_0", "seedance_2_5", "cinematic_studio_video_4_0"):
        params["resolution"] = resolution or kd.get("resolution", "720p")
    if job_type == "seedance_2_0":
        params["genre"] = kd.get("genre", "drama"); params["mode"] = kd.get("mode", "std")
    if job_type == "kling3_0":
        params["mode"] = kd.get("kling_mode", "std"); params["sound"] = kd.get("kling_sound", "off")
    if job_type == "veo3_1":
        params["quality"] = kd.get("veo_quality", "high")
    params.update(extra or {})
    return generate(job_type, _compose(prompt, kernel), params, {}, output_path=output_path, workflow=workflow)


def render_audio_higgsfield(prompt: str, output_path: str, model: str = "seed_audio", voice_id: str = None,
                            voice_type: str = None, variant: str = None, audio_refs: list = None,
                            extra: dict = None) -> dict:
    """seed_audio (SFX/ambience/voice-style; voice_id+voice_type together) or text2speech_v2
    (variant elevenlabs|minimax|seed_speech|vibe_voice|cozy_voice; voice_id + voice_type required)."""
    params = {}
    if model == "seed_audio":
        params["format"] = "wav"
        if voice_id:
            params["voice_id"] = voice_id; params["voice_type"] = voice_type or "preset"
    elif model == "text2speech_v2":
        if not (voice_id and variant):
            raise HiggsfieldError("text2speech_v2 requires variant + voice_id (+ voice_type)")
        params.update({"variant": variant, "voice_id": voice_id, "voice_type": voice_type or "preset"})
    params.update(extra or {})
    media = {"audio_references": list(audio_refs)} if audio_refs else {}
    return generate(model, prompt, params, media, output_path=output_path)


def route(model: str) -> tuple[str, str]:
    """studio model string -> (job_type, kind). Unknown 'higgsfield:<x>' passes <x> through as a
    job_type (kind inferred)."""
    m = (model or "higgsfield").lower()
    if m in ROUTES:
        jt, kind = ROUTES[m]
        if jt == "__default_video__":
            jt = os.getenv("HIGGSFIELD_DEFAULT_VIDEO", "seedance_2_0")
        return jt, kind
    if m.startswith("higgsfield:"):
        jt = m.split(":", 1)[1]
        kind = ("still" if jt in STILL_JOB_TYPES else "audio" if jt in AUDIO_JOB_TYPES
                else "workflow" if jt in WORKFLOW_JOB_TYPES else "video")
        return jt, kind
    raise HiggsfieldError(f"not a higgsfield model string: {model!r}")


def render_scene_higgsfield(visual_prompt: str, scene_number: int, output_dir: str = ".",
                            aspect_ratio: str = "16:9", output_name: str = None, model: str = "higgsfield",
                            kernel: dict = None, cref: str = None, duration_seconds: int = 8,
                            audio_ref: str = None, end_image: str = None, soul_id: str = None,
                            image_refs: list = None) -> str:
    """producer._render_video entry point. Mirrors the other renderers' contract: returns the saved
    file path (mp4 for video; png for still routes), raises on failure so the orchestrator records a
    failed take. `cref` (the project anchor / locked keyframe: local path or job/upload UUID) becomes
    the first frame for video routes and the image reference for still routes."""
    os.makedirs(output_dir, exist_ok=True)
    job_type, kind = route(model)
    base = (output_name or f"scene_{scene_number}.mp4").rsplit(".", 1)[0]
    if kind == "still":
        out = os.path.join(output_dir, base + ".png")
        print(f"[HIGGSFIELD] scene {scene_number}: still via {job_type}")
        res = render_still_higgsfield(visual_prompt, out, model=job_type, aspect_ratio=aspect_ratio,
                                      soul_id=soul_id, image_refs=([cref] if cref else None) or image_refs,
                                      kernel=kernel)
        return res["path"]
    if kind == "audio":
        out = os.path.join(output_dir, base + ".wav")
        res = render_audio_higgsfield(visual_prompt, out, model=job_type)
        return res["path"]
    out = os.path.join(output_dir, output_name or f"scene_{scene_number}.mp4")
    if cref:
        print(f"[HIGGSFIELD] scene {scene_number}: i2v via {job_type} from {os.path.basename(str(cref))}")
        res = render_i2v_higgsfield(visual_prompt, out, start_image=cref, model=job_type,
                                    duration=duration_seconds, aspect_ratio=aspect_ratio,
                                    end_image=end_image, audio_refs=[audio_ref] if audio_ref else None,
                                    image_refs=image_refs, kernel=kernel)
    else:
        print(f"[HIGGSFIELD] scene {scene_number}: t2v via {job_type} (no locked frame — prefer a keyframe)")
        res = render_t2v_higgsfield(visual_prompt, out, model=job_type, duration=duration_seconds,
                                    aspect_ratio=aspect_ratio, kernel=kernel)
    print(f"[HIGGSFIELD] scene {scene_number} -> {res['path']} (job {res['job_id']}, ~{res['credits']} cr)")
    return res["path"]


# --------------------------------------------------------------------------- #
# Batch preview (Higgsfield "cost first" applied to a whole song manifest)
# --------------------------------------------------------------------------- #
def preview_manifest_cost(manifest_path: str, model: str = "higgsfield:kling3_0", resolution: str = "720p") -> dict:
    """Estimate the credit cost of rendering every shot in an ilyrium-shots song manifest through
    one Higgsfield video route (durations from each spec). Read-only; no jobs are created."""
    with open(manifest_path, encoding="utf-8") as f:
        man = json.load(f)
    base_dir = os.path.dirname(manifest_path)
    job_type, _ = route(model)
    total, rows = 0.0, []
    for s in man.get("shots", []):
        spec_path = os.path.join(base_dir, s["spec_path"])
        try:
            spec = json.load(open(spec_path, encoding="utf-8"))
        except OSError:
            continue
        dur = int(round(spec.get("duration_s", 5)))
        params = {"duration": max(dur, 3 if job_type.startswith("kling") else 4)}
        if job_type in ("seedance_2_0", "seedance_2_5"):
            params["resolution"] = resolution; params["mode"] = "std"
        if job_type == "kling3_0":
            params["mode"] = "std"
        try:
            c = estimate_cost(job_type, spec.get("prompt", "shot"), params, {})
        except HiggsfieldError as e:
            c = float("nan"); rows.append((spec["shot_id"], dur, str(e))); continue
        total += c
        rows.append((spec["shot_id"], dur, c))
    return {"model": job_type, "shots": rows, "total_credits": total}


if __name__ == "__main__":  # tiny CLI: python media/higgsfield_renderer.py cost <manifest> [model]
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "cost":
        res = preview_manifest_cost(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "higgsfield:kling3_0")
        for r in res["shots"]:
            print(f"  {r[0]}  {r[1]}s  {r[2]}")
        print(f"TOTAL ~{res['total_credits']} credits via {res['model']}")
    else:
        print(__doc__)
