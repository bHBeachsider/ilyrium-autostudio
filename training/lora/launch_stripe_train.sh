#!/usr/bin/env bash
# Resume-when-back-up launcher for the Stripe Flux LoRA.
#
# Legacy Flux-only entry point, not the bounded Qwen session controller.
# Supply an independently verified Linux G6E instance ID. No stale default IDs.
# This script makes bounded capacity-only retries, then scps the train config +
# self-shutdown wrapper to the box and launches training DETACHED. The trainset itself is
# already in S3 (the wrapper pulls it), and the wrapper archives the LoRA to S3 and
# terminates the box on success — so once this script reports "launched", you can walk away.
#
# Run from Git Bash:  bash infra/launch_stripe_train.sh
#
# Pure-AWS start is reliable; the scp/ssh launch assumes the box is the Amazon-Linux
# ai-toolkit box (ec2-user, ~/ai-toolkit, venv ~/aitk) used for the prior Flux LoRAs. If the
# ssh step fails, the script prints the exact manual commands to finish by hand.
set -u
REGION=us-east-1
G6E=${G6E:-}
KEY="C:/Users/bradu/Documents/ilyrium-autostudio/slm-foundry-key-v2.pem"
HERE="$(cd "$(dirname "$0")/../.." && pwd)"   # ilyrium-autostudio root (relocated from slm-foundry/infra)
INTERVAL=${INTERVAL:-120}                  # seconds between capacity retries
MAX_ATTEMPTS=${MAX_ATTEMPTS:-1}
export AWS_MAX_ATTEMPTS=1 AWS_RETRY_MODE=standard AWS_PAGER=""
if [[ ! "$G6E" =~ ^i-[0-9a-f]{8,17}$ ]] || [[ "${ALLOW_G6:-0}" != 0 ]]; then
  echo 'Supply G6E for a verified Linux Flux host. Windows fallback is unsupported.' >&2
  exit 2
fi
if [[ ! "$MAX_ATTEMPTS" =~ ^[1-3]$ ]] || [[ ! "$INTERVAL" =~ ^[0-9]{1,3}$ ]] ||
   (( 10#$INTERVAL < 1 || 10#$INTERVAL > 300 )); then
  echo 'Require MAX_ATTEMPTS=1..3 and INTERVAL=1..300 seconds.' >&2
  exit 2
fi

try_start() {  # echoes the instance id if it entered pending/running, else nothing
  local id=$1
  local out
  local status=0 code
  out=$(aws ec2 start-instances --region "$REGION" --instance-ids "$id" \
        --query "StartingInstances[].CurrentState.Name" --output text 2>&1) || status=$?
  out=${out//$'\r'/}
  if (( status == 0 )); then
    if [[ "$out" == pending || "$out" == running ]]; then echo "$id"; return 0; fi
    echo 'Unexpected start response; reconcile instance state before any retry.' >&2
    return 76
  fi
  if [[ "$out" =~ An\ error\ occurred\ \(([A-Za-z0-9_.]+)\)\ when\ calling ]]; then
    code=${BASH_REMATCH[1]}
    case "$code" in
      InsufficientInstanceCapacity|Server.InsufficientInstanceCapacity) return 75 ;;
      InvalidInstanceID.*|*VcpuLimitExceeded|*InstanceLimitExceeded|*UnauthorizedOperation|*AuthFailure|*ExpiredToken*)
        printf 'Start refused (%s); no retry.\n' "$code" >&2; return 2 ;;
    esac
  fi
  echo 'Unclassified start failure; reconcile instance state before any retry.' >&2
  return 76
}

echo "Trying the explicit Flux host; at most ${MAX_ATTEMPTS} capacity attempts."
INSTANCE=""
for (( attempt=1; attempt<=MAX_ATTEMPTS; attempt++ )); do
  if INSTANCE=$(try_start "$G6E"); then break; else status=$?; fi
  if (( status != 75 )); then exit "$status"; fi
  if (( attempt == MAX_ATTEMPTS )); then
    echo 'Capacity unavailable; attempt limit reached. No training started.' >&2
    exit 75
  fi
  echo "Capacity unavailable; retry ${attempt}/${MAX_ATTEMPTS} after ${INTERVAL}s."
  sleep "$INTERVAL"
done
echo "Capacity! starting instance $INSTANCE"

aws ec2 wait instance-running --region "$REGION" --instance-ids "$INSTANCE"
IP=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$INSTANCE" \
     --query "Reservations[0].Instances[0].PublicIpAddress" --output text)
echo "Instance running at $IP — waiting for SSH…"
for _ in $(seq 1 30); do
  if ssh -i "$KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
       -o ConnectTimeout=10 "ec2-user@$IP" 'echo ok' >/dev/null 2>&1; then break; fi
  sleep 10
done

SSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new ec2-user@$IP"
SCP="scp -i $KEY -o StrictHostKeyChecking=accept-new"
echo "Staging train config + wrapper to box…"
$SSH 'mkdir -p ~/slm-foundry/packs/stripe' \
  && $SCP "$HERE/projects/stripe/_training/stripe_flux_char_v7_nb.yaml" "ec2-user@$IP:~/slm-foundry/packs/stripe/" \
  && $SCP "$HERE/projects/stripe/_training/run_stripe_and_finalize.sh" "ec2-user@$IP:~/slm-foundry/packs/stripe/" \
  && $SSH 'chmod +x ~/slm-foundry/packs/stripe/run_stripe_and_finalize.sh
           nohup bash ~/slm-foundry/packs/stripe/run_stripe_and_finalize.sh </dev/null >~/stripe_train.log 2>&1 & disown
           sleep 2; echo LAUNCHED; tail -n 3 ~/stripe_train.log 2>/dev/null'

if [ $? -eq 0 ]; then
  echo
  echo "✅ Training launched DETACHED on $INSTANCE ($IP). Safe to close/walk away."
  echo "   Watch:   ssh -i $KEY ec2-user@$IP 'tail -f ~/stripe_train.log'"
  echo "   Result:  aws s3 ls s3://ilyrium-slm-foundry/models/stripe/char/flux_v7_nb/"
  echo "   The box self-terminates on success."
else
  echo
  echo "⚠️  SSH launch step failed. The box IS running at $IP. Finish by hand:"
  echo "   $SCP $HERE/projects/stripe/_training/stripe_flux_char_v7_nb.yaml ec2-user@$IP:~/slm-foundry/packs/stripe/"
  echo "   $SCP $HERE/projects/stripe/_training/run_stripe_and_finalize.sh ec2-user@$IP:~/slm-foundry/packs/stripe/"
  echo "   $SSH 'nohup bash ~/slm-foundry/packs/stripe/run_stripe_and_finalize.sh </dev/null >~/stripe_train.log 2>&1 & disown'"
  echo "   (Verify the box user/paths — it must be the ai-toolkit box: ~/ai-toolkit + venv ~/aitk.)"
fi
