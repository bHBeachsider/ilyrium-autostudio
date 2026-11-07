#!/usr/bin/env bash
# Launch the Nast Flux-schnell LoRA training on the box (ai-toolkit).
# Use detached:  nohup bash ~/slm-foundry/packs/nast/hand/run_flux_box.sh </dev/null >~/flux_train.log 2>&1 & disown
cd ~/ai-toolkit
source ~/aitk/bin/activate
set -a; . ~/slm-foundry/.env; set +a       # HF_TOKEN + OPENROUTER_API_KEY
export HF_HUB_ENABLE_HF_TRANSFER=1
exec python run.py /home/ec2-user/slm-foundry/packs/nast/hand/flux_lora.yaml
