#!/usr/bin/env bash
# Training QUEUE: run the Nast Flux LoRA, then the Broderick Flux-dev LoRA, archive each to S3,
# then finalize the box ONCE. Both train on the same L40S (no rebuild between). On full success
# the box TERMINATES (volume -> $0). If either job fails, the box STOPS (not terminates) so the
# failing job can be debugged without re-provisioning.
#
# Launch detached:
#   nohup bash ~/slm-foundry/packs/run_queue.sh </dev/null >~/queue_train.log 2>&1 & disown
set -uo pipefail
echo "######## QUEUE START $(date -u) ########"

bash ~/slm-foundry/packs/nast/hand/train_nast_flux.sh
NAST=$?
echo "######## NAST done exit=$NAST $(date -u) ########"

bash ~/slm-foundry/packs/broderick/hand/train_broderick_flux.sh
BROD=$?
echo "######## BRODERICK done exit=$BROD $(date -u) ########"

_TOK=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 120")
_IID=$(curl -s -H "X-aws-ec2-metadata-token: $_TOK" http://169.254.169.254/latest/meta-data/instance-id)

if [ "$NAST" -eq 0 ] && [ "$BROD" -eq 0 ]; then
  echo "######## BOTH OK -> TERMINATE (volume -> 0 cost) $(date -u) ########"
  aws ec2 terminate-instances --region us-east-1 --instance-ids "$_IID" || sudo shutdown -h now
else
  echo "######## FAILURE (nast=$NAST brod=$BROD) -> STOP for debug $(date -u) ########"
  sudo shutdown -h now
fi
