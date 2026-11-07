#!/usr/bin/env bash
# Train the Nast Flux schnell LoRA and archive to S3. NO box finalize — the queue orchestrator
# (run_queue.sh) decides terminate-vs-stop after all queued jobs run. Exit 0 = LoRA archived.
set -uo pipefail
cd ~/ai-toolkit
source ~/aitk/bin/activate
set -a; . ~/slm-foundry/.env; set +a
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_DISABLE_XET=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo "=== [NAST] PRE-DOWNLOAD schnell $(date -u) ==="
python - <<'PY'
import os
from huggingface_hub import snapshot_download
tok = os.environ.get("HF_TOKEN")
snapshot_download("black-forest-labs/FLUX.1-schnell", token=tok)
snapshot_download("ostris/FLUX.1-schnell-training-adapter", token=tok)
print("PREDOWNLOAD_OK", flush=True)
PY
[ $? -ne 0 ] && { echo "[NAST] pre-download failed"; exit 1; }
hf auth login --token "$HF_TOKEN" >/dev/null 2>&1 || true   # hf replaces the deprecated huggingface-cli

echo "=== [NAST] TRAIN $(date -u) ==="
python run.py ~/slm-foundry/packs/nast/hand/flux_lora.yaml
echo "=== [NAST] TRAIN EXITED $(date -u) ==="

if ls ~/ai-toolkit/output/nast_flux/*.safetensors >/dev/null 2>&1; then
  aws s3 cp ~/ai-toolkit/output/nast_flux/ s3://ilyrium-slm-foundry/models/nast/hand/flux/ \
    --recursive --exclude "*" --include "*.safetensors" --include "*.png" --only-show-errors && echo "[NAST] S3_OK"
  exit 0
fi
echo "[NAST] NO LoRA produced"
exit 1
