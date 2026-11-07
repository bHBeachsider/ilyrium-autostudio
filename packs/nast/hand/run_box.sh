#!/usr/bin/env bash
# Generic ai-toolkit training launcher on the box. Pass a config path as $1.
# Detached:  nohup bash ~/slm-foundry/packs/nast/hand/run_box.sh <config> </dev/null >~/<log> 2>&1 & disown
cd ~/ai-toolkit
source ~/aitk/bin/activate
set -a; . ~/slm-foundry/.env; set +a       # HF_TOKEN + OPENROUTER_API_KEY
export HF_HUB_ENABLE_HF_TRANSFER=1
exec python run.py "$1"
