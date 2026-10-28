// apps/control-panel/app/api/webhooks/fal/route.ts
// Receives async completion/failure callbacks from fal.ai.
// Validates HMAC-SHA256 signature (x-fal-signature: sha256=<hex>).
// On completed: notifies local pipeline service + persists the asset.
// On failed:    records in the in-memory failedJobs store.

import { NextResponse } from "next/server";
import crypto from "crypto";
import { pendingJobs, failedJobs, appendLedgerEntry, FailedJob } from "../../../../lib/adapters/falAdapter";
import { createAssetWithRights, getOrCreateProject } from "../../../../lib/studio-writes";
import studioDb from "../../../../lib/studio-db";

// ──────────────── signature validation ────────────────
function validateFalSignature(rawBody: string, signatureHeader: string, secret: string): boolean {
  try {
    const hmac = crypto.createHmac("sha256", secret);
    hmac.update(rawBody, "utf8");
    const expected = `sha256=${hmac.digest("hex")}`;
    const sigBuf = Buffer.from(signatureHeader);
    const expBuf = Buffer.from(expected);
    if (sigBuf.length !== expBuf.length) return false;
    return crypto.timingSafeEqual(sigBuf, expBuf);
  } catch {
    return false;
  }
}

// ──────────────── cost helper ────────────────
const FAL_CENTS_PER_SEC_VIDEO = parseInt(process.env.FAL_CENTS_PER_SEC_VIDEO ?? "40", 10);
const FAL_CENTS_PER_SEC_IMAGE = parseInt(process.env.FAL_CENTS_PER_SEC_IMAGE ?? "5", 10);

function estimateCostCents(modelId: string, inferenceTimeSec: number): number {
  const rate = modelId.includes("wan") ? FAL_CENTS_PER_SEC_VIDEO : FAL_CENTS_PER_SEC_IMAGE;
  return Math.round(rate * inferenceTimeSec);
}

// ──────────────── fal webhook payload shape ────────────────
interface FalWebhookPayload {
  request_id: string;
  status: "completed" | "failed" | string;
  payload?: {
    images?: Array<{ url: string }>;
    video?: { url: string };
  };
  metrics?: { inference_time?: number };
  error?: { message?: string } | string | null;
}

// ──────────────── POST handler ────────────────
export async function POST(request: Request): Promise<Response> {
  // 1. Read raw body for signature verification.
  const rawBody = await request.text();
  const signature = request.headers.get("x-fal-signature") ?? "";
  const secret = process.env.FAL_WEBHOOK_SECRET ?? "";

  if (!secret) {
    console.error("FAL_WEBHOOK_SECRET is not set — rejecting webhook");
    return NextResponse.json({ error: "Webhook secret not configured." }, { status: 500 });
  }

  if (!validateFalSignature(rawBody, signature, secret)) {
    return NextResponse.json({ error: "Invalid signature." }, { status: 401 });
  }

  let body: FalWebhookPayload;
  try {
    body = JSON.parse(rawBody) as FalWebhookPayload;
  } catch {
    return NextResponse.json({ error: "Invalid JSON." }, { status: 400 });
  }

  const { request_id, status } = body;
  if (!request_id || !status) {
    return NextResponse.json({ error: "Missing request_id or status." }, { status: 400 });
  }

  // ── completed ──
  if (status === "completed") {
    const assetUrl =
      body.payload?.video?.url ??
      body.payload?.images?.[0]?.url ??
      null;

    const inferenceTimeSec = body.metrics?.inference_time ?? 0;
    const job = pendingJobs.get(request_id);
    const modelId = job?.modelId ?? "fal:unknown";
    const projectTitle = job?.project ?? "unknown";
    const costCents = estimateCostCents(modelId, inferenceTimeSec);

    // 2a. Notify local pipeline service (best-effort).
    try {
      await fetch(`http://127.0.0.1:8800/pipeline/jobs/${request_id}/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id, asset_url: assetUrl, cost_cents: costCents }),
        signal: AbortSignal.timeout(3000),
      });
    } catch {
      // Pipeline service may not be running in dev — non-fatal.
    }

    // 2b. Persist asset + rights record via studio writes.
    if (assetUrl) {
      try {
        const project = await getOrCreateProject({ title: projectTitle });
        if (project) {
          const assetType = modelId.includes("wan") ? "video" : "image";
          const { asset } = await createAssetWithRights({
            projectId: project.id,
            assetType,
            uri: assetUrl,
            modelId,
          });

          // 2c. Trace the generation in agent_runs.
          await studioDb.run.create({
            data: {
              agentName: modelId,
              plane: "production",
              modelUsed: modelId,
              costCents: costCents,
              latencyMs: Math.round(inferenceTimeSec * 1000),
              completedAt: new Date(),
            },
          });

          // 2d. Append to rights ledger JSONL.
          const songId = job?.songId ?? project.id;
          appendLedgerEntry(songId, {
            request_id,
            model: modelId,
            asset_url: assetUrl,
            asset_id: asset.id,
            cost_cents: costCents,
            inference_time_s: inferenceTimeSec,
          });
        }
      } catch (err) {
        console.error("fal webhook: failed to persist asset:", err);
      }
    }

    pendingJobs.delete(request_id);
    return NextResponse.json({ ok: true, request_id, status: "completed" }, { status: 200 });
  }

  // ── failed ──
  if (status === "failed") {
    const job = pendingJobs.get(request_id);
    const errorMsg =
      typeof body.error === "string"
        ? body.error
        : (body.error as { message?: string } | null)?.message ?? "unknown error";

    const failed: FailedJob = {
      requestId: request_id,
      modelId: job?.modelId ?? "fal:unknown",
      error: errorMsg,
      failedAt: new Date().toISOString(),
    };
    failedJobs.set(request_id, failed);
    pendingJobs.delete(request_id);

    console.error(`fal job failed: ${request_id} — ${errorMsg}`);
    return NextResponse.json({ ok: false, request_id, status: "failed", error: errorMsg }, { status: 200 });
  }

  // ── other statuses (IN_QUEUE, IN_PROGRESS) — acknowledge ──
  return NextResponse.json({ ok: true, request_id, status }, { status: 200 });
}
