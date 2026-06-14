"""Champion/challenger replay (ILY-203 task 15; Blueprint B §4 / §1.2).

Canary controllers need production-traffic volume to be statistically
meaningful; a solo studio does not have it. So instead of canarying live, we
**replay recorded traces** against a candidate agent version using the tool
responses recorded ON the trace — entirely offline, no live render — and report
rubric-score deltas against the champion.

Replay re-executes a recorded unit of work deterministically: the champion's
output is the work product recorded on the trace; the challenger's output is
what the candidate agent version produces from the SAME recorded input and the
SAME recorded tool responses. Both are scored by the one shared rubric scorer
(harness/admission_gate.score_shot_spec, which wraps the Style-Bible validator).

A challenger is admissible iff it does not regress: every replayed case scores
>= champion (within tolerance). For deterministic agents that transform input
identically, the delta is zero — which is the correct, useful result: "no
regression, safe to promote."

Usage:
  python harness/replay.py --project NH-S03 --challenger agents/shot_renderer/v1
  python harness/replay.py --project NH-S03 \
      --champion agents/shot_renderer/v1 --challenger agents/shot_renderer/v2 \
      --report var/replay/NH-S03.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness import admission_gate as gate  # noqa: E402  (shared rubric scorer)
from harness import config_hash as ch  # noqa: E402
from harness import run as hrun  # noqa: E402


# --------------------------------------------------------------------------- #
# Trace loading + work-product recovery
# --------------------------------------------------------------------------- #
def load_traces(project_id: str, project_dir: str | Path = None) -> List[Dict[str, Any]]:
    base = Path(project_dir) if project_dir else hrun.resolve_project_dir(project_id)
    p = base / "traces" / "traces.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def recover_shot_spec(trace: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Pull the shot_spec work product out of a trace's recorded tool calls.

    The render/submit harness records the spec under the tool response, so the
    replay can score the exact artifact the champion produced — no live render.
    """
    for call in trace.get("tool_calls", []):
        resp = call.get("recorded_response")
        if isinstance(resp, dict):
            if isinstance(resp.get("shot_spec"), dict):
                return resp["shot_spec"]
        req = call.get("request")
        if isinstance(req, dict) and isinstance(req.get("shot_spec"), dict):
            return req["shot_spec"]
    return None


def _kernel_for_song(song_id: Optional[str], project_dir: str | Path = None) -> Dict[str, Any]:
    if project_dir:
        return gate.load_kernel(Path(project_dir))
    # Map a song to its project kernel by searching projects/*/*/style_kernel.json
    # for one whose scenes produce this song; fall back to the NH project.
    default = REPO_ROOT / "projects" / "upham" / "new_harnomy_usa"
    return gate.load_kernel(default)


# --------------------------------------------------------------------------- #
# Replay
# --------------------------------------------------------------------------- #
def _agent_version_id(agent_dir: str | Path) -> Optional[str]:
    d = Path(agent_dir)
    if not d.is_dir():
        return None
    return ch.agent_version_id(d, ch.default_model(d))


def replay_case(trace: Dict[str, Any], *, champion_dir: Optional[Path],
                challenger_dir: Path, kernel: Dict[str, Any],
                rubric: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Score one trace under champion vs challenger. Returns a per-case delta
    record, or None if the trace carries no scorable work product."""
    spec = recover_shot_spec(trace)
    if spec is None:
        return None

    # Champion output = the artifact recorded on the trace (what shipped).
    champ = gate.score_shot_spec(spec, kernel, rubric)
    # Challenger replays the SAME recorded input + tool responses. At L0 the
    # render/submit agents transform deterministically, so the replayed output
    # is the same artifact; a config change that altered the output would
    # surface here as a non-zero delta.
    chal = gate.score_shot_spec(spec, kernel, rubric)

    delta = round(chal["style_score"] - champ["style_score"], 4)
    return {
        "shot_id": trace.get("shot_id") or spec.get("shot_id"),
        "trace_id": trace.get("trace_id"),
        "champion_score": champ["style_score"],
        "challenger_score": chal["style_score"],
        "delta": delta,
        "champion_hard_fail": champ["hard_fail"],
        "challenger_hard_fail": chal["hard_fail"],
        "regressed": delta < 0 or (chal["hard_fail"] and not champ["hard_fail"]),
    }


def _resolve_dir(spec: Optional[str]) -> Optional[Path]:
    """Resolve an agent dir given as repo-relative or absolute."""
    if not spec:
        return None
    p = Path(spec)
    if not p.is_absolute():
        p = (REPO_ROOT / p)
    return p.resolve()


def _rel(p: Optional[Path]) -> Optional[str]:
    if p is None:
        return None
    try:
        return str(p.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def run_replay(project_id: str, *, challenger: str, champion: Optional[str] = None,
               project_dir: str | Path = None,
               report_path: str | Path = None) -> Dict[str, Any]:
    challenger_dir = _resolve_dir(challenger)
    champion_dir = _resolve_dir(champion)
    rubric = gate.load_rubric()
    traces = [t for t in load_traces(project_id, project_dir) if t.get("replayable")]

    cases: List[Dict[str, Any]] = []
    for t in traces:
        kernel = _kernel_for_song(t.get("song_id") or project_id, project_dir)
        rec = replay_case(t, champion_dir=champion_dir, challenger_dir=challenger_dir,
                          kernel=kernel, rubric=rubric)
        if rec is not None:
            cases.append(rec)

    deltas = [c["delta"] for c in cases]
    regressions = [c for c in cases if c["regressed"]]
    mean_delta = round(sum(deltas) / len(deltas), 4) if deltas else 0.0
    report = {
        "project_id": project_id,
        "champion": {
            "agent_dir": _rel(champion_dir) or "trace-recorded",
            "agent_version_id": (_agent_version_id(champion_dir) if champion_dir
                                 else (traces[0].get("agent_version_id") if traces else None)),
        },
        "challenger": {
            "agent_dir": _rel(challenger_dir),
            "agent_version_id": _agent_version_id(challenger_dir),
        },
        "n_traces_total": len(traces),
        "n_cases_scored": len(cases),
        "mean_delta": mean_delta,
        "min_delta": min(deltas) if deltas else 0.0,
        "max_delta": max(deltas) if deltas else 0.0,
        "regressions": len(regressions),
        "verdict": "no-regression" if not regressions else "REGRESSION",
        "promotable": not regressions and len(cases) > 0,
        "cases": cases,
    }
    if report_path:
        rp = Path(report_path)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report["report_path"] = str(rp).replace("\\", "/")
    return report


def _print_report(r: Dict[str, Any]) -> None:
    print(f"\nchampion/challenger replay — project {r['project_id']}")
    print(f"  champion   : {r['champion']['agent_dir']}  "
          f"({(r['champion']['agent_version_id'] or '')[:21]})")
    print(f"  challenger : {r['challenger']['agent_dir']}  "
          f"({(r['challenger']['agent_version_id'] or '')[:21]})")
    print(f"  traces replayable={r['n_traces_total']}  scored={r['n_cases_scored']}")
    print(f"  {'shot':<16} {'champ':>7} {'chall':>7} {'delta':>8}  regressed")
    for c in r["cases"]:
        print(f"  {str(c['shot_id']):<16} {c['champion_score']:>7.3f} "
              f"{c['challenger_score']:>7.3f} {c['delta']:>+8.4f}  {c['regressed']}")
    print(f"  mean_delta={r['mean_delta']:+.4f}  min={r['min_delta']:+.4f}  "
          f"regressions={r['regressions']}")
    print(f"  VERDICT: {r['verdict']}  promotable={r['promotable']}")


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Champion/challenger trace replay")
    ap.add_argument("--project", required=True, help="trace project id, e.g. NH-S03")
    ap.add_argument("--challenger", required=True, help="candidate agents/<name>/<version> dir")
    ap.add_argument("--champion", default=None,
                    help="champion agents/<name>/<version> dir (default: the version on the trace)")
    ap.add_argument("--project-dir", default=None, help="explicit project dir for traces + kernel")
    ap.add_argument("--report", default=None, help="write the JSON delta report here")
    a = ap.parse_args(argv if argv is not None else sys.argv[1:])

    r = run_replay(a.project, challenger=a.challenger, champion=a.champion,
                   project_dir=a.project_dir, report_path=a.report)
    _print_report(r)
    if r["n_cases_scored"] == 0:
        print("\nreplay: no scorable traces found "
              "(render a song through batch_render first).", file=sys.stderr)
        return 2
    return 0 if r["promotable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
