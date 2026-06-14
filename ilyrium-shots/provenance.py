"""Ilyrium Stage 8 provenance registry.

A dependency-light (stdlib-only; optional `jsonschema`) ledger for film-shot
renders. One ledger file per song -- ``ledger/<song_id>.jsonl`` -- append-only,
hash-chained. A record is a full snapshot of one render attempt; every state
change appends a new snapshot line, so the current state of a record is simply
its most recent line.

Hashing
-------
* ``content_hash``  -- sha256 of canonical-JSON of {shot_spec, generation,
  models, engine}. The reproducibility fingerprint / dedupe key. Excludes
  lifecycle fields by construction.
* ``chain.record_hash`` -- sha256(prev_record_hash + snapshot_hash) where
  ``snapshot_hash`` is the digest of the whole record minus its ``chain`` field.
  This attests the entire snapshot (including status/approval), so any tampering
  with a past line breaks the chain from that point forward.

Canonical JSON (must match every writer, in any language):
    json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    encoded as UTF-8, then sha256, prefixed "sha256:".
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

SCHEMA_VERSION = "1.0.0"

# Fields that determine reproducibility (the content_hash domain).
_CONTENT_KEYS = ("shot_spec", "generation", "models", "engine")


# --------------------------------------------------------------------------- #
# Canonicalisation + hashing
# --------------------------------------------------------------------------- #
def canonical_bytes(obj: Any) -> bytes:
    """Deterministic UTF-8 serialisation used for every hash."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def digest(obj: Any) -> str:
    """sha256 of an object's canonical JSON, as 'sha256:<hex>'."""
    return "sha256:" + hashlib.sha256(canonical_bytes(obj)).hexdigest()


def digest_str(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def file_sha256(path: str | os.PathLike, *, chunk: int = 1 << 20) -> str:
    """Bare hex sha256 of a file's bytes (used for models / outputs / keyframes)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def content_hash(record: Dict[str, Any]) -> str:
    """Reproducibility fingerprint over {shot_spec, generation, models, engine}."""
    return digest({k: record[k] for k in _CONTENT_KEYS})


def snapshot_hash(record: Dict[str, Any]) -> str:
    """Digest of the full record minus its 'chain' field."""
    core = {k: v for k, v in record.items() if k != "chain"}
    return digest(core)


def link(prev_record_hash: Optional[str], record: Dict[str, Any]) -> str:
    """record_hash = sha256(prev_record_hash + snapshot_hash(record))."""
    return digest_str((prev_record_hash or "") + snapshot_hash(record))


# --------------------------------------------------------------------------- #
# ULID (Crockford base32, 26 chars, monotonic by time prefix)
# --------------------------------------------------------------------------- #
_CROCK = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford: no I L O U


def new_ulid(ts_ms: Optional[int] = None) -> str:
    ts = int(time.time() * 1000) if ts_ms is None else ts_ms
    value = (ts << 80) | int.from_bytes(os.urandom(10), "big")  # 48-bit time + 80-bit rand
    out = []
    for _ in range(26):
        out.append(_CROCK[value & 0x1F])
        value >>= 5
    return "".join(reversed(out))


def now_iso() -> str:
    """UTC, second precision, 'Z'-suffixed -- matches the schema's date-time."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# Optional schema validation (best-effort; resolves the sibling shot_spec ref)
# --------------------------------------------------------------------------- #
def _load_validator(schema_path: str | os.PathLike):
    """Return a callable(record)->errors, or None if jsonschema is unavailable."""
    try:
        import jsonschema
        from jsonschema import Draft7Validator
        from referencing import Registry, Resource  # type: ignore
        from referencing.jsonschema import DRAFT7  # type: ignore
    except Exception:
        try:
            import jsonschema  # noqa: F401
            from jsonschema import Draft7Validator, RefResolver  # type: ignore
        except Exception:
            return None
        # Older jsonschema path (RefResolver).
        schema_path = Path(schema_path)
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        base = schema_path.resolve().parent.as_uri() + "/"
        resolver = RefResolver(base_uri=base, referrer=schema)
        validator = Draft7Validator(schema, resolver=resolver)
        return lambda rec: sorted(validator.iter_errors(rec), key=lambda e: list(e.path))

    # Newer jsonschema path (referencing registry).
    from urllib.parse import urljoin

    schema_path = Path(schema_path)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    base_id = schema.get("$id") or schema_path.resolve().as_uri()
    registry = Registry()
    sibling = schema_path.resolve().parent / "shot_spec.schema.json"
    if sibling.exists():
        ref_doc = json.loads(sibling.read_text(encoding="utf-8"))
        ref_uri = urljoin(base_id, "shot_spec.schema.json")
        registry = registry.with_resource(
            ref_uri, Resource.from_contents(ref_doc, default_specification=DRAFT7)
        )
    validator = Draft7Validator(schema, registry=registry)
    return lambda rec: sorted(validator.iter_errors(rec), key=lambda e: list(e.path))


# --------------------------------------------------------------------------- #
# Record construction
# --------------------------------------------------------------------------- #
def new_record(
    *,
    shot: Dict[str, Any],
    shot_spec: Dict[str, Any],
    generation: Dict[str, Any],
    models: List[Dict[str, Any]],
    engine: Dict[str, Any],
    attempt: int = 1,
    supersedes: Optional[str] = None,
    status: str = "queued",
    agent_version_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a fresh, queued provenance record. Models are sorted for a stable hash."""
    models = sorted(models, key=lambda m: (m["role"], m["filename"]))
    ts = now_iso()
    record: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_id": new_ulid(),
        "created_at": ts,
        "updated_at": ts,
        "status": status,
        "attempt": attempt,
        "supersedes": supersedes,
        "shot": shot,
        "shot_spec": shot_spec,
        "shot_spec_hash": digest(shot_spec),
        "generation": generation,
        "models": models,
        "engine": engine,
        "render": None,
        "approval": {"state": "pending", "reviewer": None, "decided_at": None, "note": None},
        # RSI L0 (ILY-203): agent config identity, stamped by the harness. Inside
        # the chained snapshot so verify_chain attests agent identity; outside
        # _CONTENT_KEYS so content_hash dedupe semantics are unchanged.
        "agent_version_id": agent_version_id,
    }
    record["content_hash"] = content_hash(record)
    return record


# --------------------------------------------------------------------------- #
# Ledger
# --------------------------------------------------------------------------- #
class Ledger:
    """Append-only, hash-chained JSONL ledger, one file per song."""

    def __init__(
        self,
        ledger_dir: str | os.PathLike = "ledger",
        *,
        schema_path: Optional[str | os.PathLike] = "provenance_record.schema.json",
        validate: bool = True,
    ):
        self.dir = Path(ledger_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._validate = None
        if validate and schema_path and Path(schema_path).exists():
            self._validate = _load_validator(schema_path)

    # --- paths / io ------------------------------------------------------- #
    def path_for(self, song_id: str) -> Path:
        return self.dir / f"{song_id}.jsonl"

    def read(self, song_id: str) -> List[Dict[str, Any]]:
        p = self.path_for(song_id)
        if not p.exists():
            return []
        out = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out

    def _last_record_hash(self, song_id: str) -> Optional[str]:
        records = self.read(song_id)
        if not records:
            return None
        return records[-1].get("chain", {}).get("record_hash")

    # --- writes ----------------------------------------------------------- #
    def append(self, song_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
        """Chain and append one snapshot. Returns the record with its chain set."""
        record = dict(record)
        # content_hash is frozen at creation; only compute it if missing.
        if "content_hash" not in record or record["content_hash"] is None:
            record["content_hash"] = content_hash(record)
        prev = self._last_record_hash(song_id)
        record["chain"] = {"prev_record_hash": prev, "record_hash": link(prev, record)}
        if self._validate is not None:
            errs = self._validate(record)
            if errs:
                raise ValueError(
                    "provenance record failed schema validation: "
                    + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:5])
                )
        with self.path_for(song_id).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def transition(
        self,
        song_id: str,
        record_id: str,
        *,
        status: Optional[str] = None,
        approval: Optional[Dict[str, Any]] = None,
        render: Optional[Dict[str, Any]] = None,
        generation_patch: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Append a new snapshot of an existing record with lifecycle fields patched.

        content_hash is preserved (generation_patch is for non-reproducibility
        fields populated at runtime, e.g. comfy_prompt_id).
        """
        latest = self.current_state(song_id).get(record_id)
        if latest is None:
            raise KeyError(f"{record_id} not found in {song_id}")
        snap = json.loads(json.dumps(latest))  # deep copy
        snap.pop("chain", None)
        snap["updated_at"] = now_iso()
        if status is not None:
            snap["status"] = status
        if approval is not None:
            snap["approval"] = approval
        if render is not None:
            snap["render"] = render
        if generation_patch:
            snap["generation"].update(generation_patch)
        return self.append(song_id, snap)

    # --- queries ---------------------------------------------------------- #
    def current_state(self, song_id: str) -> Dict[str, Dict[str, Any]]:
        """record_id -> latest snapshot (last line wins)."""
        state: Dict[str, Dict[str, Any]] = {}
        for rec in self.read(song_id):
            state[rec["record_id"]] = rec
        return state

    def find_by_content_hash(
        self,
        song_id: str,
        chash: str,
        *,
        statuses: Iterable[str] = ("rendered", "approved"),
    ) -> Optional[Dict[str, Any]]:
        statuses = set(statuses)
        for rec in self.current_state(song_id).values():
            if rec.get("content_hash") == chash and rec.get("status") in statuses:
                return rec
        return None

    def verify_chain(self, song_id: str) -> bool:
        """Recompute the chain end-to-end; True iff every link matches."""
        prev = None
        for rec in self.read(song_id):
            chain = rec.get("chain") or {}
            if chain.get("prev_record_hash") != prev:
                return False
            if chain.get("record_hash") != link(prev, rec):
                return False
            prev = chain.get("record_hash")
        return True


__all__ = [
    "SCHEMA_VERSION",
    "canonical_bytes", "digest", "digest_str", "file_sha256",
    "content_hash", "snapshot_hash", "link",
    "new_ulid", "now_iso", "new_record", "Ledger",
]
