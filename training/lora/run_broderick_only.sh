#!/usr/bin/env bash
# Nast Flux is already trained + archived to S3. Run ONLY the Broderick Flux-dev LoRA, then
# finalize: terminate on success (volume -> $0), stop on failure (debug). The Broderick wrapper
# frees the schnell cache first and sends the Telegram/SES alert on every exit path (trap).
#
# Launch detached:
#   nohup bash ~/slm-foundry/packs/run_broderick_only.sh </dev/null >~/queue_train.log 2>&1 & disown
set -uo pipefail
echo "######## BRODERICK-ONLY START $(date -u) ########"

bash ~/slm-foundry/packs/broderick/hand/train_broderick_flux.sh
BROD=$?
echo "######## BRODERICK done exit=$BROD $(date -u) ########"

_TOK=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 120")
_IID=$(curl -s -H "X-aws-ec2-metadata-token: $_TOK" http://169.254.169.254/latest/meta-data/instance-id)

if [ "$BROD" -eq 0 ]; then
  echo "######## BRODERICK OK -> TERMINATE (volume -> 0 cost) $(date -u) ########"
  aws ec2 terminate-instances --region us-east-1 --instance-ids "$_IID" || sudo shutdown -h now
else
  echo "######## BRODERICK FAILED -> STOP for debug $(date -u) ########"
  sudo shutdown -h now
fi
