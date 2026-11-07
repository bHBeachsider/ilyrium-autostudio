#!/usr/bin/env bash
# Lean diffusers env for the satirist Flux smoke test (no ai-toolkit needed).
set -e
sudo dnf install -y python3.11 python3.11-devel gcc-c++ >/dev/null 2>&1 || true
python3.11 -m venv ~/senv
source ~/senv/bin/activate
pip install -q --upgrade pip wheel
pip install -q torch torchvision --index-url https://download.pytorch.org/whl/cu124
pip install -q diffusers transformers accelerate sentencepiece protobuf peft safetensors huggingface_hub
python -c "import torch; print('CUDA', torch.cuda.is_available(), torch.cuda.get_device_name(0))"
echo BOOTSTRAP_DONE
