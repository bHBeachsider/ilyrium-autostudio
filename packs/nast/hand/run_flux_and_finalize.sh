#!/usr/bin/env bash
# Train the Nast Flux LoRA, archive to S3, then SHUT DOWN the box (no idle billing).
# Detached: nohup bash ~/slm-foundry/packs/nast/hand/run_flux_and_finalize.sh </dev/null >~/flux_train.log 2>&1 & disown
#
# WORKAROUND: ai-toolkit's from_pretrained does NOT pass the HF token, so gated Flux 403s even
# with a valid token. Fix: PRE-DOWNLOAD the full repos with snapshot_download (ambient auth works),
# then run training with HF_HUB_OFFLINE=1 so from_pretrained loads from the local cache (no auth).
cd ~/ai-toolkit
source ~/aitk/bin/activate
set -a; . ~/slm-foundry/.env; set +a
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_DISABLE_XET=1   # Xet backend crashed (writer error) on the prior run; use standard HTTP
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True   # reduce fragmentation at the quantize-load step (per the OOM error's own hint)

echo "=== PRE-DOWNLOAD Flux repos (online, with token) $(date -u) ==="
python - <<'PY'
import os
from huggingface_hub import snapshot_download
tok = os.environ.get("HF_TOKEN")
print("downloading black-forest-labs/FLUX.1-schnell ...", flush=True)
snapshot_download("black-forest-labs/FLUX.1-schnell", token=tok)
print("downloading ostris/FLUX.1-schnell-training-adapter ...", flush=True)
snapshot_download("ostris/FLUX.1-schnell-training-adapter", token=tok)
print("PREDOWNLOAD_DONE", flush=True)
PY
if [ $? -ne 0 ]; then echo "PRE-DOWNLOAD FAILED"; sudo shutdown -h now; exit 1; fi

echo "=== FLUX TRAINING START (warm cache + authed metadata) $(date -u) ==="
# Do NOT use HF_HUB_OFFLINE: diffusers' sharded loader calls model_info() (a network metadata
# call) even when every shard is already cached, and offline mode rejects it. Instead authenticate
# so that metadata call succeeds against the gated repo; the shards themselves load from the
# pre-downloaded cache (metadata-only round-trip, not a re-download).
huggingface-cli login --token "$HF_TOKEN" >/dev/null 2>&1 || python - <<'PY'
import os
from huggingface_hub import login
login(token=os.environ["HF_TOKEN"])
PY
python run.py /home/ec2-user/slm-foundry/packs/nast/hand/flux_lora.yaml
echo "=== FLUX TRAINING EXITED $(date -u) ==="

_IMDS_TOK=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 120")
_IID=$(curl -s -H "X-aws-ec2-metadata-token: $_IMDS_TOK" http://169.254.169.254/latest/meta-data/instance-id)

if ls ~/ai-toolkit/output/nast_flux/*.safetensors >/dev/null 2>&1; then
  echo "=== archiving Flux LoRA -> S3 ==="
  aws s3 cp ~/ai-toolkit/output/nast_flux/ s3://ilyrium-slm-foundry/models/nast/hand/flux/ \
    --recursive --exclude "*" --include "*.safetensors" --only-show-errors && echo "S3_ARCHIVE_OK"
  # SUCCESS: artifacts are in S3 -> TERMINATE (deletes the EBS volume -> $0 storage; rebuild via scripts)
  echo "=== SUCCESS: terminating box (volume -> 0 cost) $(date -u) ==="
  aws ec2 terminate-instances --region us-east-1 --instance-ids "$_IID" || sudo shutdown -h now
else
  # FAILURE: keep the volume so we can restart and debug; just stop (no compute billing)
  echo "=== NO LoRA produced (training failed) -- STOPPING (not terminating) for debug $(date -u) ==="
  sudo shutdown -h now
fi
