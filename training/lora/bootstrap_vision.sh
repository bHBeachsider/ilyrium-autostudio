#!/usr/bin/env bash
# Vision-LoRA training stack: ai-toolkit (ostris) handles BOTH SDXL and Flux LoRA training
# from one config-driven tool. Run once per box:  bash infra/bootstrap_vision.sh
set -e
echo "=== deps ==="
sudo dnf install -y git python3.11 python3.11-devel gcc-c++ >/dev/null 2>&1 || true

echo "=== clone ai-toolkit ==="
[ -d ~/ai-toolkit ] || git clone https://github.com/ostris/ai-toolkit ~/ai-toolkit
cd ~/ai-toolkit
git pull --ff-only 2>/dev/null || true
git submodule update --init --recursive 2>/dev/null || true

echo "=== venv + torch (cu124, matches L4 driver) ==="
python3.11 -m venv ~/aitk
source ~/aitk/bin/activate
python -m pip install --upgrade pip wheel
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt

echo "=== verify GPU ==="
python -c "import torch; print('CUDA:', torch.cuda.is_available(), '|', torch.cuda.get_device_name(0))"
echo "=== ai-toolkit ready (activate with: source ~/aitk/bin/activate) ==="
