"""harness/run.py — the single execution entrypoint (ILY-203 tasks 1-2).

Every model invocation and every ComfyUI render submission in this repository
goes through this module. In exchange, every invocation gets — structurally,
not procedurally:

* a computed ``agent_version_id`` (sha256 of prompt.md + tools.yaml +
  routing.yaml + model id; see harness/config_hash.py),
* credentials injected from the environment (agent config dirs never hold
  secrets),
* tool calls and responses recorded for offline champion/challenger replay,
* one JSONL trace row per invocation appended to
  ``projects/<project_id>/traces/traces.jsonl``.

Traces carry reasoning SUMMARIES only — never raw chain-of-thought.

The raw model SDK is importable only here (enforced by
harness/lint_no_raw_sdk.py as a pre-commit gate).
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.parse
import urllib.request
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from harness import config_hash as ch

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = REPO_ROOT / "agents"
POLICIES_ROUTING = REPO_ROOT / "policies" / "routing.yaml"

TRACE_SCHEMA_VERSION = "1.0.0"

# Rough $/MTok (input, output) for cost ESTIMATES on traces — not billing data.
_PRICES_PER_MTOK = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-8": (15.0, 75.0),
    "claude-fable-5": (15.0, 75.0),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_trace_id() -> str:
    return "tr_" + uuid.uuid4().hex


# --------------------------------------------------------------------------- #
# Routing policy (policies/routing.yaml — the tier ladder)
# --------------------------------------------------------------------------- #
def load_routing(path: str | Path = None) -> Dict[str, Any]:
    p = Path(path) if path else POLICIES_ROUTING
    if not p.exists():
        return {}
    import yaml
    return yaml.safe_load(p.read_text(encoding="utf-8-sig")) or {}


def routing_for(task_type: str, *, policy: Dict[str, Any] = None) -> Dict[str, Any]:
    """Resolve a task_type against the tier ladder. Returns
    {tier, model|engine, ...tier fields...}; empty dict if unmapped."""
    pol = policy if policy is not None else load_routing()
    for tier_name, tier in (pol.get("tiers") or {}).items():
        if task_type in (tier.get("task_types") or []):
            out = dict(tier)
            out["tier"] = tier_name
            out.pop("task_types", None)
            return out
    return {}


# --------------------------------------------------------------------------- #
# Agent resolution + version stamping
# --------------------------------------------------------------------------- #
def agent_dir(name: str, version: Optional[str] = None) -> Optional[Path]:
    base = AGENTS_DIR / name
    if not base.is_dir():
        return None
    if version:
        d = base / version
        return d if d.is_dir() else None
    versions = sorted([p for p in base.iterdir() if p.is_dir()], key=lambda p: p.name)
    return versions[-1] if versions else None


def stamp_agent(name: Optional[str], version: Optional[str], model: str) -> Dict[str, Any]:
    """Compute the agent identity block for a trace/provenance record."""
    if not name:
        return {"agent": None, "agent_version": None, "agent_version_id": None}
    d = agent_dir(name, version)
    if d is None:
        return {"agent": name, "agent_version": version, "agent_version_id": None}
    return {
        "agent": name,
        "agent_version": d.name,
        "agent_version_id": ch.agent_version_id(d, model or ch.default_model(d)),
    }


# --------------------------------------------------------------------------- #
# Credentials — environment only. Agent configs hold names, never values.
# --------------------------------------------------------------------------- #
def credential(env_name: str, *, required: bool = True) -> Optional[str]:
    val = os.getenv(env_name)
    if required and not val:
        raise RuntimeError(
            f"credential {env_name} not set in the environment "
            "(agent configs never hold secrets — export it and re-run)"
        )
    return val


# --------------------------------------------------------------------------- #
# Trace emission
# --------------------------------------------------------------------------- #
def resolve_project_dir(project_id: str) -> Path:
    """projects/<id>, else projects/<client>/<id>, else env override, else
    create projects/<id>. Trace dirs are created on demand."""
    override = os.getenv("ILYRIUM_PROJECT_DIR")
    if override:
        return Path(override)
    direct = REPO_ROOT / "projects" / project_id
    if direct.is_dir():
        return direct
    projects = REPO_ROOT / "projects"
    if projects.is_dir():
        for client in projects.iterdir():
            cand = client / project_id
            if cand.is_dir():
                return cand
    return direct  # created on first emit


REQUIRED_TRACE_FIELDS = (
    "trace_id", "ts", "agent_version_id", "task_type", "shot_id", "model",
    "tier", "tokens", "estimated_cost_usd", "latency_s", "retries",
    "replayable", "reasoning_summary",
)


def emit_trace(project_id: str, row: Dict[str, Any], *,
               project_dir: str | Path = None) -> Path:
    """Append one JSONL trace row to projects/<project_id>/traces/traces.jsonl.

    Fills defaults so every row carries the full required field set."""
    base = Path(project_dir) if project_dir else resolve_project_dir(project_id)
    traces = base / "traces"
    traces.mkdir(parents=True, exist_ok=True)
    full = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "trace_id": new_trace_id(),
        "ts": now_iso(),
        "project_id": project_id,
        "domain": "studio",
        "agent": None, "agent_version": None, "agent_version_id": None,
        "task_type": None, "song_id": None, "shot_id": None,
        "model": None, "tier": None,
        "tokens": {"input": None, "output": None},
        "estimated_cost_usd": None,
        "latency_s": None, "retries": 0, "replayable": False,
        "reasoning_summary": "",
        "status": "ok", "error": None,
        "tool_calls": [],
    }
    full.update(row)
    path = traces / "traces.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(full, ensure_ascii=False, default=str) + "\n")
    return path


def estimate_cost(model: Optional[str], tokens_in: Optional[int],
                  tokens_out: Optional[int], flat: Optional[float] = None) -> Optional[float]:
    if flat is not None:
        return round(float(flat), 6)
    if not model or tokens_in is None:
        return None
    for prefix, (pi, po) in _PRICES_PER_MTOK.items():
        if model.startswith(prefix):
            return round((tokens_in * pi + (tokens_out or 0) * po) / 1_000_000, 6)
    return None


# --------------------------------------------------------------------------- #
# Invocation recording (tool calls + responses, for replay)
# --------------------------------------------------------------------------- #
class Invocation:
    def __init__(self, **fields):
        self.fields: Dict[str, Any] = fields
        self.tool_calls: List[Dict[str, Any]] = []
        self.retries = 0

    def record_tool_call(self, tool: str, request: Any, response: Any) -> None:
        self.tool_calls.append({
            "tool": tool, "ts": now_iso(),
            "request": request, "recorded_response": response,
        })

    def set(self, **fields) -> None:
        self.fields.update(fields)


_active = threading.local()


def _current_invocation() -> Optional[Invocation]:
    return getattr(_active, "inv", None)


@contextmanager
def invocation(*, project_id: str, task_type: str, agent: Optional[str] = None,
               agent_version: Optional[str] = None, model: Optional[str] = None,
               song_id: Optional[str] = None, shot_id: Optional[str] = None,
               tier: Optional[str] = None, replayable: bool = True,
               reasoning_summary: str = "", project_dir: str | Path = None):
    """Trace one unit of work. HTTP/model calls made inside the block through
    this module are recorded onto the trace for offline replay."""
    route = routing_for(task_type)
    model = model or route.get("model") or route.get("engine")
    tier = tier or route.get("tier")
    inv = Invocation(
        **stamp_agent(agent, agent_version, model or ""),
        task_type=task_type, song_id=song_id, shot_id=shot_id,
        model=model, tier=tier, replayable=replayable,
        reasoning_summary=reasoning_summary,
    )
    prev = _current_invocation()
    _active.inv = inv
    t0 = time.time()
    try:
        yield inv
        inv.fields.setdefault("status", "ok")
    except Exception as exc:
        inv.fields["status"] = "error"
        inv.fields["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        _active.inv = prev
        inv.fields["latency_s"] = round(time.time() - t0, 3)
        inv.fields["retries"] = inv.retries
        inv.fields["tool_calls"] = inv.tool_calls
        if inv.fields.get("estimated_cost_usd") is None:
            inv.fields["estimated_cost_usd"] = estimate_cost(
                model, None, None, flat=route.get("estimated_cost_usd"))
        emit_trace(project_id, inv.fields, project_dir=project_dir)


# --------------------------------------------------------------------------- #
# HTTP transport — the only sanctioned path to the ComfyUI API
# --------------------------------------------------------------------------- #
def http_get_json(url: str, *, timeout: float = 30.0) -> Dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        data = json.loads(r.read())
    inv = _current_invocation()
    if inv is not None:
        inv.record_tool_call("http_get", {"url": url}, data)
    return data


def http_get_bytes(url: str, *, timeout: float = 120.0) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        data = r.read()
    inv = _current_invocation()
    if inv is not None:
        import hashlib
        inv.record_tool_call("http_get_bytes", {"url": url},
                             {"bytes": len(data),
                              "sha256": hashlib.sha256(data).hexdigest()})
    return data


def http_post_json(url: str, payload: Dict[str, Any], *, timeout: float = 60.0) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    inv = _current_invocation()
    if inv is not None:
        inv.record_tool_call("http_post", {"url": url, "payload": payload}, data)
    return data


def comfy_submit_prompt(comfy_url: str, graph: Dict[str, Any],
                        client_id: Optional[str] = None) -> str:
    """POST a workflow graph to ComfyUI /prompt; returns the prompt_id."""
    client_id = client_id or uuid.uuid4().hex
    resp = http_post_json(f"{comfy_url.rstrip('/')}/prompt",
                          {"prompt": graph, "client_id": client_id})
    return resp["prompt_id"]


def comfy_history(comfy_url: str, prompt_id: str) -> Dict[str, Any]:
    return http_get_json(f"{comfy_url.rstrip('/')}/history/{prompt_id}")


def comfy_system_stats(comfy_url: str) -> Dict[str, Any]:
    try:
        return http_get_json(f"{comfy_url.rstrip('/')}/system_stats")
    except Exception:
        return {}


def comfy_view(comfy_url: str, filename: str, subfolder: str = "",
               type_: str = "output") -> bytes:
    q = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": type_})
    return http_get_bytes(f"{comfy_url.rstrip('/')}/view?{q}")


def comfy_upload_image(comfy_url: str, local_path: str) -> Dict[str, Any]:
    """Multipart upload of a keyframe into ComfyUI/input."""
    import io
    import mimetypes
    fname = os.path.basename(local_path)
    boundary = uuid.uuid4().hex
    body = io.BytesIO()

    def w(s):
        body.write(s if isinstance(s, bytes) else s.encode("utf-8"))

    w(f"--{boundary}\r\n")
    w(f'Content-Disposition: form-data; name="image"; filename="{fname}"\r\n')
    w(f"Content-Type: {mimetypes.guess_type(fname)[0] or 'application/octet-stream'}\r\n\r\n")
    with open(local_path, "rb") as fh:
        w(fh.read())
    w("\r\n")
    w(f"--{boundary}\r\n")
    w('Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n')
    w(f"--{boundary}--\r\n")
    req = urllib.request.Request(
        f"{comfy_url.rstrip('/')}/upload/image", data=body.getvalue(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
    inv = _current_invocation()
    if inv is not None:
        inv.record_tool_call("comfy_upload_image",
                             {"url": comfy_url, "filename": fname}, data)
    return data


# --------------------------------------------------------------------------- #
# Model execution — the ONLY raw-SDK call site in the repository
# --------------------------------------------------------------------------- #
def run_model(*, agent: str, task_type: str, messages: List[Dict[str, Any]],
              project_id: str, system: Optional[str] = None,
              tools: Optional[List[Dict[str, Any]]] = None,
              model: Optional[str] = None, agent_version: Optional[str] = None,
              max_tokens: int = 3000, song_id: Optional[str] = None,
              shot_id: Optional[str] = None, reasoning_summary: str = "",
              project_dir: str | Path = None):
    """One traced Anthropic messages.create call. Returns the SDK response.

    Model resolution order: explicit arg > agent routing.yaml > policies tier
    ladder for task_type. The API key is injected from the environment here
    and nowhere else.
    """
    import anthropic  # raw SDK: importable ONLY inside harness/

    route = routing_for(task_type)
    d = agent_dir(agent, agent_version)
    if model is None and d is not None:
        model = ch.default_model(d) or None
    model = model or route.get("model")
    if not model:
        raise RuntimeError(
            f"no model resolved for agent={agent!r} task_type={task_type!r} "
            "(set model: in the agent routing.yaml or map the task_type in "
            "policies/routing.yaml)")

    client = anthropic.Anthropic(api_key=credential("ANTHROPIC_API_KEY"))

    with invocation(project_id=project_id, task_type=task_type, agent=agent,
                    agent_version=agent_version, model=model, song_id=song_id,
                    shot_id=shot_id, replayable=True,
                    reasoning_summary=reasoning_summary,
                    project_dir=project_dir) as inv:
        kwargs: Dict[str, Any] = dict(model=model, max_tokens=max_tokens, messages=messages)
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools
        resp = client.messages.create(**kwargs)

        usage = getattr(resp, "usage", None)
        tokens_in = getattr(usage, "input_tokens", None)
        tokens_out = getattr(usage, "output_tokens", None)
        text = "".join(b.text for b in resp.content
                       if getattr(b, "type", None) == "text")
        tool_uses = [{"name": b.name, "input": b.input}
                     for b in resp.content if getattr(b, "type", None) == "tool_use"]
        inv.record_tool_call(
            "anthropic.messages.create",
            {"model": model, "max_tokens": max_tokens,
             "system_sha256": _sha256_text(system or ""),
             "n_messages": len(messages),
             "tools": [t.get("name") for t in (tools or [])]},
            {"stop_reason": resp.stop_reason, "text": text[:20000],
             "tool_uses": tool_uses})
        inv.set(tokens={"input": tokens_in, "output": tokens_out},
                estimated_cost_usd=estimate_cost(model, tokens_in, tokens_out))
        return resp


def _sha256_text(s: str) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()
