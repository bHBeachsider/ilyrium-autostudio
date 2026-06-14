"""Lint gate: harness-only execution (ILY-203 task 4; Blueprint B day-zero rule 1).

Fails any Python file OUTSIDE harness/ that
  (a) imports a model SDK (anthropic, openai, google genai, mistral, cohere,
      litellm, ollama), or
  (b) speaks to the ComfyUI API directly (an HTTP client import combined with
      a ComfyUI endpoint literal: /prompt, /upload/image, /history/,
      /system_stats, /view?).

The only sanctioned path is harness.run — which stamps agent_version_id,
injects credentials from the environment, records tool I/O for replay, and
emits traces. This gate is what makes untraced execution structurally
impossible rather than merely discouraged.

LEGACY BASELINE: pre-harness files listed below are reported as warnings, not
failures, each tied to FINDINGS.md F-0004. Migrating a file removes it from
the baseline in the same PR (strangler rule — dual enforcement is how
fix-cascades start). Adding NEW entries to the baseline is prohibited.

Usage:
  python harness/lint_no_raw_sdk.py <file> [...]   # pre-commit passes staged files
  python harness/lint_no_raw_sdk.py --all           # scan the whole repo
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SDK_IMPORT_RE = re.compile(
    r"^\s*(?:import|from)\s+"
    r"(anthropic|openai|google\.generativeai|google\.genai|mistralai|cohere|litellm|ollama)\b",
    re.MULTILINE,
)
HTTP_CLIENT_RE = re.compile(r"\b(urllib\.request|requests\.(?:get|post|request)|httpx\.)")
COMFY_ENDPOINT_RE = re.compile(r"(/prompt['\"]|/upload/image|/history/|/system_stats|/view\?)")

# A file may opt out explicitly (e.g. a test that constructs violation fixtures,
# or vendored code). Auditable, unlike a silent directory exclude.
ALLOW_PRAGMA = "lint-no-raw-sdk: allow"

# Directory names never linted: the harness itself, vendored code, caches.
EXCLUDE_DIR_NAMES = {
    "harness", "ComfyUI", "__pycache__", "node_modules", ".git",
    "_test", ".superpowers", "99_archive",
}

# Pre-harness violators, each tied to a findings-registry entry. WARN, not FAIL.
# Do NOT add entries — migrate the file through harness.run instead (F-0004).
# This is the strangler-fig baseline: the loop shrinks it; nothing grows it.
LEGACY_BASELINE = {
    "apps/auto-studio/app.py": "F-0004",
    "apps/auto-studio/ad_studio_agent.py": "F-0004",
    "apps/auto-studio/eval_tool_knowledge.py": "F-0004",
    "apps/auto-studio/delivery.py": "F-0004",
    "apps/auto-studio/pipeline_exec.py": "F-0004",
    "apps/auto-studio/stage_agents.py": "F-0004",
    "apps/auto-studio/ec2_session.py": "F-0004",
    "apps/auto-studio/media/comfyui_renderer.py": "F-0004",
    "apps/auto-studio/agents/art_director.py": "F-0004",
    "apps/auto-studio/agents/copywriter.py": "F-0004",
    "ilyrium-shots/keyframe_to_comfy.py": "F-0004",
    "projects/upham/new_harnomy_usa/05_production/scripts/generate_teaser.py": "F-0004",
    "projects/upham/new_harnomy_usa/05_production/scripts/veo_prompt.py": "F-0004",
}


def _excluded(path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        rel = path
    return any(part in EXCLUDE_DIR_NAMES for part in rel.parts)


def check_file(path: Path) -> list[str]:
    """Return a list of violation descriptions for one file (empty = clean)."""
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as exc:
        return [f"unreadable: {exc}"]
    if ALLOW_PRAGMA in text:
        return []
    out = []
    m = SDK_IMPORT_RE.search(text)
    if m:
        out.append(f"raw model-SDK import '{m.group(1)}' — use harness.run.run_model()")
    if HTTP_CLIENT_RE.search(text) and COMFY_ENDPOINT_RE.search(text):
        out.append("direct ComfyUI API access — use harness.run.comfy_* transports")
    return out


def _all_repo_files() -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "--", "*.py"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    return [REPO_ROOT / line for line in proc.stdout.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "--all":
        files = _all_repo_files()
    else:
        files = [Path(a) for a in args]
    if not files:
        print("lint_no_raw_sdk: no files to check (pass paths or --all)")
        return 0

    failures, warnings = [], []
    for f in files:
        if f.suffix != ".py" or _excluded(f) or not f.exists():
            continue
        violations = check_file(f)
        if not violations:
            continue
        try:
            rel = str(f.resolve().relative_to(REPO_ROOT)).replace("\\", "/")
        except ValueError:
            rel = str(f).replace("\\", "/")
        finding = LEGACY_BASELINE.get(rel)
        for v in violations:
            if finding:
                warnings.append(f"  WARN {rel}: {v} [legacy baseline {finding}]")
            else:
                failures.append(f"  FAIL {rel}: {v}")

    for w in warnings:
        print(w)
    if failures:
        print("lint_no_raw_sdk: harness-only execution violated:", file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)
        print("(route the call through harness/run.py; see README_RSI.md)", file=sys.stderr)
        return 1
    print(f"lint_no_raw_sdk: OK ({len(files)} file(s) checked, "
          f"{len(warnings)} legacy warning(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
