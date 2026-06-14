"""Ilyrium batch runner -- walk a song's shot list, render each shot, and write a
full provenance ledger entry for every attempt.

The runner owns orchestration + provenance only. Rendering is delegated to a
``Renderer`` (the default shells out to ``shot_to_comfy.py`` for the submit, then
polls ComfyUI's ``/history`` to harvest + hash the outputs). A ``FakeRenderer``
lets the whole pipeline run end-to-end with no GPU box (``--dry-run``).

Per shot the lifecycle is: queued -> rendering -> rendered (or failed), each step
appended as a new chained snapshot via provenance.Ledger.

Manifest (JSON)
---------------
{
  "song_id": "NH-07",
  "comfy_url": "http://127.0.0.1:8188",
  "template": "wan_i2v.api.json",
  "schema": "shot_spec.schema.json",
  "defaults": {"width":640,"height":640,"frames":49,"fps":16,"steps":4,
               "cfg":1.0,"sampler":"euler","scheduler":"simple"},
  "engine":   {"comfyui_version":"0.3.x","gpu":"NVIDIA L4 24GB",
               "instance_id":"i-030994c5371ee5de9","torch":"2.4.1+cu124","cuda":"12.4"},
  "shots": [
    {"shot_id":"NH07-S012","scene_id":"NH07-SC03","sequence_index":12,
     "spec_path":"shots/NH07-S012.json", "keyframe":"keyframes/NH07-S012.png",
     "seed":482913}
  ]
}

A shot may carry an inline "spec" instead of "spec_path", and may override any
"defaults" key inline.

Models lock (JSON) -- list of every weight, with a precomputed sha256:
  [ {"role":"vae","filename":"wan_2.1_vae.safetensors","sha256":"<hex>",
     "source":{"hf_repo":"...","hf_revision":"main"}}, ... ]
Generate it once on the box with --lock-models (hashes the files in models_root).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# RSI L0 (ILY-203): all ComfyUI HTTP goes through the execution harness, which
# records tool calls for replay and emits one JSONL trace row per render.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from harness import run as harness_run  # noqa: E402

import provenance as pv  # noqa: E402

VIDEO_EXTS = {".mp4", ".webm", ".mkv", ".mov", ".gif"}

RENDER_AGENT = "shot_renderer"          # agents/shot_renderer/<version>/
RENDER_TASK_TYPE = "video_render"       # policies/routing.yaml T4 entry


# --------------------------------------------------------------------------- #
# ComfyUI HTTP client (generic; transport delegated to the harness)
# --------------------------------------------------------------------------- #
class ComfyClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    def system_stats(self) -> Dict[str, Any]:
        return harness_run.comfy_system_stats(self.base)

    def history(self, prompt_id: str) -> Dict[str, Any]:
        return harness_run.comfy_history(self.base, prompt_id)

    def download(self, filename: str, subfolder: str, type_: str, dest_dir: Path) -> Path:
        data = harness_run.comfy_view(self.base, filename, subfolder, type_)
        dest_dir.mkdir(parents=True, exist_ok=True)
        out = dest_dir / filename
        out.write_bytes(data)
        return out

    @staticmethod
    def parse_history_outputs(history: Dict[str, Any], prompt_id: str) -> List[Dict[str, str]]:
        """Flatten ComfyUI /history node outputs into {filename, subfolder, type} dicts.

        Pure function so it can be unit-tested without a live server.
        """
        entry = history.get(prompt_id) or {}
        node_outputs = entry.get("outputs", {}) or {}
        files: List[Dict[str, str]] = []
        for node in node_outputs.values():
            for bucket in ("gifs", "videos", "images"):
                for item in node.get(bucket, []) or []:
                    if "filename" in item:
                        files.append({
                            "filename": item["filename"],
                            "subfolder": item.get("subfolder", ""),
                            "type": item.get("type", "output"),
                        })
        return files

    def await_history(self, prompt_id: str, *, poll: float = 2.0, timeout: float = 1800.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            hist = self.history(prompt_id)
            if prompt_id in hist:
                outs = self.parse_history_outputs(hist, prompt_id)
                if outs:
                    return outs
            time.sleep(poll)
        raise TimeoutError(f"render {prompt_id} did not complete within {timeout}s")


def _kind_for(filename: str) -> str:
    return "video" if Path(filename).suffix.lower() in VIDEO_EXTS else "preview_frame"


# --------------------------------------------------------------------------- #
# Renderers
# --------------------------------------------------------------------------- #
class Renderer:
    """submit(record) -> prompt_id ; await_outputs(prompt_id, out_dir) -> [output dict]."""

    def submit(self, record: Dict[str, Any], *, spec_file: Path, keyframe: Optional[str]) -> str:
        raise NotImplementedError

    def await_outputs(self, prompt_id: str, out_dir: Path) -> List[Dict[str, Any]]:
        raise NotImplementedError


class SubprocessRenderer(Renderer):
    """Delegates the submit to shot_to_comfy.py, then harvests via ComfyClient.

    Integration contract (one small change to shot_to_comfy.py if not already present):
    when invoked with ``--emit-json`` it must print, as its final stdout line, a JSON
    object containing at least ``{"prompt_id": "<id>"}``. If it also emits
    ``"outputs": [{"filename","subfolder","type"}, ...]`` those are used directly and
    the /history poll is skipped.
    """

    def __init__(self, client: ComfyClient, *, script: str, template: str, schema: str,
                 python_exe: str = sys.executable, poll: float = 2.0, timeout: float = 1800.0,
                 comfy_url: str = "http://127.0.0.1:8188"):
        self.client = client
        self.script = script
        self.template = template
        self.schema = schema
        self.python = python_exe
        self.poll = poll
        self.timeout = timeout
        self.comfy_url = comfy_url
        self._last_submit_outputs: List[Dict[str, str]] = []

    def submit(self, record: Dict[str, Any], *, spec_file: Path, keyframe: Optional[str]) -> str:
        cmd = [self.python, self.script, "--spec", str(spec_file),
               "--template", self.template, "--schema", self.schema, "--emit-json", "--comfy", self.comfy_url]
        if keyframe:
            cmd += ["--upload", keyframe]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"shot_to_comfy failed ({proc.returncode}): {proc.stderr.strip()[:500]}")
        payload = _last_json_line(proc.stdout)
        if not payload or "prompt_id" not in payload:
            raise RuntimeError("shot_to_comfy did not emit a JSON line with prompt_id "
                               "(needs --emit-json support)")
        self._last_submit_outputs = payload.get("outputs", []) or []
        return payload["prompt_id"]

    def await_outputs(self, prompt_id: str, out_dir: Path) -> List[Dict[str, Any]]:
        files = self._last_submit_outputs or self.client.await_history(
            prompt_id, poll=self.poll, timeout=self.timeout)
        results = []
        for f in files:
            local = self.client.download(f["filename"], f.get("subfolder", ""),
                                         f.get("type", "output"), out_dir)
            results.append(_output_record(local))
        return results


class FakeRenderer(Renderer):
    """No-box renderer: writes a deterministic placeholder file so the full
    provenance flow (and the ledger) can be exercised offline."""

    def __init__(self, out_dir: Path):
        self.out_dir = out_dir
        self._n = 0

    def submit(self, record: Dict[str, Any], *, spec_file: Path, keyframe: Optional[str]) -> str:
        self._n += 1
        return f"dryrun-{record['record_id'][:8]}-{self._n:04d}"

    def await_outputs(self, prompt_id: str, out_dir: Path) -> List[Dict[str, Any]]:
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{prompt_id}.mp4"
        out.write_bytes(b"FAKE-RENDER-" + prompt_id.encode())
        return [_output_record(out)]


def _output_record(path: Path) -> Dict[str, Any]:
    return {
        "kind": _kind_for(path.name),
        "path": str(path),
        "sha256": pv.file_sha256(path),
        "bytes": path.stat().st_size,
        "container": path.suffix.lstrip(".") or None,
        "duration_s": None,
    }


def _last_json_line(text: str) -> Optional[Dict[str, Any]]:
    for line in reversed(text.strip().splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


# --------------------------------------------------------------------------- #
# Record assembly
# --------------------------------------------------------------------------- #
def _load_spec(shot: Dict[str, Any], base: Path) -> Dict[str, Any]:
    if "spec" in shot:
        return shot["spec"]
    if "spec_path" in shot:
        return json.loads((base / shot["spec_path"]).read_text(encoding="utf-8"))
    raise ValueError(f"shot {shot.get('shot_id')} has neither 'spec' nor 'spec_path'")


def _hash_if_exists(base: Path, rel: Optional[str]) -> Optional[str]:
    if not rel:
        return None
    p = base / rel
    return pv.file_sha256(p) if p.exists() else None


def build_record(manifest: Dict[str, Any], shot: Dict[str, Any], models: List[Dict[str, Any]],
                 base: Path, agent_version_id: Optional[str] = None) -> Dict[str, Any]:
    defaults = dict(manifest.get("defaults", {}))
    gen = {k: shot.get(k, defaults.get(k)) for k in
           ("width", "height", "frames", "fps", "steps", "cfg", "sampler", "scheduler")}
    gen["seed"] = shot.get("seed", defaults.get("seed", 0))

    template_rel = manifest["template"]
    template_path = base / template_rel
    gen["workflow_template"] = {
        "name": Path(template_rel).name,
        "sha256": pv.file_sha256(template_path) if template_path.exists() else "0" * 64,
        "node_map_version": manifest.get("node_map_version"),
    }
    kf = shot.get("keyframe")
    kf_hash = _hash_if_exists(base, kf)
    gen["keyframe"] = ({"path": kf, "sha256": kf_hash or "0" * 64,
                        "width": shot.get("keyframe_width"), "height": shot.get("keyframe_height")}
                       if kf else None)

    shot_id = shot["shot_id"]
    rec = pv.new_record(
        shot={"song_id": manifest["song_id"], "shot_id": shot_id,
              "scene_id": shot.get("scene_id"), "sequence_index": shot.get("sequence_index")},
        shot_spec=_load_spec(shot, base),
        generation=gen,
        models=models,
        engine=dict(manifest.get("engine", {})),
        agent_version_id=agent_version_id,
    )
    return rec


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def run(manifest_path: str, models_path: str, *, ledger_dir: str, dry_run: bool,
        no_skip: bool, comfy_url: Optional[str], script: str,
        project_id: Optional[str] = None, project_dir: Optional[str] = None) -> int:
    base = Path(manifest_path).resolve().parent
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    models = json.loads(Path(models_path).read_text(encoding="utf-8"))
    song = manifest["song_id"]
    url = comfy_url or manifest.get("comfy_url", "http://127.0.0.1:8188")

    # RSI L0: stamp the render agent's config-hash identity onto every
    # record/trace. The model id feeding the version hash is the render agent's
    # OWN routing.yaml model, so the stamp matches its registered manifest
    # exactly (not the coarser policy-tier engine).
    project_id = project_id or song
    _render_dir = harness_run.agent_dir(RENDER_AGENT)
    if _render_dir is not None:
        engine_id = harness_run.ch.default_model(_render_dir)
    else:
        route = harness_run.routing_for(RENDER_TASK_TYPE)
        engine_id = route.get("engine") or route.get("model") or "comfyui"
    agent_stamp = harness_run.stamp_agent(RENDER_AGENT, None, engine_id)
    avid = agent_stamp.get("agent_version_id")

    led = pv.Ledger(ledger_dir, schema_path=str(base / "provenance_record.schema.json"))
    out_dir = Path(ledger_dir) / "renders" / song

    if dry_run:
        renderer: Renderer = FakeRenderer(out_dir)
    else:
        client = ComfyClient(url)
        # Fill engine.comfyui_version live if the manifest didn't pin it.
        if not manifest.get("engine", {}).get("comfyui_version"):
            stats = client.system_stats()
            ver = (stats.get("system", {}) or {}).get("comfyui_version")
            if ver:
                manifest.setdefault("engine", {})["comfyui_version"] = ver
        renderer = SubprocessRenderer(
            client, script=script, template=str(base / manifest["template"]),
            schema=str(base / manifest["schema"]), comfy_url=url)

    counts = {"rendered": 0, "failed": 0, "skipped": 0}
    for shot in manifest["shots"]:
        rec = build_record(manifest, shot, models, base, agent_version_id=avid)
        chash = rec["content_hash"]
        if not no_skip:
            dup = led.find_by_content_hash(song, chash, statuses=("rendered", "approved"))
            if dup:
                counts["skipped"] += 1
                print(f"  = skip  {shot['shot_id']}  (content_hash already rendered: {dup['record_id']})")
                continue

        led.append(song, rec)  # queued (genesis or chained)
        rid = rec["record_id"]
        spec_file = out_dir / f"{rid}.spec.json"
        spec_file.parent.mkdir(parents=True, exist_ok=True)
        spec_file.write_text(json.dumps(rec["shot_spec"], ensure_ascii=False), encoding="utf-8")

        try:
            with harness_run.invocation(
                    project_id=project_id, project_dir=project_dir,
                    task_type=RENDER_TASK_TYPE, agent=RENDER_AGENT,
                    model=engine_id, song_id=song, shot_id=shot["shot_id"],
                    replayable=True,
                    reasoning_summary=("dry-run placeholder render" if dry_run else
                                       "i2v render of validated shot spec")) as inv:
                started = pv.now_iso()
                t0 = time.time()
                prompt_id = renderer.submit(rec, spec_file=spec_file, keyframe=shot.get("keyframe"))
                led.transition(song, rid, status="rendering",
                               render={"comfy_prompt_id": prompt_id, "started_at": started,
                                       "finished_at": None, "wall_seconds": None,
                                       "outputs": [], "error": None})
                outputs = renderer.await_outputs(prompt_id, out_dir)
                led.transition(song, rid, status="rendered",
                               render={"comfy_prompt_id": prompt_id, "started_at": started,
                                       "finished_at": pv.now_iso(),
                                       "wall_seconds": round(time.time() - t0, 2),
                                       "outputs": outputs, "error": None})
                inv.record_tool_call(
                    "renderer", {"shot_id": shot["shot_id"], "record_id": rid,
                                 "content_hash": chash, "dry_run": dry_run},
                    {"prompt_id": prompt_id, "outputs": outputs,
                     "shot_spec": rec["shot_spec"]})
                inv.set(provenance_record_id=rid, content_hash=chash)
            counts["rendered"] += 1
            print(f"  + done  {shot['shot_id']}  -> {outputs[0]['path'] if outputs else '(no output)'}")
        except Exception as exc:  # noqa: BLE001 - record the failure, keep going
            led.transition(song, rid, status="failed",
                           render={"started_at": pv.now_iso(), "finished_at": pv.now_iso(),
                                   "wall_seconds": None, "outputs": [], "error": str(exc)})
            counts["failed"] += 1
            print(f"  ! fail  {shot['shot_id']}  -> {exc}")

    ok = led.verify_chain(song)
    print(f"\n{song}: rendered={counts['rendered']} failed={counts['failed']} "
          f"skipped={counts['skipped']}  chain_ok={ok}  ledger={led.path_for(song)}")
    return 0 if (counts["failed"] == 0 and ok) else 1


def lock_models(models_root: str, out_path: str) -> int:
    """Hash every weight under models_root into a models.lock.json. Run on the box."""
    root = Path(models_root)
    role_by_dir = {"diffusion_models": "lora_other", "unet": "lora_other",
                   "vae": "vae", "text_encoders": "text_encoder", "clip": "text_encoder",
                   "loras": "lora_other"}
    locked = []
    for p in sorted(root.rglob("*")):
        if p.suffix.lower() in (".safetensors", ".ckpt", ".pt", ".gguf") and p.is_file():
            parent = p.parent.name
            locked.append({"role": role_by_dir.get(parent, "lora_other"),
                           "filename": p.name, "sha256": pv.file_sha256(p), "source": None})
    Path(out_path).write_text(json.dumps(locked, indent=2), encoding="utf-8")
    print(f"locked {len(locked)} model files -> {out_path} "
          f"(review and fix roles: diffusion_high/low_noise, lora_speed/character)")
    return 0


def lock_lora_library(library_path: str, lockfile_path: str) -> int:
    """Merge trained character LoRAs from lora_library.json into models.lock.json as
    role 'lora_character'. Idempotent: a lora_character row with the same filename is
    replaced; all other lock entries are preserved. Untrained entries (no sha256) are
    skipped with a warning -- you can't pin a weight that doesn't exist yet.

    Lock rows are kept provenance-schema-clean ({role, filename, sha256, source}); the
    LoRA's job/base metadata lives in lora_library.json, not the lockfile, because the
    provenance record's model.source only permits hf_repo/hf_revision."""
    lib = json.loads(Path(library_path).read_text(encoding="utf-8"))
    lock: List[Dict[str, Any]] = []
    p = Path(lockfile_path)
    if p.exists():
        lock = json.loads(p.read_text(encoding="utf-8"))

    by_filename = {e.get("filename"): i for i, e in enumerate(lock)
                   if e.get("role") == "lora_character"}
    merged = skipped = 0
    for entry in lib.get("loras", []):
        fn, sha = entry.get("filename"), entry.get("sha256")
        if not fn or not sha:
            skipped += 1
            print(f"[skip] LoRA '{entry.get('name')}' has no sha256 yet "
                  f"(status={entry.get('status')}); train it before locking", file=sys.stderr)
            continue
        rec = {"role": "lora_character", "filename": fn, "sha256": sha, "source": None}
        if fn in by_filename:
            lock[by_filename[fn]] = rec
        else:
            lock.append(rec)
            by_filename[fn] = len(lock) - 1
        merged += 1
    p.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(f"locked {merged} character LoRA(s) into {lockfile_path} (skipped {skipped} untrained)")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Ilyrium batch render + provenance runner")
    sub = ap.add_subparsers(dest="cmd")

    r = sub.add_parser("render", help="render a song's shot list (default)")
    r.add_argument("--manifest", required=True)
    r.add_argument("--models", required=True, help="models.lock.json")
    r.add_argument("--ledger-dir", default="ledger")
    r.add_argument("--dry-run", action="store_true", help="use FakeRenderer; no GPU box needed")
    r.add_argument("--no-skip", action="store_true", help="do not dedupe by content_hash")
    r.add_argument("--comfy-url", default=None)
    r.add_argument("--script", default="shot_to_comfy.py")
    r.add_argument("--project-id", default=None,
                   help="trace project id (default: the manifest's song_id)")
    r.add_argument("--project-dir", default=None,
                   help="explicit project dir for traces (default: resolve projects/<id>)")

    l = sub.add_parser("lock-models", help="hash weights into models.lock.json (run on the box)")
    l.add_argument("--models-root", required=True)
    l.add_argument("--out", default="models.lock.json")

    ll = sub.add_parser("lock-loras",
                        help="merge trained LoRAs from lora_library.json into models.lock.json")
    ll.add_argument("--library", default="lora_library.json")
    ll.add_argument("--lockfile", default="models.lock.json")

    args = ap.parse_args(argv)
    if args.cmd == "lock-models":
        return lock_models(args.models_root, args.out)
    if args.cmd == "lock-loras":
        return lock_lora_library(args.library, args.lockfile)
    if args.cmd in (None, "render"):
        if args.cmd is None:  # allow bare flags without subcommand
            return ap.print_help() or 2
        return run(args.manifest, args.models, ledger_dir=args.ledger_dir, dry_run=args.dry_run,
                   no_skip=args.no_skip, comfy_url=args.comfy_url, script=args.script,
                   project_id=args.project_id, project_dir=args.project_dir)
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
