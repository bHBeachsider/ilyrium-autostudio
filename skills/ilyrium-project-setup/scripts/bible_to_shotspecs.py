#!/usr/bin/env python3
"""
bible_to_shotspecs.py  -  Ilyrium project-setup skill: the bible -> render bridge.

Turns a project's Stage-2 scene cards (02_script/scenes.json) into Stage-2
SHOT SPECS that the ilyrium-shots render engine consumes -- each conformant to
ilyrium-shots/shot_spec.schema.json -- plus a batch_render-compatible song
manifest (song_<id>.json). This closes the gap between the creative bible/script
(human-authored) and the deterministic render pipeline (machine-consumed).

What it does per scene card:
  * infers camera shot_size / movement / lens from the visual_prompt,
  * carries setting (location), action, mood (performance), subjects (characters),
  * builds the t2i prompt (visual_prompt + the project's style-kernel look),
  * pulls the project's negative-prompt library,
  * resolves keyframe.ref_lora for the scene's lead character against the LoRA
    library (exact/character/prefix match), or forward-references the canonical
    character key so registering a LoRA later completes the wire,
  * assigns deterministic seeds and prev_shot continuity,
  * splits any scene longer than --max-shot-s into multiple ordered shots.

It NEVER invents identity: characters are carried by their casting-canon keys, and
the prompt is the author's visual_prompt plus the enforced kernel look -- nothing
about real people is added.

USAGE
-----
  python bible_to_shotspecs.py --project projects/new_harnomy_usa --song-id NH-S03 \
      --out-dir ilyrium-shots --schema ilyrium-shots/shot_spec.schema.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

# RSI L0 (ILY-203 task 9): model/tier selection comes from policies/routing.yaml
# through the harness, not hardcoded here; the harness also stamps the
# shot_spec_generator agent version onto the manifest and emits a trace.
# Best-effort so this script still runs standalone outside the repo.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
try:
    from harness import run as harness_run
    from harness import config_hash as _ch
except Exception:  # pragma: no cover - standalone fallback
    harness_run = None
    _ch = None

GENERATOR_AGENT = "shot_spec_generator"
GENERATOR_TASK_TYPE = "bible_to_shotspec"

# ---- camera inference ---------------------------------------------------
LENS_BY_SIZE = {"extreme-wide": 16, "wide": 24, "two-shot": 35, "medium": 50,
                "close-up": 85, "macro": 100}


def infer_shot_size(text: str) -> str:
    t = (text or "").lower()
    if "extreme wide" in t or "extreme-wide" in t:
        return "extreme-wide"
    if "two-shot" in t or "two shot" in t:
        return "two-shot"
    if "macro" in t:
        return "macro"
    if "close-up" in t or "close up" in t or "closeup" in t:
        return "close-up"
    if "wide" in t or "establishing" in t:
        return "wide"
    return "medium"


def infer_movement(text: str) -> str:
    t = (text or "").lower()
    if "locked-off" in t or "locked off" in t or "no camera movement" in t or "locked" in t:
        return "locked-off"
    if "push-in" in t or "push in" in t or "dolly in" in t:
        return "slow push-in"
    if "pull-out" in t or "pull out" in t or "dolly out" in t:
        return "slow pull-out"
    if "track" in t:
        return "tracking"
    if "pan" in t:
        return "slow pan"
    if "tilt" in t:
        return "slow tilt"
    if "handheld" in t or "hand-held" in t:
        return "handheld"
    return "static"


# ---- inputs -------------------------------------------------------------
def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_negative_prompts(project_dir, default):
    p = os.path.join(project_dir, "NEGATIVE_PROMPTS.txt") if project_dir else None
    if p and os.path.exists(p):
        lines = [ln.strip() for ln in open(p, encoding="utf-8").read().splitlines() if ln.strip()]
        if lines:
            return ", ".join(lines)
    return default


def load_kernel_look(project_dir):
    p = os.path.join(project_dir, "style_kernel.json") if project_dir else None
    if p and os.path.exists(p):
        try:
            return (_load_json(p).get("look") or "").strip()
        except (ValueError, OSError):
            return ""
    return ""


def load_lora_index_from_entries(entries):
    """Build {character_key: ref_lora_name} from a list of lora_library entries.
    Matches by explicit 'character' field, by exact name, and by name-without-_vN suffix."""
    index = {}
    for e in entries or []:
        name = e.get("name")
        if not name:
            continue
        keys = set()
        if e.get("character"):
            keys.add(str(e["character"]).lower())
        keys.add(name.lower())
        keys.add(re.sub(r"_v\d+$", "", name.lower()))  # lincoln_satirical_v2 -> lincoln_satirical
        for k in keys:
            index.setdefault(k, name)
    return index


def load_lora_index(paths):
    """Build {character_key: ref_lora_name} from one or more lora_library.json files."""
    entries = []
    for p in paths:
        if not p or not os.path.exists(p):
            continue
        try:
            entries.extend(_load_json(p).get("loras", []))
        except (ValueError, OSError):
            continue
    return load_lora_index_from_entries(entries)


def resolve_ref_lora(character, lora_index, forward_ref):
    """character (casting-canon key) -> registered LoRA name, or forward-ref key, or ''."""
    if not character:
        return ""
    c = character.lower()
    if c in lora_index:
        return lora_index[c]
    # prefix match: character 'lincoln' resolves 'lincoln_satirical_v2'
    for key, name in lora_index.items():
        if key.startswith(c + "_") or key == c:
            return name
    return character if forward_ref else ""


# ---- generation ---------------------------------------------------------
def split_durations(total, max_s):
    """Split a scene duration into 1..N shot durations each in [1, min(10,max_s)]."""
    cap = min(10, max_s)
    total = max(1, int(round(total or cap)))
    n = max(1, math.ceil(total / cap))
    base = total // n
    rem = total - base * n
    out = []
    for i in range(n):
        d = base + (1 if i < rem else 0)
        out.append(max(1, min(10, d)))
    return out


def scene_to_shots(scene, song_id, seq_start, seed_base, lora_index, kernel_look,
                   negatives, defaults, max_shot_s, forward_ref):
    scene_no = scene.get("scene_number", seq_start)
    scene_id = f"{song_id}-SC{int(scene_no):02d}"
    chars = scene.get("characters") or []
    lead = chars[0] if chars else ""
    ref_lora = resolve_ref_lora(lead, lora_index, forward_ref)

    shot_size = infer_shot_size(scene.get("visual_prompt", ""))
    movement = infer_movement(scene.get("visual_prompt", ""))
    lens = LENS_BY_SIZE.get(shot_size, 50)

    base_prompt = (scene.get("visual_prompt") or scene.get("action") or "shot").strip()
    prompt = base_prompt
    if kernel_look and kernel_look.lower() not in base_prompt.lower():
        prompt = f"{base_prompt}, {kernel_look}"
    mood = (scene.get("performance") or "").split(";")[0].strip() or "neutral"

    durations = split_durations(scene.get("duration_target_s"), max_shot_s)
    shots = []
    for i, dur in enumerate(durations):
        seq = seq_start + i
        shot_id = f"{song_id}-SH{seq:03d}"
        seed = seed_base + seq
        spec = {
            "shot_id": shot_id,
            "song_id": song_id,
            "duration_s": dur,
            "camera": {"shot_size": shot_size, "movement": movement, "lens_mm": lens},
            "subjects": chars,
            "setting": (scene.get("location") or "unspecified").strip() or "unspecified",
            "mood": mood,
            "action": (scene.get("action") or base_prompt).strip(),
            "prompt": prompt,
            "negative_prompt": negatives,
            "keyframe": {"source": "t2i", "ref_lora": ref_lora, "seed": seed},
            "seed": seed,
            "continuity": {"prev_shot": "", "flf2v": False},  # filled by caller
            "render": {
                "width": defaults["width"], "height": defaults["height"],
                "fps": defaults["fps"], "steps": defaults["steps"], "duration_s": dur,
            },
        }
        shots.append({"spec": spec, "scene_id": scene_id, "sequence_index": seq,
                      "scene_number": int(scene_no)})
    return shots


def generate(scenes, song_id, seed_base, lora_index, kernel_look, negatives,
             defaults, max_shot_s, forward_ref):
    all_shots = []
    seq = 1
    for scene in scenes:
        produced = scene_to_shots(scene, song_id, seq, seed_base, lora_index,
                                  kernel_look, negatives, defaults, max_shot_s, forward_ref)
        all_shots.extend(produced)
        seq += len(produced)
    # continuity: prev_shot + flf2v (true when chaining within the same scene)
    for i, item in enumerate(all_shots):
        if i == 0:
            continue
        prev = all_shots[i - 1]
        item["spec"]["continuity"]["prev_shot"] = prev["spec"]["shot_id"]
        item["spec"]["continuity"]["flf2v"] = (prev["scene_number"] == item["scene_number"])
    return all_shots


def resolve_generator_routing():
    """Model/tier for shot-spec generation, from policies/routing.yaml via the
    harness — plus this generator's config-hash agent version. Returns a dict
    (empty if the harness is unavailable / standalone)."""
    if harness_run is None:
        return {}
    route = harness_run.routing_for(GENERATOR_TASK_TYPE)
    d = harness_run.agent_dir(GENERATOR_AGENT)
    model = (_ch.default_model(d) if d is not None else None) or route.get("model")
    stamp = harness_run.stamp_agent(GENERATOR_AGENT, None, model or "")
    return {
        "task_type": GENERATOR_TASK_TYPE,
        "tier": route.get("tier"),
        "model": model,
        "agent": GENERATOR_AGENT,
        "agent_version": stamp.get("agent_version"),
        "agent_version_id": stamp.get("agent_version_id"),
    }


def build_manifest(song_id, shots, defaults, comfy_url, template, schema_name,
                   generator=None):
    return {
        "song_id": song_id,
        "comfy_url": comfy_url,
        "template": template,
        "schema": schema_name,
        "node_map_version": "1",
        "defaults": defaults,
        # RSI L0: which agent version + model produced these specs (from routing).
        "generator": generator or {},
        "engine": {"comfyui_version": None, "gpu": "NVIDIA L4 24GB",
                   "instance_id": None, "torch": None, "cuda": None},
        "shots": [
            {"shot_id": s["spec"]["shot_id"], "scene_id": s["scene_id"],
             "sequence_index": s["sequence_index"],
             "spec_path": f"shots/{s['spec']['shot_id']}.json",
             "keyframe": f"keyframes/{s['spec']['shot_id']}_key.png",
             "seed": s["spec"]["seed"]}
            for s in shots
        ],
    }


def validate_specs(shots, schema_path):
    if not schema_path or not os.path.exists(schema_path):
        return True, "schema not found; skipped validation"
    try:
        import jsonschema
    except ImportError:
        return True, "jsonschema not installed; skipped validation"
    schema = _load_json(schema_path)
    for s in shots:
        jsonschema.validate(s["spec"], schema)
    return True, f"all {len(shots)} specs valid"


def write_outputs(shots, manifest, out_dir):
    shots_dir = os.path.join(out_dir, "shots")
    os.makedirs(shots_dir, exist_ok=True)
    for s in shots:
        sid = s["spec"]["shot_id"]
        Path(os.path.join(shots_dir, f"{sid}.json")).write_text(
            json.dumps(s["spec"], indent=2) + "\n", encoding="utf-8")
    manifest_path = os.path.join(out_dir, f"song_{manifest['song_id']}.json")
    Path(manifest_path).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


DEFAULT_NEG = "text, watermark, blurry, distorted, low quality"


def main():
    ap = argparse.ArgumentParser(description="Generate ilyrium-shots shot specs from scene cards")
    ap.add_argument("--project", help="project dir (reads scenes.json, style_kernel.json, negatives, lora_library)")
    ap.add_argument("--scenes", help="explicit path to scenes.json (overrides --project/02_script/scenes.json)")
    ap.add_argument("--song-id", required=True, help="song id, e.g. NH-S03 (must match ^NH-S[0-9]{2,}$)")
    ap.add_argument("--out-dir", default=".", help="where to write shots/ + song_<id>.json")
    ap.add_argument("--schema", help="shot_spec.schema.json to validate emitted specs against")
    ap.add_argument("--lora-library", action="append", default=[],
                    help="lora_library.json path(s); may repeat. Defaults to project + ilyrium-shots if found")
    ap.add_argument("--seed-base", type=int, default=100000)
    ap.add_argument("--max-shot-s", type=int, default=8, help="max seconds per shot before splitting (<=10)")
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=640)
    ap.add_argument("--fps", type=int, default=16)
    ap.add_argument("--steps", type=int, default=4)
    ap.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    ap.add_argument("--template", default="wan_i2v.api.json")
    ap.add_argument("--no-kernel-look", action="store_true", help="do not append the style-kernel look to prompts")
    ap.add_argument("--no-forward-ref", action="store_true",
                    help="leave ref_lora empty when no registered LoRA matches (default: forward-reference the character key)")
    args = ap.parse_args()

    if not re.match(r"^NH-S[0-9]{2,}$", args.song_id):
        ap.error("--song-id must match ^NH-S[0-9]{2,}$ (e.g. NH-S03)")

    scenes_path = args.scenes or (os.path.join(args.project, "02_script", "scenes.json")
                                  if args.project else None)
    if not scenes_path or not os.path.exists(scenes_path):
        ap.error(f"scenes.json not found ({scenes_path})")
    scenes = _load_json(scenes_path)
    if not isinstance(scenes, list):
        ap.error("scenes.json must be a JSON array of scene cards")

    kernel_look = "" if args.no_kernel_look else load_kernel_look(args.project)
    negatives = load_negative_prompts(args.project, DEFAULT_NEG)

    lib_paths = list(args.lora_library)
    if not lib_paths and args.project:
        cand = os.path.join(args.project, "03_design", "characters", "loras", "lora_library.json")
        if os.path.exists(cand):
            lib_paths.append(cand)
    lora_index = load_lora_index(lib_paths)

    defaults = {"width": args.width, "height": args.height, "fps": args.fps,
                "steps": args.steps, "cfg": 1.0, "sampler": "euler",
                "scheduler": "simple", "frames": 81}

    shots = generate(scenes, args.song_id, args.seed_base, lora_index, kernel_look,
                     negatives, defaults, args.max_shot_s, not args.no_forward_ref)
    if not shots:
        ap.error("no shots generated (empty scenes.json?)")

    ok, msg = validate_specs(shots, args.schema)
    print(f"[validate] {msg}")

    generator = resolve_generator_routing()
    if generator:
        print(f"[routing] {generator['task_type']} -> tier={generator.get('tier')} "
              f"model={generator.get('model')} "
              f"agent={generator.get('agent')}@{generator.get('agent_version')}")

    manifest = build_manifest(args.song_id, shots, defaults, args.comfy_url,
                              args.template, os.path.basename(args.schema) if args.schema else "shot_spec.schema.json",
                              generator=generator)
    manifest_path = write_outputs(shots, manifest, args.out_dir)
    print(f"[ok] {len(shots)} shot spec(s) -> {os.path.join(args.out_dir, 'shots')}/")
    print(f"[ok] manifest -> {manifest_path}")

    # Emit one trace row for the generation (replayable=False: deterministic,
    # not a model call to replay — it is reproducible from scenes.json).
    if harness_run is not None and generator:
        try:
            with harness_run.invocation(
                    project_id=args.song_id, task_type=GENERATOR_TASK_TYPE,
                    agent=GENERATOR_AGENT, model=generator.get("model"),
                    song_id=args.song_id, replayable=False,
                    reasoning_summary=f"generated {len(shots)} shot spec(s) from scene cards") as inv:
                inv.record_tool_call(
                    "bible_to_shotspecs",
                    {"scenes": scenes_path, "song_id": args.song_id},
                    {"n_shots": len(shots), "manifest": manifest_path,
                     "validate": msg})
                inv.set(n_shots=len(shots))
        except Exception as _e:
            print(f"[trace] skipped: {_e}")
    # quick per-shot recap
    for s in shots:
        sp = s["spec"]
        print(f"   {sp['shot_id']}  {sp['camera']['shot_size']:<12} {sp['duration_s']}s  "
              f"lead_lora={sp['keyframe']['ref_lora'] or '-'}")


if __name__ == "__main__":
    main()
