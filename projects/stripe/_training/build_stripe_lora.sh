#!/usr/bin/env bash
# Full Stripe char-LoRA build: render 18-shot trainset (v6 recipe) -> caption -> train -> archive -> stop.
#   nohup bash ~/build_stripe_lora.sh </dev/null >~/build_stripe.log 2>&1 & disown
set -uo pipefail
cd ~

echo "=== [1/4] render 18-shot trainset (senv/diffusers) $(date -u) ==="
source ~/senv/bin/activate
set -a; . ~/.env; set +a
export HUGGINGFACE_HUB_TOKEN=$HF_TOKEN PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
rm -f ~/trainset_out/*.png
python ~/render_trainset.py
echo "trainset=$(ls ~/trainset_out/*.png 2>/dev/null | wc -l)"
deactivate || true

echo "=== [2/4] build dataset + short trigger captions ==="
rm -rf ~/stripe_train; mkdir -p ~/stripe_train
cp ~/trainset_out/t*.png ~/stripe_train/
cd ~/stripe_train
for f in t*.png; do
  base="${f%.png}"; pose=$(echo "$base" | sed -E 's/^t[0-9]+_//; s/_/ /g')
  printf 'strp, %s\n' "$pose" > "${base}.txt"
done
echo "dataset=$(ls ~/stripe_train/*.png | wc -l) images"
cd ~

echo "=== [3/4] train stripe_char (ai-toolkit) $(date -u) ==="
[ -d ~/ai-toolkit ] || bash ~/bootstrap_vision.sh
rm -rf ~/ai-toolkit/output/stripe_char
source ~/aitk/bin/activate
set -a; . ~/.env; set +a
export HF_HUB_ENABLE_HF_TRANSFER=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
hf auth login --token "$HF_TOKEN" >/dev/null 2>&1 || huggingface-cli login --token "$HF_TOKEN" >/dev/null 2>&1 || true
cd ~/ai-toolkit
python run.py ~/stripe_flux_char.yaml

echo "=== [4/4] archive -> S3 ==="
OK=1
if ls ~/ai-toolkit/output/stripe_char/*.safetensors >/dev/null 2>&1; then
  aws s3 cp ~/ai-toolkit/output/stripe_char/ s3://ilyrium-slm-foundry/models/stripe/hand/char/ \
    --recursive --exclude "*" --include "*.safetensors" --include "*.png" --only-show-errors && OK=0
fi
echo "=== STRIPE_LORA_DONE OK=$OK $(date -u) ==="
sudo shutdown -h now   # -> STOP (volume kept for validation render)
