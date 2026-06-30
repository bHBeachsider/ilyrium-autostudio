"""
site_box_client — bridge ilyrium auto-studio → the site-box news site.

Attaches a finished, HITL-RELEASED video (its Cloudflare R2 master) to an existing
site-box article via POST /api/video/attach. It does NOT render (the studio pipeline
does that) and it does NOT bypass the release gate — it refuses to POST a cut whose
release gate did not pass (site-box independently enforces the same with HTTP 422).

Spec: docs/specs/2026-06-30-ilyrium-sitebox-bridge.md

Env:
  SITE_BOX_BASE_URL        site-box deployment, e.g. https://sitebox.build
  SITE_BOX_INGEST_SECRET   == site-box VIDEO_INGEST_SECRET (bearer token)
  R2_PUBLIC_HOST           browser-public R2 host, e.g. https://media.ilyrium.io
  R2_BUCKET                R2 bucket (default ilyrium-assets) — captions upload
  STUDIO_PIPELINE_URL      pipeline service base (default http://127.0.0.1:8800) — `render`

CLI:
  python site_box_client.py render --cluster cluster.json [--mode auto_draft]
  python site_box_client.py attach --project-dir outputs/<campaign> --article-id <id> [--build-captions]
"""

import os
import json
import time
import argparse

import requests

DEFAULT_AI_DISCLOSURE = "AI-generated video — ilyrium auto-studio"
_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
_DETERMINISTIC_FAIL = {400, 401, 404, 422}
_BACKOFF = [1, 4, 16]


class AttachError(RuntimeError):
    """Raised when a video cannot be (or should not be) attached."""


# --------------------------------------------------------------------------- #
# Pure helpers (unit-tested; no network / no boto3)
# --------------------------------------------------------------------------- #
def _cut_release_allowed(cut: dict) -> bool:
    """True if the cut passed the release gate. Accepts the assemble_cut() return
    shape (``release_allowed``) OR a stored project cut (``release.allowed``)."""
    if cut.get("release_allowed") is True:
        return True
    return (cut.get("release") or {}).get("allowed") is True


def _public_manifest_url(campaign_id: str) -> str | None:
    host = os.getenv("R2_PUBLIC_HOST")
    return f"{host.rstrip('/')}/campaigns/{campaign_id}/manifest.json" if host else None


def build_attach_body(
    *,
    campaign_id: str,
    cut: dict,
    article_id: str | None = None,
    slug: str | None = None,
    captions_url: str | None = None,
    poster_url: str | None = None,
    duration_sec: int | None = None,
    ai_disclosure: str = DEFAULT_AI_DISCLOSURE,
) -> dict:
    """Build the POST /api/video/attach request body from a released cut.

    Raises AttachError if no article key is given, the cut did not pass the release
    gate, or it has no public R2 url (defense in depth — site-box enforces the same).
    Top-level fields are the camelCase API contract; ``meta`` is the snake_case
    provenance bag that lands in site-box ``video_meta``.
    """
    if not (article_id or slug):
        raise AttachError("article_id or slug is required")
    if not _cut_release_allowed(cut):
        raise AttachError("cut release gate did not pass — refusing to attach")
    video_url = cut.get("public_url")
    if not video_url:
        raise AttachError("cut has no public_url (not uploaded to R2) — refusing to attach")

    cut_id = cut.get("cut_id")
    rel = cut.get("release") or {}
    body: dict = {
        "videoUrl": video_url,
        "posterUrl": poster_url,
        "captionsUrl": captions_url,
        "durationSec": duration_sec,
        "idempotencyKey": f"{campaign_id}:{cut_id}",
        "meta": {
            "campaign_id": campaign_id,
            "cut_id": cut_id,
            "manifest_url": _public_manifest_url(campaign_id),
            "checksum": rel.get("checksum"),
            "ai_disclosure": ai_disclosure,
            "release": {
                "published": rel.get("published", bool(cut.get("published"))),
                "allowed": True,
                "enforced": rel.get("enforced"),
                "qa_passed": rel.get("qa_passed"),
                "blockers": rel.get("blockers", []),
            },
        },
    }
    if article_id:
        body["articleId"] = article_id
    if slug:
        body["slug"] = slug
    return body


def _should_retry(status: int | None) -> bool:
    """Retry on network errors (status None) and transient HTTP (408/429/5xx)."""
    return status is None or status in _RETRYABLE_STATUS


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #
def post_attach(
    body: dict,
    *,
    base_url: str | None = None,
    secret: str | None = None,
    attempts: int = 3,
    _sleep=time.sleep,
) -> dict:
    """POST the body to {base}/api/video/attach with bounded exponential backoff
    (max ``attempts``, only 408/429/5xx/network). Returns the parsed JSON on 200.
    Raises AttachError on a deterministic failure (400/401/404/422) or after retries."""
    base_url = base_url or os.getenv("SITE_BOX_BASE_URL")
    secret = secret or os.getenv("SITE_BOX_INGEST_SECRET")
    if not base_url:
        raise AttachError("SITE_BOX_BASE_URL is not set")
    if not secret:
        raise AttachError("SITE_BOX_INGEST_SECRET is not set")
    url = f"{base_url.rstrip('/')}/api/video/attach"
    headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}

    last_err: AttachError | None = None
    for i in range(attempts):
        status: int | None = None
        try:
            resp = requests.post(url, json=body, headers=headers, timeout=30)
            status = resp.status_code
            if status == 200:
                return resp.json()
            if status in _DETERMINISTIC_FAIL:
                raise AttachError(f"attach failed {status}: {resp.text[:300]}")
            last_err = AttachError(f"attach failed {status}: {resp.text[:300]}")
        except requests.RequestException as e:
            last_err, status = AttachError(f"network error: {e}"), None
        if i < attempts - 1 and _should_retry(status):
            _sleep(_BACKOFF[min(i, len(_BACKOFF) - 1)])
        else:
            break
    raise last_err or AttachError("attach failed")


def attach_video_to_article(
    *,
    campaign_id: str,
    cut: dict,
    article_id: str | None = None,
    slug: str | None = None,
    captions_url: str | None = None,
    poster_url: str | None = None,
    duration_sec: int | None = None,
    ai_disclosure: str = DEFAULT_AI_DISCLOSURE,
    base_url: str | None = None,
    secret: str | None = None,
) -> dict:
    """Guard + build + POST. The one call P4 (webhook) makes on stage-8 success."""
    body = build_attach_body(
        campaign_id=campaign_id, cut=cut, article_id=article_id, slug=slug,
        captions_url=captions_url, poster_url=poster_url, duration_sec=duration_sec,
        ai_disclosure=ai_disclosure,
    )
    return post_attach(body, base_url=base_url, secret=secret)


def upload_captions_to_r2(campaign_id: str, vtt_path: str) -> str:
    """Upload a .vtt to R2 under campaigns/{id}/captions.vtt; return its public URL.
    Same public host as the video so the <track> stays same-origin (spec D7)."""
    host = os.getenv("R2_PUBLIC_HOST")
    if not host:
        raise AttachError("R2_PUBLIC_HOST is not set — cannot build a public captions URL")
    from utils.storage_manager import get_r2_client  # lazy: keep boto3 out of import path

    bucket = os.getenv("R2_BUCKET", "ilyrium-assets")
    key = f"campaigns/{campaign_id}/captions.vtt"
    get_r2_client().upload_file(vtt_path, bucket, key, ExtraArgs={"ContentType": "text/vtt"})
    return f"{host.rstrip('/')}/{key}"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _load_cluster(args) -> dict:
    if args.cluster:
        with open(args.cluster, encoding="utf-8") as f:
            return json.load(f)
    return {
        "id": args.article_id, "article_id": args.article_id, "slug": args.slug,
        "title": args.title, "summary": args.summary or "",
        "topic": args.topic, "county": args.county,
    }


def _brief_from_cluster(c: dict) -> str:
    bits = [f"Title: {c.get('title', '')}"]
    if c.get("summary"):
        bits.append(f"Summary: {c['summary']}")
    if c.get("topic"):
        bits.append(f"Topic: {c['topic']}")
    if c.get("county"):
        bits.append(f"County: {c['county']}")
    bits.append(
        "Produce a 45-90s explainer news video for the article above for a "
        "construction-industry audience. Hook first, clear takeaway, no AI slop."
    )
    return "\n".join(bits)


def _cmd_render(args) -> None:
    cluster = _load_cluster(args)
    if not cluster.get("title"):
        raise SystemExit("render: a cluster --title (or --cluster file with a title) is required")
    base = os.getenv("STUDIO_PIPELINE_URL", "http://127.0.0.1:8800").rstrip("/")
    resp = requests.post(
        f"{base}/pipeline/start",
        json={"prompt": _brief_from_cluster(cluster), "mode": args.mode},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    print(json.dumps(
        {"run_id": data.get("run_id"),
         "article_id": cluster.get("article_id") or cluster.get("id"),
         "slug": cluster.get("slug")}, indent=2))
    print(
        "\nNext: approve the release gate (stage 7) in the studio console, then run "
        "`attach --project-dir outputs/<campaign>` to publish the released cut.",
    )


def _cmd_attach(args) -> None:
    if not (args.article_id or args.slug):
        raise SystemExit("attach: --article-id or --slug is required")
    import project_store as ps  # lazy: flat sibling module

    project = ps.load_project(args.project_dir)
    if not project:
        raise SystemExit(f"attach: no project.json in {args.project_dir}")
    campaign_id = project["campaign_id"]
    if args.cut_id:
        cut = next((c for c in project.get("cuts", []) if c.get("cut_id") == args.cut_id), None)
    else:
        cut = ps.latest_cut(project)
    if not cut:
        raise SystemExit("attach: no cut found in project")

    captions_url = args.captions_url
    if args.build_captions:
        import delivery  # lazy
        caps = delivery.build_captions(project, args.project_dir)
        captions_url = upload_captions_to_r2(campaign_id, caps["vtt"])

    result = attach_video_to_article(
        campaign_id=campaign_id, cut=cut,
        article_id=args.article_id, slug=args.slug,
        captions_url=captions_url, poster_url=args.poster_url,
        duration_sec=args.duration_sec,
    )
    print(json.dumps(result, indent=2))


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="site_box_client", description="ilyrium → site-box video bridge")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render", help="start a studio pipeline run from a cluster (HITL release still required)")
    r.add_argument("--cluster", help="path to a cluster JSON file ({title, summary, topic, county, article_id|slug})")
    r.add_argument("--article-id")
    r.add_argument("--slug")
    r.add_argument("--title")
    r.add_argument("--summary")
    r.add_argument("--topic")
    r.add_argument("--county")
    r.add_argument("--mode", default="auto_draft", help="manual | assisted | auto_draft (default)")
    r.set_defaults(fn=_cmd_render)

    a = sub.add_parser("attach", help="attach a released cut's R2 video to a site-box article")
    a.add_argument("--project-dir", required=True, help="outputs/<campaign_id>")
    a.add_argument("--article-id")
    a.add_argument("--slug")
    a.add_argument("--cut-id", help="default: the latest cut")
    a.add_argument("--poster-url")
    a.add_argument("--captions-url")
    a.add_argument("--duration-sec", type=int)
    a.add_argument("--build-captions", action="store_true", help="build + upload the .vtt, then attach")
    a.set_defaults(fn=_cmd_attach)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
