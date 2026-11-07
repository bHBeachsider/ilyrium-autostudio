#!/usr/bin/env bash
# Train the Stripe character Flux LoRA (v7 nano-banana trainset), archive to S3, then
# TERMINATE the box on success (no idle/storage billing) or STOP on failure (keep volume to debug).
#
# Pulls the trainset from S3 first, so the box needs nothing staged by hand.
# Detached launch (survives your local reboot):
#   nohup bash ~/slm-foundry/packs/stripe/run_stripe_and_finalize.sh </dev/null >~/stripe_train.log 2>&1 & disown
#
# Gated-Flux note (same as nast): ai-toolkit's from_pretrained does NOT pass the HF token, so the
# gated FLUX.1-dev 403s even with a valid token. Fix: snapshot_download the repo (ambient auth works),
# then authenticate so diffusers' metadata round-trip succeeds; shards load from the warm cache.
set -u
S3=s3://ilyrium-slm-foundry
TRAIN_DIR=/home/ec2-user/stripe_train_v7_nb
YAML=/home/ec2-user/slm-foundry/packs/stripe/stripe_flux_char_v7_nb.yaml
OUT=/home/ec2-user/ai-toolkit/output/stripe_char_v7_nb

cd ~/ai-toolkit || { echo "no ai-toolkit dir"; exit 1; }
source ~/aitk/bin/activate
set -a; . ~/slm-foundry/.env; set +a
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_DISABLE_XET=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo "=== PULL trainset from S3 $(date -u) ==="
mkdir -p "$TRAIN_DIR"
aws s3 cp "$S3/data/stripe/train_v7_nb/" "$TRAIN_DIR/" --recursive --only-show-errors \
  --exclude "*" --include "*.png" --include "*.txt"
n=$(ls "$TRAIN_DIR"/*.png 2>/dev/null | wc -l)
echo "trainset images: $n"
if [ "$n" -lt 8 ]; then echo "TRAINSET TOO SMALL -- aborting, STOPPING"; sudo shutdown -h now; exit 1; fi

echo "=== PRE-DOWNLOAD FLUX.1-dev (online, with token) $(date -u) ==="
python - <<'PY'
import os
from huggingface_hub import snapshot_download
tok = os.environ.get("HF_TOKEN")
print("downloading black-forest-labs/FLUX.1-dev ...", flush=True)
snapshot_download("black-forest-labs/FLUX.1-dev", token=tok)
print("PREDOWNLOAD_DONE", flush=True)
PY
if [ $? -ne 0 ]; then echo "PRE-DOWNLOAD FAILED -- STOPPING"; sudo shutdown -h now; exit 1; fi

# authenticate so the gated metadata call during the sharded load succeeds (shards come from cache)
huggingface-cli login --token "$HF_TOKEN" >/dev/null 2>&1 || python - <<'PY'
import os
from huggingface_hub import login
login(token=os.environ["HF_TOKEN"])
PY

echo "=== STRIPE FLUX TRAINING START $(date -u) ==="
python run.py "$YAML"
echo "=== STRIPE FLUX TRAINING EXITED $(date -u) ==="

_TOK=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 120")
_IID=$(curl -s -H "X-aws-ec2-metadata-token: $_TOK" http://169.254.169.254/latest/meta-data/instance-id)

if ls "$OUT"/*.safetensors >/dev/null 2>&1; then
  echo "=== archiving Stripe LoRA -> S3 ==="
  aws s3 cp "$OUT/" "$S3/models/stripe/char/flux_v7_nb/" --recursive \
    --exclude "*" --include "*.safetensors" --only-show-errors && echo "S3_ARCHIVE_OK"
  echo "=== SUCCESS: terminating box $(date -u) ==="
  aws ec2 terminate-instances --region us-east-1 --instance-ids "$_IID" || sudo shutdown -h now
else
  echo "=== NO LoRA produced (training failed) -- STOPPING for debug $(date -u) ==="
  sudo shutdown -h now
fi
