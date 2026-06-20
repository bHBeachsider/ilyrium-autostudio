"""
Push projects into the canonical asset graph via the control-panel /api/studio/sync.

Best-effort and non-blocking: if the control-panel isn't running, rendering/scaffolding
still succeeds; the project just isn't mirrored into the graph until the next sync. Local
project.json / scaffold folders remain the working cache; the graph is the record of truth.
"""

import os

SYNC_URL = os.getenv("STUDIO_SYNC_URL", "http://127.0.0.1:3000/api/studio/sync")
ASSET_URL = os.getenv("STUDIO_ASSET_URL", "http://127.0.0.1:3000/api/studio/asset")
RUN_URL = os.getenv("STUDIO_RUN_URL", "http://127.0.0.1:3000/api/studio/run")

# Rough per-engine cost estimate (cents per second of generated video). These are
# ESTIMATES for the cost-per-finished-second telemetry, not billed amounts; override
# with ILYRIUM_ENGINE_RATES (JSON) when real provider pricing is wired.
import json as _json
_DEFAULT_RATES = {"grok-imagine": 4, "grok": 4, "veo3": 40, "veo3.1": 50, "kling": 28,
                  "comfyui": 2, "ue": 2, "keyframe": 12, "moviepy-assembly": 0, "ffmpeg": 0,
                  "runway": 25, "gen4.5": 25, "gen4_aleph": 15, "act_two": 15}
try:
    ENGINE_RATES = {**_DEFAULT_RATES, **_json.loads(os.getenv("ILYRIUM_ENGINE_RATES", "{}"))}
except Exception:
    ENGINE_RATES = dict(_DEFAULT_RATES)


def estimate_cost_cents(model: str, duration_sec) -> int | None:
    rate = ENGINE_RATES.get((model or "").lower().split(":")[0])
    if rate is None:
        return None
    try:
        return int(round(rate * float(duration_sec or 0)))
    except Exception:
        return None


def record_run(external_id: str, entity_type: str, **kw):
    """Record one Run/Trace row (render / assemble / agent action). Best-effort."""
    payload = {"externalId": external_id, "entityType": entity_type}
    payload.update({k: v for k, v in kw.items() if v is not None})
    return _post_to(RUN_URL, payload)


def file_checksum(path: str) -> str:
    """SHA-256 of a file (content-addressing for the asset graph)."""
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sync_asset(external_id: str, uri: str, checksum: str, provider: str = None,
               model: str = None, prompt: str = None, seed: str = None,
               asset_type: str = "video", scene_number=None, cost_cents: int = None,
               storage_provider: str = "local"):
    """Record one rendered asset + its provenance in the graph. Idempotent on checksum."""
    import os as _os
    payload = {
        "externalId": external_id,
        "type": asset_type,
        "uri": uri,
        "checksum": checksum,
        "storageProvider": storage_provider,
        "sizeBytes": (_os.path.getsize(uri) if storage_provider == "local" and _os.path.exists(uri) else None),
        "provider": provider,
        "model": model,
        "seed": seed,
        "prompt": prompt,
        "sceneNumber": scene_number,
        "costCents": cost_cents,
    }
    return _post_to(ASSET_URL, payload)


def _post_to(url: str, payload: dict):
    import requests
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.ok:
            return r.json()
        print(f"[GRAPH SYNC] {url} {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[GRAPH SYNC] skipped ({type(e).__name__}: {e})")
    return None


def _post(payload: dict):
    import requests
    try:
        r = requests.post(SYNC_URL, json=payload, timeout=15)
        if r.ok:
            return r.json()
        print(f"[GRAPH SYNC] {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[GRAPH SYNC] skipped ({type(e).__name__}: {e})")
    return None


def sync_autostudio_project(project: dict, scaffold_path: str = None):
    """Register an auto-studio ad/campaign project (project_store dict) in the graph.
    Each project_store shot becomes a Scene containing one Shot (ads are scene=shot)."""
    kernel = project.get("style_kernel")
    payload = {
        "externalId": project.get("campaign_id"),
        "title": project.get("business_name") or project.get("campaign_id") or "Untitled",
        "type": "AD",
        "styleKernel": kernel if isinstance(kernel, dict) else None,
        "scaffoldPath": scaffold_path,
        "scenes": [
            {
                "number": s.get("scene_number"),
                "title": None,
                "shots": [{"number": s.get("scene_number"), "prompt": s.get("visual_prompt")}],
            }
            for s in sorted(project.get("shots", []), key=lambda x: x.get("scene_number", 0))
        ],
    }
    return _post(payload)


def sync_scaffold_project(slug: str, title: str, kernel: dict = None,
                          scaffold_path: str = None, ptype: str = "SHORT"):
    """Register a scaffolded film project node (+ kernel + scaffold path) in the graph."""
    return _post({
        "externalId": slug,
        "title": title,
        "type": ptype,
        "styleKernel": kernel if isinstance(kernel, dict) else None,
        "scaffoldPath": scaffold_path,
        "scenes": [],
    })
