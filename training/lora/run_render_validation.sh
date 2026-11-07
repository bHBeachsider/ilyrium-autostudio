#!/usr/bin/env bash
# Render validation samples from the trained Flux Hand LoRAs (Broderick dev + Nast schnell),
# archive the PNGs to S3, then finalize. Broderick is the priority (never visually validated).
# Launch detached: nohup bash ~/slm-foundry/packs/run_render_validation.sh </dev/null >~/render.log 2>&1 & disown
set -uo pipefail
source ~/aitk/bin/activate 2>/dev/null || true
set -a; . ~/slm-foundry/.env; set +a
export HF_HUB_ENABLE_HF_TRANSFER=1 HF_HUB_DISABLE_XET=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
hf auth login --token "$HF_TOKEN" >/dev/null 2>&1 || huggingface-cli login --token "$HF_TOKEN" >/dev/null 2>&1 || true
python -c "import diffusers" 2>/dev/null || pip install -q diffusers transformers accelerate sentencepiece protobuf

mkdir -p ~/loras ~/render_out/broderick ~/render_out/nast
aws s3 cp s3://ilyrium-slm-foundry/models/broderick/hand/flux/broderick_flux.safetensors ~/loras/broderick_flux.safetensors --only-show-errors
aws s3 cp s3://ilyrium-slm-foundry/models/nast/hand/flux/nast_flux.safetensors ~/loras/nast_flux.safetensors --only-show-errors

cat > ~/broderick_prompts.txt <<'EOF'
brdrck style, two men arguing at an office desk, one holding a phone, white void background
brdrck style, a dog leaping at a child in a suburban yard
brdrck style, a man dancing alone, single red accent
brdrck style, a deadpan office worker staring at a ringing phone over a torn ledger
EOF
cat > ~/nast_prompts.txt <<'EOF'
thomas_nast_style a powerful senator depicted as a giant octopus labeled MONOPOLY strangling city hall
thomas_nast_style the Tammany tiger loose in a ruined Roman arena over a fallen woman labeled THE REPUBLIC
thomas_nast_style a corrupt political boss with a money bag for a head and top hat over a torn ledger
EOF

echo "=== RENDER Broderick (FLUX.1-dev) $(date -u) ==="
python ~/slm-foundry/packs/render_samples.py --base black-forest-labs/FLUX.1-dev \
  --lora ~/loras/broderick_flux.safetensors --prompts ~/broderick_prompts.txt \
  --out ~/render_out/broderick --steps 28 --guidance 3.5
echo "=== RENDER Nast (FLUX.1-schnell) $(date -u) ==="
python ~/slm-foundry/packs/render_samples.py --base black-forest-labs/FLUX.1-schnell \
  --lora ~/loras/nast_flux.safetensors --prompts ~/nast_prompts.txt \
  --out ~/render_out/nast --steps 4 --guidance 1.0

B=$(ls ~/render_out/broderick/*.png 2>/dev/null | wc -l)
N=$(ls ~/render_out/nast/*.png 2>/dev/null | wc -l)
echo "=== rendered: broderick=$B nast=$N $(date -u) ==="
aws s3 cp ~/render_out/broderick/ s3://ilyrium-slm-foundry/models/broderick/hand/flux/samples/ --recursive --include "*.png" --only-show-errors
aws s3 cp ~/render_out/nast/ s3://ilyrium-slm-foundry/models/nast/hand/flux/samples/ --recursive --include "*.png" --only-show-errors

# telegram alert (token in .env if present)
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  curl -s -m 20 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=🖼️ Hand-LoRA validation renders done: broderick=$B nast=$N -> s3://ilyrium-slm-foundry/models/*/hand/flux/samples/. Box finalizing." >/dev/null 2>&1 || true
fi

_TOK=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 120")
_IID=$(curl -s -H "X-aws-ec2-metadata-token: $_TOK" http://169.254.169.254/latest/meta-data/instance-id)
if [ "$B" -ge 1 ]; then
  echo "=== SUCCESS -> terminate $(date -u) ==="
  aws ec2 terminate-instances --region us-east-1 --instance-ids "$_IID" || sudo shutdown -h now
else
  echo "=== render produced nothing -> stop for debug $(date -u) ==="
  sudo shutdown -h now
fi
