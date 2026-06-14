"""Deterministic agent-config hashing + manifest writer (ILY-203 task 7).

An agent version is a directory of config files — agents/<name>/<version>/ —
and its identity is computed, never asserted:

* ``agent_version_id`` = sha256 over prompt.md + tools.yaml + routing.yaml +
  the model identifier (the spec-mandated formula). This is the id stamped on
  every trace and every provenance record.
* ``config_hash``      = sha256 over EVERY config file in the version dir
  (manifest.json excluded), used by the admission gate to detect drift between
  the manifest and the directory contents.

Hashed bytes are canonicalised: UTF-8 BOM stripped, CRLF normalised to LF —
so the same config hashes identically regardless of the OS or editor that
wrote it (BOM corruption is a seeded failure class in FINDINGS.md).

Credentials never appear in agent config dirs; the manifest records names and
hashes only.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# The spec formula inputs, in fixed order.
VERSION_ID_FILES = ("prompt.md", "tools.yaml", "routing.yaml")
# Everything that may define behaviour; config_hash covers whatever subset exists.
CONFIG_FILES = ("prompt.md", "tools.yaml", "routing.yaml", "permissions.yaml", "validation.yaml")
MANIFEST_NAME = "manifest.json"


def canonical_file_bytes(path: Path) -> bytes:
    """File bytes with UTF-8 BOM stripped and CRLF -> LF. Missing file -> b''."""
    if not path.exists():
        return b""
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return data.replace(b"\r\n", b"\n")


def agent_version_id(agent_dir: str | Path, model_id: str) -> str:
    """sha256(prompt.md + tools.yaml + routing.yaml + model id), per ILY-203."""
    d = Path(agent_dir)
    h = hashlib.sha256()
    for name in VERSION_ID_FILES:
        h.update(name.encode("utf-8") + b"\x00")
        h.update(canonical_file_bytes(d / name) + b"\x00")
    h.update((model_id or "").encode("utf-8"))
    return "sha256:" + h.hexdigest()


def config_hash(agent_dir: str | Path) -> str:
    """sha256 over every present config file (sorted, manifest excluded)."""
    d = Path(agent_dir)
    h = hashlib.sha256()
    for name in sorted(CONFIG_FILES):
        p = d / name
        if p.exists():
            h.update(name.encode("utf-8") + b"\x00")
            h.update(canonical_file_bytes(p) + b"\x00")
    return "sha256:" + h.hexdigest()


def file_digests(agent_dir: str | Path) -> Dict[str, str]:
    d = Path(agent_dir)
    out = {}
    for name in sorted(CONFIG_FILES):
        p = d / name
        if p.exists():
            out[name] = "sha256:" + hashlib.sha256(canonical_file_bytes(p)).hexdigest()
    return out


def default_model(agent_dir: str | Path) -> str:
    """The model id the version-id formula uses: the agent routing.yaml's
    ``model:`` if set, else the policies ladder entry for its ``task_type:``."""
    d = Path(agent_dir)
    routing = _load_yaml(d / "routing.yaml")
    if routing.get("model"):
        return str(routing["model"])
    task_type = routing.get("task_type")
    if task_type:
        pol = _load_yaml(_repo_root() / "policies" / "routing.yaml")
        for tier in (pol.get("tiers") or {}).values():
            if task_type in (tier.get("task_types") or []):
                return str(tier.get("model") or tier.get("engine") or "")
    return ""


def write_manifest(
    agent_dir: str | Path,
    *,
    parent_version: Optional[str] = None,
    rubric: str = "evals/rubrics/studio_rubric.yaml",
    golden_set: Optional[str] = None,
) -> Dict[str, Any]:
    """Record name, version, hash, and parent version into manifest.json."""
    d = Path(agent_dir).resolve()
    name, version = d.parent.name, d.name
    model = default_model(d)
    manifest = {
        "agent": name,
        "version": version,
        "parent_version": parent_version,
        "model": model,
        "agent_version_id": agent_version_id(d, model),
        "config_hash": config_hash(d),
        "files": file_digests(d),
        "rubric": rubric,
        "golden_set": golden_set or f"evals/golden/{name}",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (d / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def read_manifest(agent_dir: str | Path) -> Optional[Dict[str, Any]]:
    p = Path(agent_dir) / MANIFEST_NAME
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8-sig"))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
    except Exception:
        return {}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Hash an agent config dir / write its manifest")
    ap.add_argument("agent_dir", help="agents/<name>/<version> directory")
    ap.add_argument("--write-manifest", action="store_true")
    ap.add_argument("--parent", default=None, help="parent version, e.g. v1")
    ap.add_argument("--golden-set", default=None)
    a = ap.parse_args(argv)
    d = Path(a.agent_dir)
    if not d.is_dir():
        print(f"not a directory: {d}", file=sys.stderr)
        return 2
    if a.write_manifest:
        m = write_manifest(d, parent_version=a.parent, golden_set=a.golden_set)
        print(json.dumps(m, indent=2))
    else:
        model = default_model(d)
        print(json.dumps({
            "agent_version_id": agent_version_id(d, model),
            "config_hash": config_hash(d),
            "model": model,
        }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
