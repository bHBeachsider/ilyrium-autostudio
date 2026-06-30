import os
import json
import boto3
from datetime import datetime
from botocore.config import Config

def get_r2_client():
    """Initializes the S3 client tailored for Cloudflare R2."""
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("R2_ENDPOINT"),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4")
    )

def setup_campaign_directory(business_name: str) -> tuple[str, str]:
    """Creates a local timestamped directory for the run and returns its path and ID."""
    clean_name = "".join(c for c in business_name if c.isalnum() or c in (" ", "_", "-")).rstrip().replace(" ", "_").lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    campaign_id = f"{clean_name}_{timestamp}"
    
    local_dir = os.path.join("outputs", campaign_id)
    os.makedirs(local_dir, exist_ok=True)
    return local_dir, campaign_id

def finalize_and_upload_campaign(local_dir: str, campaign_id: str, metadata: dict, final_video_path: str):
    """Generates a sidecar metadata manifest and uploads files to Cloudflare R2."""
    bucket_name = os.getenv("R2_BUCKET", "ilyrium-assets")
    manifest_path = os.path.join(local_dir, "manifest.json")
    
    # 1. Save local JSON manifest metadata sidecar
    metadata["generated_at"] = datetime.utcnow().isoformat() + "Z"
    metadata["campaign_id"] = campaign_id
    with open(manifest_path, "w") as f:
        json.dump(metadata, f, indent=4)
        
    print(f"\n📦 [STORAGE] Local artifacts organized in: {local_dir}")
    
    # 2. Upload to Cloudflare R2
    try:
        r2 = get_r2_client()
        
        # Define cloud paths (keys)
        video_key = f"campaigns/{campaign_id}/final_commercial.mp4"
        manifest_key = f"campaigns/{campaign_id}/manifest.json"
        
        print(f"☁️ [STORAGE] Uploading master video to R2 bucket '{bucket_name}'...")
        r2.upload_file(final_video_path, bucket_name, video_key, ExtraArgs={"ContentType": "video/mp4"})
        
        print(f"☁️ [STORAGE] Uploading metadata manifest to R2...")
        r2.upload_file(manifest_path, bucket_name, manifest_key, ExtraArgs={"ContentType": "application/json"})
        
        print("✅ [STORAGE] R2 Synchronization complete!")
        
        # Public delivery URL. Prefer a browser-public custom domain bound to the bucket in
        # Cloudflare (R2_PUBLIC_HOST, e.g. https://media.ilyrium.io). The S3 API endpoint
        # (R2_ENDPOINT) is NOT publicly fetchable and will 403 on a direct browser GET, so it
        # cannot be embedded in a <video> tag. See docs/specs/2026-06-30-ilyrium-sitebox-bridge.md (D1).
        public_host = os.getenv("R2_PUBLIC_HOST")
        if public_host:
            # A custom/managed R2 domain maps to the bucket root: the path is just the object key.
            public_url = f"{public_host.rstrip('/')}/{video_key}"
        else:
            # Legacy fallback (NOT browser-public; 403 on direct GET) — kept for back-compat.
            public_url = f"{os.getenv('R2_ENDPOINT')}/{bucket_name}/{video_key}"
        return public_url

    except Exception as e:
        print(f"❌ [STORAGE] Cloudflare R2 upload failed: {e}")
        return None