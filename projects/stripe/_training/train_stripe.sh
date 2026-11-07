#!/usr/bin/env bash
# Train the Stripe character LoRA on the box, archive to S3, stop the box.
#   nohup bash ~/train_stripe.sh </dev/null >~/train_stripe.log 2>&1 & disown
set -uo pipefail

# 1. dataset: images + SHORT trigger captions derived from filenames
mkdir -p ~/stripe_train
cp ~/trainset_out/t*.png ~/stripe_train/
cd ~/stripe_train
for f in t*.png; do
  base="${f%.png}"
  pose=$(echo "$base" | sed -E 's/^t[0-9]+_//; s/_/ /g')
  printf 'strp, %s\n' "$pose" > "${base}.txt"
done
echo "=== dataset: $(ls ~/stripe_train/*.png | wc -l) images ==="

# 2. ensure ai-toolkit (this box has the diffusers env, not ai-toolkit)
if [ ! -d ~/ai-toolkit ]; then
  echo "=== bootstrapping ai-toolkit ==="
  bash ~/bootstrap_vision.sh
fi
source ~/aitk/bin/activate
set -a; . ~/.env; set +a
export HF_HUB_ENABLE_HF_TRANSFER=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
hf auth login --token "$HF_TOKEN" >/dev/null 2>&1 || huggingface-cli login --token "$HF_TOKEN" >/dev/null 2>&1 || true

# 3. train
echo "=== TRAIN stripe_char $(date -u) ==="
cd ~/ai-toolkit
python run.py ~/stripe_flux_char.yaml

# 4. archive
OK=1
if ls ~/ai-toolkit/output/stripe_char/*.safetensors >/dev/null 2>&1; then
  aws s3 cp ~/ai-toolkit/output/stripe_char/ s3://ilyrium-slm-foundry/models/stripe/hand/char/ \
    --recursive --exclude "*" --include "*.safetensors" --include "*.png" --only-show-errors && OK=0
fi
echo "=== TRAIN_DONE OK=$OK $(date -u) ==="
sudo shutdown -h now   # -> STOP (volume persists for validation); no idle billing
