"""Run the legacy shell entry point with a fake AWS executable, never a host."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.parametrize("code,attempts,exit_code", [
    ("InvalidInstanceID.NotFound", 1, 2),
    ("UnauthorizedOperation", 1, 2),
    ("VcpuLimitExceeded", 1, 2),
    ("InsufficientInstanceCapacity", 2, 75),
    ("InternalError", 1, 76),
])
def test_only_capacity_retries_and_every_retry_is_bounded(tmp_path, code, attempts, exit_code):
    bash = Path("C:/Program Files/Git/bin/bash.exe") if os.name == "nt" else Path(shutil.which("bash") or "")
    if not bash.is_file():
        pytest.skip("Bash unavailable")
    log = tmp_path / "calls.txt"
    env = dict(os.environ, CALL_LOG=log.as_posix(), ERROR_CODE=code, G6E="i-0123456789abcdef0",
               ALLOW_G6="0", INTERVAL="1", MAX_ATTEMPTS="2", AWS_MAX_ATTEMPTS="9")
    script = Path(__file__).resolve().parents[1] / "launch_stripe_train.sh"
    # Shell functions intercept AWS/SSH even if Git Bash rewrites PATH. The
    # bounded fake terminates only this shell if old code polls indefinitely.
    harness = '''
aws() {
  printf '%s %s\n' "$AWS_MAX_ATTEMPTS" "$*" >> "$CALL_LOG"
  if [[ $(wc -l < "$CALL_LOG") -gt 2 ]]; then kill -TERM "$$"; return 99; fi
  printf 'An error occurred (%s) when calling the StartInstances operation: SECRET\n' "$ERROR_CODE" >&2
  return 255
}
sleep() { if [[ "$ERROR_CODE" != InsufficientInstanceCapacity ]]; then exit 97; fi; }
ssh() { echo 'UNEXPECTED_SSH'; exit 98; }
scp() { echo 'UNEXPECTED_SCP'; exit 98; }
source "$1"
'''
    try:
        result = subprocess.run([str(bash), "--noprofile", "--norc", "-c", harness, "test", script.as_posix()],
                                env=env, capture_output=True, text=True, timeout=8)
    except subprocess.TimeoutExpired:
        pytest.fail("launcher kept polling instead of enforcing its error/attempt boundary")
    assert result.returncode == exit_code
    calls = log.read_text().splitlines()
    assert len(calls) == attempts
    assert all(c.startswith("1 ec2 start-instances") for c in calls)
    assert "SECRET" not in result.stdout + result.stderr
    if code != "InsufficientInstanceCapacity":
        assert "no capacity" not in result.stdout.lower()
