#!/usr/bin/env bash
# strp v2 retrain on the clean speedo set. Caption -> bootstrap ai-toolkit (if needed) -> train.
# No S3 archive (this box has no S3 creds) — LoRA left on disk for scp.
#   nohup bash ~/build_stripe_v2.sh </dev/null >~/build_v2.log 2>&1 & disown
set -uo pipefail
cd ~

echo "=== caption (short trigger) $(date -u) ==="
cd ~/stripe_train_v2
for f in *.png *.jpg; do
  [ -e "$f" ] || continue
  base="${f%.*}"
  pose=$(echo "$base" | sed -E 's/_speedo2//; s/^ts[0-9]+_//; s/^userref_//; s/_/ /g')
  printf 'strp, %s\n' "$pose" > "${base}.txt"
done
echo "dataset=$(ls ~/stripe_train_v2/*.png ~/stripe_train_v2/*.jpg 2>/dev/null | wc -l) images"
cd ~

echo "=== ensure ai-toolkit $(date -u) ==="
[ -d ~/ai-toolkit ] || bash ~/bootstrap_vision.sh
rm -rf ~/ai-toolkit/output/stripe_char_v2
source ~/aitk/bin/activate
set -a; . ~/.env; set +a
export HF_HUB_ENABLE_HF_TRANSFER=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
hf auth login --token "$HF_TOKEN" >/dev/null 2>&1 || huggingface-cli login --token "$HF_TOKEN" >/dev/null 2>&1 || true

echo "=== train stripe_char_v2 $(date -u) ==="
cd ~/ai-toolkit
python run.py ~/stripe_flux_char_v2.yaml
echo "=== STRIPE_V2_TRAIN_DONE $(date -u) ==="
