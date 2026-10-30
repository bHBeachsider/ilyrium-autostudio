"""A3 (TDD): cut ledger record written by assemble_cut(engine="filmcraft").

Tests that:
 - calling assemble_cut with engine="filmcraft" (binary mocked) appends exactly one
   {"event": "cut"} record to ilyrium-shots/ledger/<campaign_id>.jsonl
 - chain_ok() returns True after the append
 - script_sha256 is present and non-null in the record

No FILMCRAFT_CLI required; all binary calls are monkeypatched.
"""
import json
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = REPO_ROOT / "apps" / "auto-studio"
for _p in (str(REPO_ROOT), str(APP_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# --- project_store stub (project_store is not importable without the full env) ---
_ps_stub = types.ModuleType("project_store")


def _ps_selected_media(project):
    out = []
    for shot in project.get("shots", []):
        sel = shot.get("selected_take")
        take = next((t for t in shot.get("takes", []) if t["take_id"] == sel), None)
        if take and take.get("video"):
            out.append(take)
    return out


def _ps_next_cut_id(project):
    n = len(project.get("cuts", [])) + 1
    return f"cut_{n}"


def _ps_add_cut(project, output, public_url=None):
    cut_id = _ps_next_cut_id(project)
    project.setdefault("cuts", []).append({
        "cut_id": cut_id, "output": output, "public_url": public_url,
    })
    return cut_id


def _ps_save_project(project_dir, project):
    path = Path(project_dir) / "project.json"
    path.write_text(json.dumps(project, default=str), encoding="utf-8")


def _ps_latest_cut(project):
    cuts = project.get("cuts", [])
    return cuts[-1] if cuts else None


_ps_stub.selected_media = _ps_selected_media
_ps_stub._next_cut_id = _ps_next_cut_id
_ps_stub.add_cut = _ps_add_cut
_ps_stub.save_project = _ps_save_project
_ps_stub.latest_cut = _ps_latest_cut
sys.modules.setdefault("project_store", _ps_stub)

# Now that the stub is in place, we can safely import producer.
import producer                            # noqa: E402
import cut_ledger                          # noqa: E402
from media import filmcraft_assembler as fa  # noqa: E402
import qc                                  # noqa: E402


def _fake_project(proj_dir: Path) -> dict:
    video_path = proj_dir / "take_1.mp4"
    video_path.write_bytes(b"fake")
    return {
        "campaign_id": "ledger_test",
        "cuts": [],
        "shots": [{
            "scene_number": 1,
            "visual_prompt": "test shot",
            "selected_take": "take_1",
            "takes": [{"take_id": "take_1", "video": str(video_path), "audio": None}],
        }],
    }


def _mock_assemble(cut_dir: Path):
    def _assemble(project, project_dir, cut_id, kernel=None):
        cut_dir.mkdir(parents=True, exist_ok=True)
        return {
            "cut_dir": str(cut_dir),
            "total_frames": 24,
            "loudness_lufs": -14.0,
            "script_sha256": "deadbeef01234567deadbeef01234567deadbeef01234567deadbeef01234567",
            "sequence_sha256": "cafebabe" * 8,
            "filmcraft_version": "filmcraft-cli 0.7.0-test",
            "fcproj": str(cut_dir / f"{cut_id}.fcproj"),
        }
    return _assemble


def _mock_export(cut_dir: Path):
    master = cut_dir / "master.mp4"

    def _export(cut_dir_arg, preset="master"):
        Path(cut_dir_arg).mkdir(parents=True, exist_ok=True)
        p = Path(cut_dir_arg) / "master.mp4"
        p.write_bytes(b"fake_master")
        return {"path": str(p), "sha256": "exportsha" + "x" * 55}

    return _export


def test_ledger_cut_record_appended(tmp_path, monkeypatch):
    ledger_dir = tmp_path / "ledger"
    monkeypatch.setenv("LEDGER_DIR", str(ledger_dir))

    proj_dir = tmp_path / "campaign"
    proj_dir.mkdir()
    cut_dir = proj_dir / "cuts" / "cut_1"

    project = _fake_project(proj_dir)

    monkeypatch.setattr(fa, "assemble", _mock_assemble(cut_dir))
    monkeypatch.setattr(fa, "export", _mock_export(cut_dir))
    monkeypatch.setattr(fa, "render_frames", lambda *a, **k: None)
    monkeypatch.setattr(fa, "interchange", lambda *a, **k: "cut_1.xml")
    monkeypatch.setattr(qc, "qc_clip", lambda *a, **k: {"ok": True, "flags": []})

    res = producer.assemble_cut(project, str(proj_dir), engine="filmcraft", upload_to_r2=False)

    assert res["cut_id"] == "cut_1"

    ledger_file = ledger_dir / "ledger_test.jsonl"
    assert ledger_file.exists(), "ledger file was not created"
    lines = [ln for ln in ledger_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1, f"expected 1 record, got {len(lines)}"

    record = json.loads(lines[0])
    assert record["event"] == "cut"
    assert record["cut_id"] == "cut_1"
    assert record["engine"] == "filmcraft"
    assert record["script_sha256"], "script_sha256 must be present and non-null"
    assert record["chain_hash"], "chain_hash must be present"
    assert record["prev_chain_hash"] is None  # first record has no predecessor

    assert cut_ledger.chain_ok("ledger_test", str(ledger_dir)), "chain_ok failed after append"


def test_ledger_chain_grows_and_verifies(tmp_path, monkeypatch):
    """Two successive cuts produce a two-record chain that still verifies."""
    ledger_dir = tmp_path / "ledger"
    monkeypatch.setenv("LEDGER_DIR", str(ledger_dir))

    proj_dir = tmp_path / "campaign"
    proj_dir.mkdir()

    project = _fake_project(proj_dir)
    call_n = {"n": 0}

    def fake_assemble(p, project_dir, cut_id, kernel=None):
        call_n["n"] += 1
        d = Path(project_dir) / "cuts" / cut_id
        d.mkdir(parents=True, exist_ok=True)
        return {
            "cut_dir": str(d), "total_frames": 24, "loudness_lufs": -14.0,
            "script_sha256": f"script{call_n['n']:064x}",
            "sequence_sha256": "seq" * 21 + "x",
            "filmcraft_version": "filmcraft-cli 0.7.0-test",
            "fcproj": str(d / f"{cut_id}.fcproj"),
        }

    def fake_export(cut_dir_arg, preset="master"):
        p = Path(cut_dir_arg) / "master.mp4"
        p.write_bytes(b"x")
        return {"path": str(p), "sha256": "expsha_" + "y" * 57}

    monkeypatch.setattr(fa, "assemble", fake_assemble)
    monkeypatch.setattr(fa, "export", fake_export)
    monkeypatch.setattr(fa, "render_frames", lambda *a, **k: None)
    monkeypatch.setattr(fa, "interchange", lambda *a, **k: "cut.xml")
    monkeypatch.setattr(qc, "qc_clip", lambda *a, **k: {"ok": True, "flags": []})

    producer.assemble_cut(project, str(proj_dir), engine="filmcraft", upload_to_r2=False)
    producer.assemble_cut(project, str(proj_dir), engine="filmcraft", upload_to_r2=False)

    ledger_file = ledger_dir / "ledger_test.jsonl"
    lines = [ln for ln in ledger_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2

    r1, r2 = [json.loads(l) for l in lines]
    assert r2["prev_chain_hash"] == r1["chain_hash"]
    assert cut_ledger.chain_ok("ledger_test", str(ledger_dir))


def test_chain_ok_detects_tampering(tmp_path):
    """Directly tampering with a record breaks chain_ok."""
    ledger_dir = str(tmp_path / "ledger")
    cut_ledger.append_cut_record("tamper", {
        "event": "cut", "cut_id": "cut_1", "engine": "filmcraft",
        "script_sha256": "abc", "export_sha256": "def",
        "filmcraft_version": "0.7.0", "published": False, "public_url": None, "qa_passed": True,
    }, ledger_dir=ledger_dir)

    path = Path(ledger_dir) / "tamper.jsonl"
    content = path.read_text(encoding="utf-8")
    tampered = content.replace('"published": false', '"published": true')
    path.write_text(tampered, encoding="utf-8")

    assert not cut_ledger.chain_ok("tamper", ledger_dir=ledger_dir)
