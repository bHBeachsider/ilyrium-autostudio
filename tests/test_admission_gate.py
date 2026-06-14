"""Tests for the eval-driven admission gate (ILY-203 task 16).

Validates: refusal of an active agent missing golden cases or a rubric
reference, acceptance of a conforming agent directory, the skip path for
non-required (prose) agents, and the wrapped style-validator scorer.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness import admission_gate as gate
from harness import config_hash as ch


def _make_agent(root: Path, name: str, *, required: bool, n_golden: int,
                rubric_ok: bool = True, version: str = "v1"):
    d = root / "agents" / name / version
    d.mkdir(parents=True, exist_ok=True)
    (d / "prompt.md").write_text(f"# {name}\nbe terse\n", encoding="utf-8")
    (d / "tools.yaml").write_text("tools: []\n", encoding="utf-8")
    req = "true" if required else "false"
    reason = "" if required else "  reason: prose ideation agent\n"
    (d / "routing.yaml").write_text(
        f"task_type: spec_draft\nmodel: claude-sonnet-4-6\n"
        f"admission:\n  required: {req}\n{reason}", encoding="utf-8")
    (d / "permissions.yaml").write_text("read: [project]\n", encoding="utf-8")

    golden_rel = f"evals/golden/{name}"
    golden_dir = root / golden_rel
    golden_dir.mkdir(parents=True, exist_ok=True)
    for i in range(n_golden):
        (golden_dir / f"case_{i:02d}.json").write_text(
            json.dumps({"case_id": f"c{i}"}), encoding="utf-8")

    rubric_rel = "evals/rubrics/studio_rubric.yaml"
    if rubric_ok:
        (root / "evals" / "rubrics").mkdir(parents=True, exist_ok=True)
        (root / rubric_rel).write_text("rubric_id: studio_rubric\n", encoding="utf-8")
    ch.write_manifest(d, golden_set=golden_rel, rubric=rubric_rel)
    return d


@pytest.fixture(autouse=True)
def _point_repo_root(tmp_path, monkeypatch):
    """Run the gate against a temp repo root so tests are hermetic."""
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    yield


def test_conforming_active_agent_admitted(tmp_path):
    d = _make_agent(tmp_path, "shot_spec_generator", required=True, n_golden=5)
    v = gate.check_agent(d)
    assert v["admitted"] is True
    assert v["n_golden"] == 5
    assert v["problems"] == []


def test_agent_missing_golden_cases_refused(tmp_path):
    d = _make_agent(tmp_path, "thin_agent", required=True, n_golden=3)
    v = gate.check_agent(d)
    assert v["admitted"] is False
    assert any("golden" in p for p in v["problems"])


def test_agent_missing_rubric_reference_refused(tmp_path):
    d = _make_agent(tmp_path, "no_rubric", required=True, n_golden=5, rubric_ok=False)
    v = gate.check_agent(d)
    assert v["admitted"] is False
    assert any("rubric" in p for p in v["problems"])


def test_non_required_agent_skipped_not_refused(tmp_path):
    d = _make_agent(tmp_path, "stage_00_bible", required=False, n_golden=0)
    v = gate.check_agent(d)
    assert v["skipped"] is True
    assert v["admitted"] is True


def test_manifest_drift_refused(tmp_path):
    d = _make_agent(tmp_path, "drifter", required=True, n_golden=5)
    # Mutate a config file AFTER the manifest was stamped -> config_hash drift.
    (d / "prompt.md").write_text("# drifter\nrewritten after stamping\n", encoding="utf-8")
    v = gate.check_agent(d)
    assert v["admitted"] is False
    assert any("config_hash" in p for p in v["problems"])


def test_gate_all_returns_nonzero_when_any_refused(tmp_path):
    _make_agent(tmp_path, "good", required=True, n_golden=5)
    _make_agent(tmp_path, "bad", required=True, n_golden=1)
    rc, verdicts = gate.gate_all(tmp_path / "agents")
    assert rc == 1
    assert len(verdicts) == 2


# --------------------------------------------------------------------------- #
# The wrapped style-validator scorer
# --------------------------------------------------------------------------- #
def test_scorer_wraps_style_validator_clean_spec():
    """A clean spec with a restated canon attribute scores high, no hard fail."""
    kernel = {"negatives": "text, watermark", "register": "serious, no winking",
              "casting_canon": {"pengold": "an American man, late 40s, solid build"},
              "palette_motifs": {"mauve": "brownish 1970s paperback, never lavender"},
              "look": "prestige drama"}
    spec = {"shot_id": "NH-S03-SH002",
            "prompt": "medium shot of an American man, late 40s, solid build, reading a mauve book",
            "action": "reads quietly", "subjects": ["pengold"], "mood": "settled"}
    res = gate.score_shot_spec(spec, kernel)
    assert res["hard_fail"] is False
    assert res["style_score"] >= 0.75
    assert res["passed"] is True


def test_scorer_hard_fails_on_likeness():
    kernel = {"negatives": "", "register": "", "casting_canon": {}, "look": "x"}
    spec = {"shot_id": "NH-S03-SH009",
            "prompt": "a man who looks like a famous president addresses the senate",
            "action": "speaks", "subjects": [], "mood": "grave"}
    res = gate.score_shot_spec(spec, kernel)
    assert res["hard_fail"] is True
    assert res["passed"] is False
