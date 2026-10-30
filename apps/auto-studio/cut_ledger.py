"""Append-only cut ledger for assembled cuts (Phase 2).

Each record describes one assembled cut and chains to the previous via SHA-256:
    chain_hash = sha256(prev_chain_hash + json.dumps(record_without_chain_hash, sort_keys=True))

where `prev_chain_hash` is "" for the first record.

File location: <repo_root>/ilyrium-shots/ledger/<campaign_id>.jsonl
Override with the LEDGER_DIR env var (for tests / CI).

Invariants:
- Records are append-only. Never rewrite, reorder, or remove entries.
- chain_ok() must return True after every write.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _default_ledger_dir() -> Path:
    if os.environ.get("LEDGER_DIR"):
        return Path(os.environ["LEDGER_DIR"])
    return Path(__file__).resolve().parents[2] / "ilyrium-shots" / "ledger"


def _ledger_path(campaign_id: str, ledger_dir=None) -> Path:
    d = Path(ledger_dir) if ledger_dir else _default_ledger_dir()
    return d / f"{campaign_id}.jsonl"


def _hash_record(record_without_chain_hash: dict, prev_chain_hash: str) -> str:
    body = json.dumps(record_without_chain_hash, sort_keys=True)
    return hashlib.sha256((prev_chain_hash + body).encode("utf-8")).hexdigest()


def append_cut_record(campaign_id: str, fields: dict, ledger_dir=None) -> dict:
    """Append one cut record; returns the full record (including chain_hash)."""
    path = _ledger_path(campaign_id, ledger_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    prev_chain_hash = ""
    if path.exists():
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if lines:
            last = json.loads(lines[-1])
            prev_chain_hash = last.get("chain_hash", "")

    record = {
        "event": fields.get("event", "cut"),
        "cut_id": fields.get("cut_id"),
        "engine": fields.get("engine"),
        "script_sha256": fields.get("script_sha256"),
        "export_sha256": fields.get("export_sha256"),
        "filmcraft_version": fields.get("filmcraft_version"),
        "published": bool(fields.get("published", False)),
        "public_url": fields.get("public_url"),
        "qa_passed": bool(fields.get("qa_passed", False)),
        "ts": fields.get("ts") or datetime.now(timezone.utc).isoformat(),
        "prev_chain_hash": prev_chain_hash or None,
    }
    chain_hash = _hash_record(record, prev_chain_hash)
    record["chain_hash"] = chain_hash

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")

    return record


def chain_ok(campaign_id: str, ledger_dir=None) -> bool:
    """Verify the full chain. Returns True if intact (or no file), False if tampered."""
    path = _ledger_path(campaign_id, ledger_dir)
    if not path.exists():
        return True
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return True

    prev_hash = ""
    for line in lines:
        record = json.loads(line)
        stored_hash = record.get("chain_hash", "")
        stored_prev = record.get("prev_chain_hash")

        if (stored_prev or "") != prev_hash:
            return False

        record_no_hash = {k: v for k, v in record.items() if k != "chain_hash"}
        expected = _hash_record(record_no_hash, prev_hash)
        if stored_hash != expected:
            return False

        prev_hash = stored_hash

    return True
