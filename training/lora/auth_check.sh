#!/usr/bin/env bash
# Persist the HF token (new `hf` CLI) and verify the GATED FLUX.1-dev repo authenticates
# AMBIENTLY (no explicit token) — i.e. the same path ai-toolkit's from_pretrained/model_info uses.
set -a; . ~/slm-foundry/.env; set +a
source ~/aitk/bin/activate 2>/dev/null
hf auth login --token "$HF_TOKEN" >/dev/null 2>&1 && echo "login_ok" || echo "login_fail"
hf auth whoami 2>&1 | head -2
python - <<'PY'
from huggingface_hub import HfApi
try:
    mi = HfApi().model_info("black-forest-labs/FLUX.1-dev")   # NO explicit token -> ambient (token file)
    print("AMBIENT_OK", mi.id)
except Exception as e:
    print("AMBIENT_FAIL", type(e).__name__, str(e)[:200])
PY
