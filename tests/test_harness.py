"""Tests for the RSI L0 harness (ILY-203 task 5).

Validates the four properties the harness must guarantee structurally:
  1. config-hash / agent_version_id stability across runs (and BOM-insensitivity),
  2. trace-row completeness (every required field present),
  3. credential non-leakage into agent config dirs,
  4. the lint gate detects a seeded raw-SDK import outside harness/.

This file deliberately constructs raw-SDK / direct-ComfyUI fixtures to exercise
the lint gate, so it opts out of that gate explicitly:
lint-no-raw-sdk: allow
"""

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness import config_hash as ch
from harness import lint_no_raw_sdk as lint
from harness import run as hrun


# --------------------------------------------------------------------------- #
# 1. config-hash stability
# --------------------------------------------------------------------------- #
def _write_agent(d: Path, *, prompt="be terse", model_in_routing=True):
    d.mkdir(parents=True, exist_ok=True)
    (d / "prompt.md").write_text(prompt, encoding="utf-8")
    (d / "tools.yaml").write_text("tools: []\n", encoding="utf-8")
    routing = "task_type: spec_draft\n"
    if model_in_routing:
        routing += "model: claude-sonnet-4-6\n"
    (d / "routing.yaml").write_text(routing, encoding="utf-8")
    (d / "permissions.yaml").write_text("read: [project]\nwrite: [stage]\n", encoding="utf-8")


def test_agent_version_id_stable_across_runs(tmp_path):
    d = tmp_path / "agents" / "demo" / "v1"
    _write_agent(d)
    a = ch.agent_version_id(d, "claude-sonnet-4-6")
    b = ch.agent_version_id(d, "claude-sonnet-4-6")
    assert a == b
    assert a.startswith("sha256:")


def test_agent_version_id_changes_with_model_and_prompt(tmp_path):
    d = tmp_path / "agents" / "demo" / "v1"
    _write_agent(d)
    base = ch.agent_version_id(d, "claude-sonnet-4-6")
    assert ch.agent_version_id(d, "claude-opus-4-8") != base
    (d / "prompt.md").write_text("be verbose", encoding="utf-8")
    assert ch.agent_version_id(d, "claude-sonnet-4-6") != base


def test_config_hash_bom_and_crlf_insensitive(tmp_path):
    d1 = tmp_path / "a" / "v1"
    d2 = tmp_path / "b" / "v1"
    _write_agent(d1)
    _write_agent(d2)
    # Rewrite d2's prompt with a UTF-8 BOM and CRLF line endings.
    (d2 / "prompt.md").write_bytes(b"\xef\xbb\xbfbe terse")
    (d2 / "tools.yaml").write_bytes(b"tools: []\r\n")
    assert ch.config_hash(d1) == ch.config_hash(d2)
    assert ch.agent_version_id(d1, "m") == ch.agent_version_id(d2, "m")


def test_manifest_records_identity_and_parent(tmp_path):
    d = tmp_path / "agents" / "demo" / "v2"
    _write_agent(d)
    m = ch.write_manifest(d, parent_version="v1")
    assert m["agent"] == "demo" and m["version"] == "v2"
    assert m["parent_version"] == "v1"
    assert m["agent_version_id"].startswith("sha256:")
    reloaded = ch.read_manifest(d)
    assert reloaded["config_hash"] == m["config_hash"]


# --------------------------------------------------------------------------- #
# 2. trace-row completeness
# --------------------------------------------------------------------------- #
def test_emit_trace_has_all_required_fields(tmp_path):
    path = hrun.emit_trace(
        "NH-S03",
        {"task_type": "video_render", "shot_id": "NH-S03-SH012",
         "model": "comfyui/wan2.2-i2v", "tier": "T4",
         "agent_version_id": "sha256:" + "a" * 64,
         "tokens": {"input": 10, "output": 5}, "estimated_cost_usd": 0.0,
         "latency_s": 1.2, "retries": 0, "replayable": True,
         "reasoning_summary": "ok"},
        project_dir=tmp_path)
    row = json.loads(path.read_text(encoding="utf-8").strip())
    for field in hrun.REQUIRED_TRACE_FIELDS:
        assert field in row, f"missing trace field: {field}"
    assert row["replayable"] is True
    assert row["shot_id"] == "NH-S03-SH012"


def test_invocation_emits_one_row_with_tool_calls(tmp_path):
    with hrun.invocation(project_id="NH-S03", project_dir=tmp_path,
                         task_type="video_render", agent="shot_renderer",
                         model="comfyui/wan2.2-i2v", song_id="NH-S03",
                         shot_id="NH-S03-SH012",
                         reasoning_summary="render") as inv:
        inv.record_tool_call("renderer", {"shot": 1}, {"prompt_id": "p1"})
    rows = (tmp_path / "traces" / "traces.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1
    row = json.loads(rows[0])
    assert row["status"] == "ok"
    assert row["latency_s"] is not None
    assert len(row["tool_calls"]) == 1
    assert row["tool_calls"][0]["recorded_response"] == {"prompt_id": "p1"}


def test_invocation_records_error_status(tmp_path):
    with pytest.raises(ValueError):
        with hrun.invocation(project_id="NH-S03", project_dir=tmp_path,
                             task_type="video_render", agent="shot_renderer",
                             model="m", reasoning_summary="boom"):
            raise ValueError("boom")
    row = json.loads((tmp_path / "traces" / "traces.jsonl").read_text(encoding="utf-8").strip())
    assert row["status"] == "error"
    assert "boom" in row["error"]


# --------------------------------------------------------------------------- #
# 3. credential non-leakage
# --------------------------------------------------------------------------- #
def test_credentials_absent_from_agent_configs():
    """No file under agents/ may contain a secret-looking assignment."""
    agents_dir = REPO_ROOT / "agents"
    if not agents_dir.is_dir():
        pytest.skip("agents/ not scaffolded yet")
    banned = ("API_KEY=", "api_key:", "sk-ant-", "secret:", "token:")
    for cfg in agents_dir.rglob("*.*"):
        if cfg.suffix.lower() not in (".md", ".yaml", ".yml", ".json"):
            continue
        text = cfg.read_text(encoding="utf-8-sig", errors="replace").lower()
        for b in banned:
            assert b.lower() not in text, f"possible secret in {cfg}: {b}"


def test_credential_reads_from_env(monkeypatch):
    monkeypatch.setenv("ILYRIUM_TEST_CRED", "value-from-env")
    assert hrun.credential("ILYRIUM_TEST_CRED") == "value-from-env"
    monkeypatch.delenv("ILYRIUM_TEST_CRED", raising=False)
    with pytest.raises(RuntimeError):
        hrun.credential("ILYRIUM_TEST_CRED")


# --------------------------------------------------------------------------- #
# 4. lint gate detection
# --------------------------------------------------------------------------- #
def test_lint_detects_seeded_raw_sdk_import(tmp_path):
    bad = tmp_path / "rogue_agent.py"
    bad.write_text("import anthropic\nclient = anthropic.Anthropic()\n", encoding="utf-8")
    assert lint.check_file(bad), "raw anthropic import should be flagged"


def test_lint_detects_direct_comfy_post(tmp_path):
    bad = tmp_path / "rogue_render.py"
    bad.write_text(
        "import urllib.request, json\n"
        "urllib.request.urlopen('http://x/prompt')\n", encoding="utf-8")
    assert lint.check_file(bad), "direct ComfyUI /prompt should be flagged"


def test_lint_passes_clean_file(tmp_path):
    ok = tmp_path / "clean.py"
    ok.write_text("from harness import run\nrun.run_model()\n", encoding="utf-8")
    assert lint.check_file(ok) == []


def test_lint_main_fails_on_violation(tmp_path, capsys):
    bad = tmp_path / "rogue.py"
    bad.write_text("import openai\n", encoding="utf-8")
    rc = lint.main([str(bad)])
    assert rc == 1
