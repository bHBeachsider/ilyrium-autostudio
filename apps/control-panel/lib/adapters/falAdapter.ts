// apps/control-panel/lib/adapters/falAdapter.ts
// Server-only: FAL_KEY must never reach the browser.
// Two adapters: falVideoAdapter (wan-i2v) + falImageAdapter (flux/schnell).
// generate() submits to fal.queue and returns immediately with a pending URI
// (fal://queue/<modelId>/<requestId>). The webhook route handles completion.

import { fal } from "@fal-ai/client";
import fs from "fs";
import path from "path";
import type { MediaAdapter, GenerateRequest, AdapterResponse } from "./types";

// ---------- env constants ----------
const FAL_CENTS_PER_SEC_VIDEO = parseInt(process.env.FAL_CENTS_PER_SEC_VIDEO ?? "40", 10);
const FAL_CENTS_PER_SEC_IMAGE = parseInt(process.env.FAL_CENTS_PER_SEC_IMAGE ?? "5", 10);
// Preliminary inference-time estimate for the upfront cost record (5 s video / 1 s image).
const PREFLIGHT_SECS_VIDEO = 5;
const PREFLIGHT_SECS_IMAGE = 1;

// ---------- in-process job tracking (serverless: ephemeral, fine for dev/test) ----------
export interface PendingJob {
  modelId: string;
  project: string;
  songId?: string;
}
export const pendingJobs = new Map<string, PendingJob>();

// ---------- failed job log (in-memory; swappable for DB when takes table lands) ----------
export interface FailedJob {
  requestId: string;
  modelId: string;
  error: string;
  failedAt: string;
}
export const failedJobs = new Map<string, FailedJob>();

// ---------- rights ledger ----------
/**
 * Append-only JSONL entry to ilyrium-shots/ledger/<songId>.jsonl.
 * Path is relative to the repo root (two dirs above apps/control-panel).
 */
export function appendLedgerEntry(songId: string, entry: Record<string, unknown>): void {
  const ledgerDir = path.resolve(process.cwd(), "../../ilyrium-shots/ledger");
  fs.mkdirSync(ledgerDir, { recursive: true });
  const ledgerPath = path.join(ledgerDir, `${songId}.jsonl`);
  fs.appendFileSync(
    ledgerPath,
    JSON.stringify({ ...entry, ts: new Date().toISOString() }) + "\n",
    "utf8",
  );
}

// ---------- extended adapter interface ----------
export interface FalMediaAdapter extends MediaAdapter {
  getStatus(requestId: string): Promise<unknown>;
  cancel(requestId: string): Promise<void>;
}

// ---------- factory ----------
function buildFalAdapter(modelId: string, mediaType: "video" | "image"): FalMediaAdapter {
  const centsPerSec = mediaType === "video" ? FAL_CENTS_PER_SEC_VIDEO : FAL_CENTS_PER_SEC_IMAGE;
  const preflightSecs = mediaType === "video" ? PREFLIGHT_SECS_VIDEO : PREFLIGHT_SECS_IMAGE;

  return {
    id: `fal:${modelId}`,
    mediaType,
    tags: mediaType === "video" ? ["async", "fal", "cinematic"] : ["async", "fal", "fast"],
    baseCostEstimate: centsPerSec * preflightSecs,

    async generate(req: GenerateRequest): Promise<AdapterResponse> {
      fal.config({ credentials: process.env.FAL_KEY ?? "" });
      const startTime = Date.now();

      const { request_id } = await fal.queue.submit(modelId, {
        input: {
          prompt: req.prompt,
          ...(req.aspect ? { aspect_ratio: req.aspect } : {}),
          ...(req.duration_seconds ? { duration_seconds: req.duration_seconds } : {}),
          ...(req.references?.length ? { image_url: req.references[0] } : {}),
          ...(req.loras?.length ? { loras: req.loras } : {}),
        },
      });

      pendingJobs.set(request_id, {
        modelId,
        project: req.project,
      });

      return {
        uri: `fal://queue/${modelId}/${request_id}`,
        cost_cents: centsPerSec * preflightSecs,
        latency_ms: Date.now() - startTime,
      };
    },

    async getStatus(requestId: string): Promise<unknown> {
      fal.config({ credentials: process.env.FAL_KEY ?? "" });
      return fal.queue.status(modelId, { requestId });
    },

    async cancel(requestId: string): Promise<void> {
      fal.config({ credentials: process.env.FAL_KEY ?? "" });
      await fal.queue.cancel(modelId, { requestId });
    },
  };
}

export const falVideoAdapter: FalMediaAdapter = buildFalAdapter("fal-ai/wan-i2v", "video");
export const falImageAdapter: FalMediaAdapter = buildFalAdapter("fal-ai/flux/schnell", "image");
