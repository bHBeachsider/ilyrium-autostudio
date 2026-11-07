#!/usr/bin/env bash
# Deploy trained nast-brain: merge -> llama.cpp GGUF (q4_k_m) -> Ollama import -> test.
# Run on the EC2 box:  bash packs/nast/brain/deploy_box.sh
#
# WHY llama.cpp (not Ollama's safetensors import): Ollama's built-in converter does NOT support
# "Qwen3ForCausalLM" safetensors (it can RUN Qwen3 GGUFs, just not CONVERT them). llama.cpp's
# convert_hf_to_gguf.py does support Qwen3, and Ollama can import a finished GGUF for any arch.
set -e
cd ~/slm-foundry
source ~/slm/bin/activate
MERGED=outputs/nast-brain/merged
F16=outputs/nast-brain/nast-f16.gguf
Q4=outputs/nast-brain/nast-q4_k_m.gguf

echo "=== 1/5 merge LoRA adapter -> 16-bit (skip if exists) ==="
if [ ! -d "$MERGED" ]; then
  python -c "from unsloth import FastLanguageModel as F; m,t=F.from_pretrained('outputs/nast-brain/lora_adapter',load_in_4bit=True,max_seq_length=2048); m.save_pretrained_merged('$MERGED',t,save_method='merged_16bit')"
else echo "  $MERGED exists -- skipping"; fi

echo "=== 2/5 build llama.cpp (quantize tool) if missing ==="
if [ ! -f ~/llama.cpp/build/bin/llama-quantize ]; then
  sudo dnf install -y cmake gcc-c++ >/dev/null 2>&1
  [ -d ~/llama.cpp ] || git clone --depth 1 https://github.com/ggerganov/llama.cpp ~/llama.cpp
  cmake -S ~/llama.cpp -B ~/llama.cpp/build -DLLAMA_CURL=OFF >/dev/null
  cmake --build ~/llama.cpp/build --config Release -j --target llama-quantize >/dev/null
fi
pip install -q gguf protobuf sentencepiece 2>/dev/null || true

echo "=== 3/5 convert merged -> f16 GGUF (skip if exists) ==="
[ -f "$F16" ] || python ~/llama.cpp/convert_hf_to_gguf.py "$MERGED" --outfile "$F16" --outtype f16

echo "=== 4/5 quantize -> q4_k_m (skip if exists) ==="
[ -f "$Q4" ] || ~/llama.cpp/build/bin/llama-quantize "$F16" "$Q4" Q4_K_M
ls -lh outputs/nast-brain/*.gguf

echo "=== 5/5 Ollama import (from GGUF) + test ==="
# Pin the ChatML template + stop token to MATCH the unsloth qwen-2.5 training template.
# Relying on the GGUF's embedded template caused schema drift + rambling (no stop).
cat > /tmp/Modelfile.nast <<'EOF'
FROM /home/ec2-user/slm-foundry/outputs/nast-brain/nast-q4_k_m.gguf
TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|im_start|>"
PARAMETER temperature 0.3
SYSTEM """You are Thomas Nast, the 19th-century political cartoonist. Given a modern event, respond with JSON {"allegory_rationale": str, "image_prompt": str} describing the satirical cartoon you would draw, in your Harper's Weekly wood-engraving idiom."""
EOF
ollama create nast-brain -f /tmp/Modelfile.nast
echo "--- TEST 1 ---"; ollama run nast-brain "Event: A tech monopoly quietly buys all its rivals to control the market."
echo "--- TEST 2 ---"; ollama run nast-brain "Event: A mayor funnels city contracts to cronies while cutting school budgets."
echo "=== DEPLOY DONE ==="
