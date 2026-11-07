#!/usr/bin/env bash
# Bootstrap ai-toolkit on a box that has a CUDA-capable python (e.g. ~/senv) but no
# ~/ai-toolkit / ~/aitk. Creates the ~/aitk venv that run_stripe_and_finalize.sh expects
# (so that wrapper runs UNCHANGED) and installs ai-toolkit + deps. Idempotent.
# Logs to ~/aitk_install.log and prints INSTALL_OK on success.
set -uo pipefail
LOG="$HOME/aitk_install.log"
exec > >(tee "$LOG") 2>&1
echo "=== AITK BOOTSTRAP START $(date -u) ==="
cd "$HOME"

if [ ! -d "$HOME/ai-toolkit/.git" ]; then
  echo "--- cloning ai-toolkit ---"
  git clone --recurse-submodules https://github.com/ostris/ai-toolkit.git "$HOME/ai-toolkit" || { echo "FAIL_CLONE"; exit 1; }
else
  echo "--- ai-toolkit present; syncing submodules ---"
  ( cd "$HOME/ai-toolkit" && git submodule update --init --recursive )
fi

if [ ! -x "$HOME/aitk/bin/python" ]; then
  echo "--- creating ~/aitk venv (from senv python) ---"
  "$HOME/senv/bin/python" -m venv "$HOME/aitk" || { echo "FAIL_VENV"; exit 1; }
fi
PIP="$HOME/aitk/bin/pip"

echo "--- upgrade pip/wheel ---"
"$PIP" install -U pip wheel setuptools

echo "--- install ai-toolkit requirements (pulls torch) $(date -u) ---"
"$PIP" install -r "$HOME/ai-toolkit/requirements.txt" || { echo "FAIL_REQS"; exit 1; }

echo "--- verify $(date -u) ---"
"$HOME/aitk/bin/python" - <<'PY' || { echo "FAIL_VERIFY"; exit 1; }
import torch
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
assert torch.cuda.is_available(), "CUDA not available in aitk venv"
import importlib
for m in ["safetensors","transformers","diffusers","peft","accelerate"]:
    importlib.import_module(m); print("ok", m)
PY
test -f "$HOME/ai-toolkit/run.py" || { echo "FAIL_NORUN"; exit 1; }
echo "INSTALL_OK $(date -u)"
