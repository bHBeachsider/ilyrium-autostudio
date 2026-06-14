"""Eval-driven agent admission gate (ILY-203 task 12; Blueprint B §4 rule 3).

An agent version is REFUSED registration unless it carries:
  * a manifest.json whose config_hash matches the directory contents,
  * at least MIN_GOLDEN golden cases under its golden_set, and
  * a rubric reference that resolves to a real rubric file.

Agents whose routing.yaml declares ``admission.required: false`` (the L0 prose
ideation agents, which have no deterministic shot-spec golden set yet) are
SKIPPED with a logged note — never silently. New active agents must pass.

This module also exposes the deterministic rubric SCORER (score_shot_spec),
which wraps apps/auto-studio/style_validator.py per studio_rubric.yaml. It is
the single scoring engine shared by the admission gate and harness/replay.py —
no second scorer exists.

Invoked from the pre-commit hook on changes under agents/ or evals/.
Usage:
  python harness/admission_gate.py            # gate every agent under agents/
  python harness/admission_gate.py --agent agents/shot_renderer/v1
  python harness/admission_gate.py --score evals/golden/.../case.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "apps" / "auto-studio"))

from harness import config_hash as ch  # noqa: E402

MIN_GOLDEN = 5
RUBRIC_PATH = REPO_ROOT / "evals" / "rubrics" / "studio_rubric.yaml"


# --------------------------------------------------------------------------- #
# Rubric loading + the wrapped style-validator scorer
# --------------------------------------------------------------------------- #
def load_rubric(path: Path = RUBRIC_PATH) -> Dict[str, Any]:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}


def _adapt_spec(shot_spec: Dict[str, Any], field_map: Dict[str, str]) -> Dict[str, Any]:
    """Map shot_spec fields onto the shape style_validator.validate_shot reads."""
    out = dict(shot_spec)
    for validator_field, spec_field in (field_map or {}).items():
        if spec_field in shot_spec and validator_field not in out:
            out[validator_field] = shot_spec[spec_field]
    return out


def score_shot_spec(shot_spec: Dict[str, Any], kernel: Dict[str, Any],
                    rubric: Dict[str, Any] = None) -> Dict[str, Any]:
    """Deterministic rubric score for one shot-spec, via the wrapped
    Style-Bible validator. Returns {style_score, hard_fail, checks, passed}."""
    rubric = rubric or load_rubric()
    import style_validator  # apps/auto-studio on path
    adapted = _adapt_spec(shot_spec, rubric.get("spec_field_map", {}))
    result = style_validator.validate_shot(adapted, kernel or {})
    min_score = float(rubric.get("thresholds", {}).get("min_style_score", 0.75))
    return {
        "style_score": result["score"],
        "hard_fail": result["hard_fail"],
        "checks": result["checks"],
        "passed": (not result["hard_fail"]) and result["score"] >= min_score,
        "min_style_score": min_score,
    }


def load_kernel(project_dir: str | Path) -> Dict[str, Any]:
    p = Path(project_dir) / "style_kernel.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8-sig"))
    return {}


# --------------------------------------------------------------------------- #
# Admission check
# --------------------------------------------------------------------------- #
def _admission_required(agent_dir: Path) -> Tuple[bool, str]:
    routing = ch._load_yaml(agent_dir / "routing.yaml")
    adm = routing.get("admission") or {}
    required = adm.get("required", True)
    return bool(required), (adm.get("reason") or "").strip()


def check_agent(agent_dir: str | Path) -> Dict[str, Any]:
    """Evaluate one agents/<name>/<version> dir. Returns a verdict dict."""
    d = Path(agent_dir)
    name = d.parent.name
    rel = str(d.resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    required, reason = _admission_required(d)
    problems: List[str] = []

    if not required:
        return {"agent_dir": rel, "agent": name, "required": False,
                "reason": reason, "admitted": True, "skipped": True,
                "problems": []}

    # 1) manifest present + matches directory contents
    manifest = ch.read_manifest(d)
    if manifest is None:
        problems.append("missing manifest.json")
    else:
        if manifest.get("config_hash") != ch.config_hash(d):
            problems.append("manifest config_hash does not match directory contents "
                            "(re-run config_hash.py --write-manifest)")
        rubric_ref = manifest.get("rubric")
        if not rubric_ref or not (REPO_ROOT / rubric_ref).exists():
            problems.append(f"rubric reference missing or unresolved: {rubric_ref!r}")
        golden_ref = manifest.get("golden_set")
    # 2) >= MIN_GOLDEN golden cases
    golden_dir = REPO_ROOT / (manifest.get("golden_set") if manifest else f"evals/golden/{name}")
    n_golden = len(list(golden_dir.glob("*.json"))) if golden_dir.is_dir() else 0
    if n_golden < MIN_GOLDEN:
        problems.append(f"only {n_golden} golden case(s) at {golden_dir.name}/ "
                        f"(need >= {MIN_GOLDEN})")

    return {"agent_dir": rel, "agent": name, "required": True,
            "n_golden": n_golden, "admitted": not problems,
            "skipped": False, "problems": problems}


def gate_all(agents_root: Path = None) -> Tuple[int, List[Dict[str, Any]]]:
    root = agents_root or (REPO_ROOT / "agents")
    verdicts = []
    for routing in sorted(root.glob("*/*/routing.yaml")):
        verdicts.append(check_agent(routing.parent))
    refused = [v for v in verdicts if not v["admitted"]]
    return (1 if refused else 0), verdicts


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Eval-driven agent admission gate")
    ap.add_argument("--agent", help="check a single agents/<name>/<version> dir")
    ap.add_argument("--score", help="score one golden case json against the rubric")
    ap.add_argument("--project-dir",
                    default="projects/upham/new_harnomy_usa",
                    help="project dir whose style_kernel.json scores --score")
    a = ap.parse_args(argv if argv is not None else sys.argv[1:])

    if a.score:
        case = json.loads(Path(a.score).read_text(encoding="utf-8-sig"))
        spec = case.get("reference_output") if "reference_output" in case else case
        if isinstance(spec, dict) and "shot_spec" in spec:
            spec = spec["shot_spec"]
        if isinstance(spec, dict) and "shot_spec" in case.get("input", {}):
            spec = case["input"]["shot_spec"]
        kernel = load_kernel(REPO_ROOT / a.project_dir)
        print(json.dumps(score_shot_spec(spec, kernel), indent=2))
        return 0

    if a.agent:
        v = check_agent(a.agent)
        print(json.dumps(v, indent=2))
        return 0 if v["admitted"] else 1

    rc, verdicts = gate_all()
    for v in verdicts:
        if v.get("skipped"):
            print(f"  skip   {v['agent_dir']}  (admission.required: false — {v['reason'][:60]})")
        elif v["admitted"]:
            print(f"  ADMIT  {v['agent_dir']}  ({v.get('n_golden')} golden cases)")
        else:
            print(f"  REFUSE {v['agent_dir']}")
            for p in v["problems"]:
                print(f"           - {p}")
    if rc:
        print("admission_gate: one or more active agents refused.", file=sys.stderr)
    else:
        print(f"admission_gate: OK ({len(verdicts)} agent version(s) checked)")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
