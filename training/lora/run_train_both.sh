#!/usr/bin/env bash
# Train BOTH Broderick LoRAs on Flux-dev, archive each to S3, finalize the box.
#   1) character LoRA  (brdmc)  -> models/broderick/hand/char/
#   2) style Hand v2  (brdrck, short captions) -> models/broderick/hand/flux_v2/
# Both archive .safetensors + sample .png (so we can SEE them). Terminate on full success,
# stop on failure. Launch detached:
#   nohup bash ~/slm-foundry/packs/run_train_both.sh </dev/null >~/train.log 2>&1 & disown
set -uo pipefail
cd ~/ai-toolkit
source ~/aitk/bin/activate
set -a; . ~/slm-foundry/.env; set +a
export HF_HUB_ENABLE_HF_TRANSFER=1 HF_HUB_DISABLE_XET=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
hf auth login --token "$HF_TOKEN" >/dev/null 2>&1 || huggingface-cli login --token "$HF_TOKEN" >/dev/null 2>&1 || true

echo "=== PRE-DOWNLOAD FLUX.1-dev (gated) $(date -u) ==="
python - <<'PY'
import os
from huggingface_hub import snapshot_download
snapshot_download("black-forest-labs/FLUX.1-dev", token=os.environ.get("HF_TOKEN"))
print("DEV_OK", flush=True)
PY
[ $? -ne 0 ] && { echo "dev pre-download failed -> stop"; sudo shutdown -h now; exit 1; }

archive() {  # $1 = output subdir name, $2 = s3 subpath
  if ls ~/ai-toolkit/output/$1/*.safetensors >/dev/null 2>&1; then
    aws s3 cp ~/ai-toolkit/output/$1/ s3://ilyrium-slm-foundry/models/broderick/hand/$2/ \
      --recursive --exclude "*" --include "*.safetensors" --include "*.png" --only-show-errors && return 0
  fi
  return 1
}

echo "######## [CHAR] train brdmc $(date -u) ########"
python run.py ~/slm-foundry/packs/broderick/hand/flux_char_lora.yaml
archive broderick_char char && CHAR=0 || CHAR=1
echo "######## [CHAR] exit=$CHAR $(date -u) ########"

echo "######## [STYLEv2] train brdrck (short captions) $(date -u) ########"
python run.py ~/slm-foundry/packs/broderick/hand/flux_dev_lora_v2.yaml
archive broderick_flux_v2 flux_v2 && STYLE=0 || STYLE=1
echo "######## [STYLEv2] exit=$STYLE $(date -u) ########"

if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  curl -s -m 20 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=🧠 Broderick LoRAs trained: char=$([ $CHAR -eq 0 ] && echo OK || echo FAIL) style_v2=$([ $STYLE -eq 0 ] && echo OK || echo FAIL) -> s3 models/broderick/hand/{char,flux_v2}/. Box finalizing." >/dev/null 2>&1 || true
fi

_TOK=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 120")
_IID=$(curl -s -H "X-aws-ec2-metadata-token: $_TOK" http://169.254.169.254/latest/meta-data/instance-id)
if [ "${CHAR:-1}" -eq 0 ] && [ "${STYLE:-1}" -eq 0 ]; then
  echo "######## BOTH OK -> TERMINATE (volume -> 0) $(date -u) ########"
  aws ec2 terminate-instances --region us-east-1 --instance-ids "$_IID" || sudo shutdown -h now
else
  echo "######## FAILURE (char=$CHAR style=$STYLE) -> STOP for debug $(date -u) ########"
  sudo shutdown -h now
fi
