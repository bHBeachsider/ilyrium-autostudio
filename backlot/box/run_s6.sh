#!/bin/bash
# box session 6: the actor fix (ovoid head) on the office x10, plus LYSTERIA office x5 and boardroom x5 - interiors, "soft" control
set -u
cd ~/nh
export COMFY_SERVER=http://127.0.0.1:8188
P=~/nh/backlot/usd/nh/passes_s6
O=~/nh/renders/keyframes_s6
mkdir -p $O
echo "[s6] start $(date +%T)"
python3 backlot/generation/generate_keyframe.py S101_SH004 --seq NH-S101 --passes $P --out $O --takes 10 --seed 6000 \
  --cn-strength 0.6 --cn-end 0.8 --edge-strength 0.2 --edge-end 0.4 2>&1 | grep -E "^\[OK\]|^\[FAIL\]|Error"
echo "[s6] office done $(date +%T)"
python3 backlot/generation/generate_keyframe.py LYST_DESK LYST_BOARD --seq NH-LYST --passes $P --out $O --takes 5 --seed 6100 \
  --cn-strength 0.6 --cn-end 0.8 --edge-strength 0.2 --edge-end 0.4 2>&1 | grep -E "^\[OK\]|^\[FAIL\]|Error"
echo "[s6] lysteria done $(date +%T)"
echo "[s6] segmenting"
~/ComfyUI/venv/bin/python backlot/gate/seg_box.py $O/S101_SH004/take_*.png $O/LYST_DESK/take_*.png $O/LYST_BOARD/take_*.png --passes-root $P 2>&1 | grep -E "^\[OK\]|Error|Traceback" | tail -25
echo "[s6] all done $(date +%T)"
touch $O/DONE
