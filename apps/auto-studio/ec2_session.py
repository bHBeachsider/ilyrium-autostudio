"""
EC2 GPU workstation lifecycle for the Ilyrium console.

Thin Python layer (boto3) so the console can see and control the AWS GPU box
that hosts ComfyUI (and, later, Unreal). It deliberately does NOT reimplement
the SSH-tunnel / security-group / app-launch dance — that's handled by Brad's
ilyrium-ec2-session PowerShell skill. This module covers what the console
needs at runtime: status, start (so a render isn't blocked on a stopped box),
stop (cost control — the g6.2xlarge bills ~$1.20/hr), and a ComfyUI reachability
check.

Config via env (sensible defaults baked in):
  ILYRIUM_EC2_INSTANCE_ID   default i-04b439af98c8faf5e
  ILYRIUM_EC2_REGION        default us-east-1
  COMFYUI_URL               default http://127.0.0.1:8188  (i.e. through the SSH tunnel)
"""

import os

INSTANCE_ID = os.getenv("ILYRIUM_EC2_INSTANCE_ID", "i-04b439af98c8faf5e")
REGION = os.getenv("ILYRIUM_EC2_REGION", "us-east-1")
# Default to the tunnelled localhost endpoint. Use 127.0.0.1 (not 'localhost') —
# the Windows SSH server resolves localhost to IPv6 and breaks the forward.
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")


def _client():
    import boto3
    return boto3.client("ec2", region_name=REGION)


def status() -> dict:
    """Current instance state + public IP."""
    ec2 = _client()
    r = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
    inst = r["Reservations"][0]["Instances"][0]
    return {
        "instance_id": INSTANCE_ID,
        "region": REGION,
        "state": inst["State"]["Name"],            # pending|running|stopping|stopped|...
        "public_ip": inst.get("PublicIpAddress"),
    }


def ensure_running(wait: bool = True, timeout: int = 300) -> dict:
    """Start the instance if it isn't running; optionally wait until it is."""
    ec2 = _client()
    s = status()
    if s["state"] == "stopping":
        ec2.get_waiter("instance_stopped").wait(InstanceIds=[INSTANCE_ID])
        s = status()
    if s["state"] in ("stopped", "shutting-down"):
        ec2.start_instances(InstanceIds=[INSTANCE_ID])
    if wait:
        ec2.get_waiter("instance_running").wait(
            InstanceIds=[INSTANCE_ID],
            WaiterConfig={"Delay": 10, "MaxAttempts": max(1, timeout // 10)},
        )
    return status()


def stop() -> dict:
    """Stop the instance (cost control). Returns the updated status."""
    ec2 = _client()
    ec2.stop_instances(InstanceIds=[INSTANCE_ID])
    return status()


def is_comfyui_up(url: str = None, timeout: int = 4) -> bool:
    """Reachability probe for ComfyUI (expects the SSH tunnel / endpoint to be live)."""
    import requests
    base = (url or COMFYUI_URL).rstrip("/")
    try:
        r = requests.get(base + "/system_stats", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False
