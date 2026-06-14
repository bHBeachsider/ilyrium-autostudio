#!/usr/bin/env python3
"""
shot_to_comfy.py  -  Ilyrium Stage 4 bridge.

Turns one validated shot-spec (Stage 2 artifact) into a /prompt call against the
working Wan 2.2 14B I2V ComfyUI graph, then waits for the rendered clip.

This operates on an EXPORTED API-format copy of YOUR working graph rather than
hardcoding node IDs, because node IDs are specific to your template and shift
between ComfyUI versions. The NODE_MAP is now DERIVED automatically from the
exported graph at runtime via comfy_automap (no more hand-filling).

ONE-TIME SETUP
--------------
1. In ComfyUI, with the working Wan I2V graph loaded:
     Workflow -> Export (API)   ->  save as  wan_i2v.api.json
2. Sanity-check the derived map (optional, recommended):
     python comfy_automap.py --automap wan_i2v.api.json --apply example_shot.json
   Read the warnings; confirm each role lands on a sensible node.field.

RUN
---
   python shot_to_comfy.py --spec example_shot.json --template wan_i2v.api.json \
       --comfy http://127.0.0.1:8188 --schema shot_spec.schema.json \
       --upload NH-S03-SH012_key.png --emit-json
"""

import argparse, copy, json, time, uuid, os, sys
from pathlib import Path

# RSI L0 (ILY-203): every ComfyUI API call is delegated to the execution
# harness (harness/run.py), which records request/response pairs for replay
# and emits the JSONL trace. Raw urllib against ComfyUI is banned outside
# harness/ by the lint gate.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from harness import run as harness_run

from comfy_automap import load_api_graph, automap

# NODE_MAP is DERIVED from the exported graph at runtime (see derive_node_map /
# build_prompt). Kept as module globals so build_prompt can populate them once.
NODE_MAP = {}            # logical field -> (node_id, input_key)
SEED_TARGETS = []        # ALL (node_id, field) seed slots (Wan 2.2 has two samplers)

# ---- GRAPH-SPECIFIC OVERRIDES (update if you RE-EXPORT the graph) -------
# Some roles can't be auto-derived because they're generic primitives feeding a
# math node, not labeled inputs. In THIS graph, WanImageToVideo.length is wired
# from a ComfyMathExpression `floor(a*b+1)` (the Wan 4n+1 rule), where:
#     a = duration in seconds   (PrimitiveFloat)
#     b = fps                   (PrimitiveFloat)
# So we drive those two primitives and let the graph compute the frame count.
# Node IDs are fixed within an exported file but CHANGE on re-export -- if you
# re-export wan_i2v.api.json, re-confirm these with:
#     python comfy_automap.py --inspect wan_i2v.api.json
GRAPH_OVERRIDES = {
    "duration_s": ("129:161", "value"),   # PrimitiveFloat feeding math 'a'
    "fps":        ("129:162", "value"),   # PrimitiveFloat feeding math 'b'
    # "length" is intentionally NOT mapped -- it's computed by the graph.
    #
    # This graph has a built-in fast/quality toggle: a single PrimitiveBoolean
    # (129:131) feeds ComfySwitchNodes that select steps/split/cfg together.
    #   True  -> lightx2v 4-step path  (steps 4,  split 2, cfg 1.0)  ~fast
    #   False -> quality path          (steps 20, split 10, cfg 3.5) ~slow
    # We drive that boolean from the spec's render.quality ("fast" | "full").
    # Default is fast. (If you re-export, re-confirm this node ID via --inspect.)
    "fast_mode":  ("129:131", "value"),
}

# Roles in GRAPH_OVERRIDES may be a single (node, field) tuple, a LIST of such
# tuples (apply to all), or None (skip).

DEFAULTS = {"width": 640, "height": 640, "duration_s": 5, "fps": 16, "quality": "fast",
            "negative_prompt": "text, watermark, blurry, distorted, low quality"}


# ---- helpers ------------------------------------------------------------
def _load_json(path):
    """Read JSON as UTF-8 explicitly (Windows defaults to cp1252, which chokes
    on smart quotes / em-dashes in ComfyUI exports and prompt text)."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _get(url):
    return harness_run.http_get_json(url)

def _post(url, payload):
    return harness_run.http_post_json(url, payload)


def derive_node_map(template_path):
    """Auto-derive NODE_MAP + SEED_TARGETS from the exported API graph.

    comfy_automap walks the graph topology and returns role -> {node, field}
    (seed may be a LIST when the workflow has multiple samplers). We project that
    onto this script's (node_id, input_key) tuple shape, and keep every seed slot
    in SEED_TARGETS so all samplers get the same seed.
    """
    global NODE_MAP, SEED_TARGETS
    graph = load_api_graph(template_path)
    nm, warnings = automap(graph)
    for w in warnings:
        print(f"[automap warning] {w}", file=sys.stderr)

    def one(role):
        v = nm.get(role)
        if v is None:
            return None
        if isinstance(v, list):
            v = v[0]
        return (v["node"], v["field"])

    NODE_MAP = {
        "positive_prompt": one("positive_prompt"),
        "negative_prompt": one("negative_prompt"),
        "load_image":      one("load_image"),
        "seed":            one("seed"),
        "width":           one("width"),
        "height":          one("height"),
        # NOTE: 'length'/frame-count is NOT taken from automap here -- in this graph
        # it is computed by a math node. Driven via GRAPH_OVERRIDES instead.
    }
    st = nm.get("seed")
    st = st if isinstance(st, list) else ([st] if st else [])
    SEED_TARGETS = [(t["node"], t["field"]) for t in st]
    return NODE_MAP


def inspect_workflow(template_path):
    """Print every node so you can eyeball the graph. (comfy_automap --inspect is richer.)"""
    wf = _load_json(template_path)
    interesting = ("text", "image", "width", "height", "duration",
                   "noise_seed", "seed", "frames", "length")
    print(f"{'id':>6}  {'class_type':32}  notable inputs")
    print("-" * 80)
    for nid, node in wf.items():
        ct = node.get("class_type", "?")
        ins = node.get("inputs", {})
        notable = {k: v for k, v in ins.items()
                   if k in interesting and not isinstance(v, list)}  # skip wired links
        print(f"{nid:>6}  {ct:32}  {notable}")
    print("\nTip: run  python comfy_automap.py --automap <template> --apply <spec>")


def validate(spec, schema_path):
    if not schema_path:
        return
    try:
        import jsonschema
    except ImportError:
        print("[warn] jsonschema not installed; skipping validation", file=sys.stderr)
        return
    jsonschema.validate(spec, _load_json(schema_path))


def build_prompt(spec, template_path):
    """Patch the exported template with this shot's values. Returns the graph dict."""
    wf = copy.deepcopy(_load_json(template_path))
    derive_node_map(template_path)   # populate NODE_MAP + SEED_TARGETS from the real graph
    render = spec.get("render", {})

    # Timing: drive the duration_s and fps PRIMITIVES; the graph's math node
    # computes the WanImageToVideo frame count (floor(s*fps+1), already 4n+1).
    fps = render.get("fps", DEFAULTS["fps"])
    duration_s = render.get("duration_s", spec.get("duration_s", DEFAULTS["duration_s"]))
    seed = spec.get("seed", spec.get("keyframe", {}).get("seed"))

    values = {
        "positive_prompt": spec["prompt"],
        "negative_prompt": spec.get("negative_prompt", DEFAULTS["negative_prompt"]),
        "load_image":      spec.get("keyframe", {}).get("image"),
        "seed":            seed,
        "width":           render.get("width", DEFAULTS["width"]),
        "height":          render.get("height", DEFAULTS["height"]),
    }

    for field, target in NODE_MAP.items():
        if target is None:
            continue
        node_id, input_key = target
        val = values.get(field)
        if val is None:
            continue
        if node_id not in wf:
            raise KeyError(f"NODE_MAP['{field}'] points at node '{node_id}' not in template")
        wf[node_id]["inputs"][input_key] = val

    # Graph-specific overrides: timing primitives + fast/quality switch.
    quality = render.get("quality", spec.get("quality", DEFAULTS["quality"]))
    fast_mode = (str(quality).lower() != "full")   # "fast" (default) -> True; "full" -> False
    override_values = {"duration_s": duration_s, "fps": fps, "fast_mode": fast_mode}
    for field, target in GRAPH_OVERRIDES.items():
        if target is None:                     # role disabled (e.g. steps until configured)
            continue
        val = override_values.get(field)
        if val is None:
            continue
        targets = target if isinstance(target, list) else [target]
        for node_id, input_key in targets:
            if node_id not in wf:
                print(f"[warn] GRAPH_OVERRIDES['{field}'] node '{node_id}' not in template "
                      f"(did you re-export? re-confirm IDs)", file=sys.stderr)
                continue
            wf[node_id]["inputs"][input_key] = val

    # Patch EVERY seed slot: Wan 2.2's two-stage (high/low) sampler shares one seed.
    if seed is not None:
        for node_id, input_key in SEED_TARGETS:
            if node_id in wf:
                wf[node_id]["inputs"][input_key] = seed
    return wf


def upload_image(comfy, local_path):
    """Push a keyframe to ComfyUI/input so LoadImage can reference it by filename."""
    return harness_run.comfy_upload_image(comfy, local_path)


def submit(comfy, graph, client_id):
    return harness_run.comfy_submit_prompt(comfy, graph, client_id)


def wait(comfy, prompt_id, timeout=900, poll=3):
    """Poll /history until the prompt completes; return output file records."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        hist = _get(f"{comfy}/history/{prompt_id}")
        if prompt_id in hist:
            outputs = hist[prompt_id].get("outputs", {})
            files = []
            for node_out in outputs.values():
                for key in ("gifs", "videos", "images"):
                    for f in node_out.get(key, []):
                        files.append(f.get("filename"))
            return files
        time.sleep(poll)
    raise TimeoutError(f"prompt {prompt_id} did not finish within {timeout}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inspect", help="print nodes of an exported API workflow and exit")
    ap.add_argument("--spec", help="path to a shot-spec json")
    ap.add_argument("--template", help="exported API-format workflow json")
    ap.add_argument("--comfy", default="http://127.0.0.1:8188")
    ap.add_argument("--schema", help="shot_spec.schema.json for validation")
    ap.add_argument("--upload", help="local keyframe image to upload before running")
    ap.add_argument("--emit-json", action="store_true",
                    help="print {'prompt_id': ...} as the final stdout line (for batch_render)")
    args = ap.parse_args()

    if args.inspect:
        inspect_workflow(args.inspect)
        return

    if not (args.spec and args.template):
        ap.error("--spec and --template are required to render")

    spec = _load_json(args.spec)
    validate(spec, args.schema)
    print(f"[ok] {spec['shot_id']} validated")

    # One trace row per submission; all HTTP inside is recorded for replay.
    with harness_run.invocation(
            project_id=spec.get("song_id") or "adhoc",
            task_type="comfy_submit", agent="shot_renderer",
            song_id=spec.get("song_id"), shot_id=spec.get("shot_id"),
            replayable=True,
            reasoning_summary="stage-4 bridge: shot spec -> ComfyUI /prompt"):
        if args.upload:
            info = upload_image(args.comfy, args.upload)
            print(f"[ok] uploaded keyframe -> {info}")
            spec.setdefault("keyframe", {})["image"] = info["name"]

        graph = build_prompt(spec, args.template)
        client_id = uuid.uuid4().hex
        pid = submit(args.comfy, graph, client_id)
        print(f"[ok] submitted prompt_id={pid}; waiting...")
        files = wait(args.comfy, pid)
    print(f"[done] {spec['shot_id']} -> outputs: {files}")
    if args.emit_json:
        print(json.dumps({"prompt_id": pid}))


if __name__ == "__main__":
    main()
