#!/usr/bin/env bash
# Train the Broderick Flux.1-dev LoRA and archive to S3. NO box finalize. Exit 0 = LoRA archived.
# Requires the grayscale dataset already staged at packs/broderick/data/hand/train (stage_dataset
# step in run_queue / scp). FLUX.1-dev is gated — the HF token must have accepted the dev license.
set -uo pipefail
cd ~/ai-toolkit
source ~/aitk/bin/activate
set -a; . ~/slm-foundry/.env; set +a
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_DISABLE_XET=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# Email the completion summary to the operator (works once bupham@ilyrium.io is SES-verified;
# guarded so a send failure never blocks the box finalize). Fires before every exit below.
NOTIFIED=0
send_done_email() {  # $1 = short status — sends Telegram (primary) + SES email (backup)
  # Telegram via the Bot API directly (token+chat in .env); fires regardless of any local machine state
  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
    curl -s -m 20 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
      --data-urlencode "text=🤖 SLM Foundry — Flux training queue finished: $1
Nast:      s3://ilyrium-slm-foundry/models/nast/hand/flux/
Broderick: s3://ilyrium-slm-foundry/models/broderick/hand/flux/
Box terminates on full success (\$0 volume); stops for debug on failure." \
      >/dev/null 2>&1 || true
  fi
  aws ses send-email --region us-east-1 \
    --from bupham@ilyrium.io --to bupham@ilyrium.io \
    --subject "[SLM Foundry] Flux training queue finished — $1" \
    --text "SLM Foundry training queue finished at $(date -u).

Broderick (FLUX.1-dev) result: $1

Check S3 for the LoRAs:
  aws s3 ls s3://ilyrium-slm-foundry/models/nast/hand/flux/
  aws s3 ls s3://ilyrium-slm-foundry/models/broderick/hand/flux/

On full success the L40S box terminates itself (volume -> 0 cost); on failure it stops for debug." \
    >/dev/null 2>&1 || true
  NOTIFIED=1
}
# Catch-all: alert on ANY exit (early exit, crash, set -u abort) that didn't already notify.
trap '[ "$NOTIFIED" = "0" ] && send_done_email "FAILED — Broderick exited without producing a LoRA (see ~/queue_train.log)"' EXIT

DATA=~/slm-foundry/packs/broderick/data/hand/train
n=$(ls "$DATA"/*.png "$DATA"/*.jpg 2>/dev/null | wc -l)
echo "=== [BRDRCK] dataset images staged: $n $(date -u) ==="
[ "$n" -lt 50 ] && { echo "[BRDRCK] dataset missing/too small ($n) — aborting"; exit 1; }

# FLUX.1-schnell (~54GB) + FLUX.1-dev (~24GB) won't coexist on the 200GB volume. Nast (schnell)
# is already archived to S3, so drop its cache + outputs to make room for the dev download.
echo "=== [BRDRCK] free disk — drop schnell cache + Nast outputs (already in S3) $(date -u) ==="
rm -rf ~/.cache/huggingface/hub/models--black-forest-labs--FLUX.1-schnell \
       ~/.cache/huggingface/hub/models--ostris--FLUX.1-schnell-training-adapter \
       ~/ai-toolkit/output/nast_flux ~/ai-toolkit/output/nast_sdxl
df -h / | tail -1

echo "=== [BRDRCK] PRE-DOWNLOAD FLUX.1-dev (gated) $(date -u) ==="
python - <<'PY'
import os, sys
from huggingface_hub import snapshot_download
tok = os.environ.get("HF_TOKEN")
try:
    snapshot_download("black-forest-labs/FLUX.1-dev", token=tok)
    print("PREDOWNLOAD_OK", flush=True)
except Exception as e:
    print("DEV_GATED_OR_UNAVAILABLE:", e, flush=True)
    sys.exit(7)
PY
rc=$?
[ $rc -eq 7 ] && { echo "[BRDRCK] FLUX.1-dev pre-download failed (gating OR disk space — see the error above)"; exit 1; }
[ $rc -ne 0 ] && { echo "[BRDRCK] pre-download failed"; exit 1; }
hf auth login --token "$HF_TOKEN" >/dev/null 2>&1 || true   # persist token file so the gated-dev loader (model_info) authenticates ambiently

echo "=== [BRDRCK] TRAIN $(date -u) ==="
python run.py ~/slm-foundry/packs/broderick/hand/flux_dev_lora.yaml
echo "=== [BRDRCK] TRAIN EXITED $(date -u) ==="

if ls ~/ai-toolkit/output/broderick_flux/*.safetensors >/dev/null 2>&1; then
  aws s3 cp ~/ai-toolkit/output/broderick_flux/ s3://ilyrium-slm-foundry/models/broderick/hand/flux/ \
    --recursive --exclude "*" --include "*.safetensors" --include "*.png" --only-show-errors && echo "[BRDRCK] S3_OK"
  send_done_email "SUCCESS — Broderick LoRA archived"
  exit 0
fi
echo "[BRDRCK] NO LoRA produced"
send_done_email "FAILED — no Broderick LoRA produced"
exit 1
