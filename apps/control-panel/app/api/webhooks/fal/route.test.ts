import { describe, test, expect, vi, beforeEach } from "vitest";
import crypto from "crypto";

// ──────────── mock studio-writes ────────────
vi.mock("../../../../lib/studio-writes", () => ({
  createAssetWithRights: vi.fn().mockResolvedValue({ asset: { id: "asset-stub-id" }, deduped: false }),
  getOrCreateProject: vi.fn().mockResolvedValue({ id: "proj-stub-id", title: "test-project" }),
}));

// ──────────── mock studio-db ────────────
vi.mock("../../../../lib/studio-db", () => ({
  default: {
    run: {
      create: vi.fn().mockResolvedValue({ id: "run-stub" }),
    },
  },
}));

// ──────────── mock appendLedgerEntry ────────────
vi.mock("../../../../lib/ledger", () => ({
  appendLedgerEntry: vi.fn(),
}));

// ──────────── import after mocks ────────────
import { POST } from "./route";
import { pendingJobs, failedJobs } from "../../../../lib/adapters/falAdapter";
import { appendLedgerEntry } from "../../../../lib/ledger";

// ──────────── helpers ────────────
const SECRET = "test-webhook-secret";

function makeSignature(body: string, secret: string): string {
  const hmac = crypto.createHmac("sha256", secret);
  hmac.update(body, "utf8");
  return `sha256=${hmac.digest("hex")}`;
}

function makeRequest(body: object, opts: { secret?: string; badSig?: boolean } = {}): Request {
  const rawBody = JSON.stringify(body);
  const secret = opts.secret ?? SECRET;
  const sig = opts.badSig ? "sha256=badsig" : makeSignature(rawBody, secret);
  return new Request("http://localhost/api/webhooks/fal", {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-fal-signature": sig },
    body: rawBody,
  });
}

describe("POST /api/webhooks/fal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    pendingJobs.clear();
    failedJobs.clear();
    process.env.FAL_WEBHOOK_SECRET = SECRET;
    process.env.FAL_KEY = "test-key";
  });

  // ── signature validation ──
  test("rejects requests with a bad signature (401)", async () => {
    const req = makeRequest({ request_id: "req_001", status: "completed" }, { badSig: true });
    const res = await POST(req);
    expect(res.status).toBe(401);
    const json = await res.json();
    expect(json.error).toMatch(/signature/i);
  });

  test("rejects when FAL_WEBHOOK_SECRET is not set (500)", async () => {
    delete process.env.FAL_WEBHOOK_SECRET;
    const req = makeRequest({ request_id: "req_002", status: "completed" });
    const res = await POST(req);
    expect(res.status).toBe(500);
  });

  // ── completed payload ──
  test("processes a valid completed payload and returns ok", async () => {
    pendingJobs.set("req_ok_001", { modelId: "fal-ai/flux/schnell", project: "test-project" });

    const payload = {
      request_id: "req_ok_001",
      status: "completed",
      payload: {
        images: [{ url: "https://cdn.fal.ai/result.jpg" }],
      },
      metrics: { inference_time: 1.2 },
    };

    const req = makeRequest(payload);
    const res = await POST(req);

    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.status).toBe("completed");
  });

  test("completed: removes job from pendingJobs after processing", async () => {
    pendingJobs.set("req_cleanup", { modelId: "fal-ai/wan-i2v", project: "test-project" });

    const req = makeRequest({
      request_id: "req_cleanup",
      status: "completed",
      payload: { video: { url: "https://cdn.fal.ai/vid.mp4" } },
      metrics: { inference_time: 3.5 },
    });

    await POST(req);
    expect(pendingJobs.has("req_cleanup")).toBe(false);
  });

  test("completed: calls appendLedgerEntry with asset details", async () => {
    pendingJobs.set("req_ledger", { modelId: "fal-ai/flux/schnell", project: "stripe-cast" });

    const req = makeRequest({
      request_id: "req_ledger",
      status: "completed",
      payload: { images: [{ url: "https://cdn.fal.ai/art.jpg" }] },
      metrics: { inference_time: 0.8 },
    });

    await POST(req);
    expect(appendLedgerEntry).toHaveBeenCalledOnce();
    const [songId, event, payload] = (appendLedgerEntry as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(event).toBe("fal_asset_completed");
    expect(payload.request_id).toBe("req_ledger");
    expect(payload.asset_url).toBe("https://cdn.fal.ai/art.jpg");
    expect(typeof payload.cost_cents).toBe("number");
  });

  // ── failed payload ──
  test("stores failed jobs in failedJobs map", async () => {
    pendingJobs.set("req_fail_001", { modelId: "fal-ai/wan-i2v", project: "test-project" });

    const req = makeRequest({
      request_id: "req_fail_001",
      status: "failed",
      error: { message: "Out of memory" },
    });

    const res = await POST(req);
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.ok).toBe(false);
    expect(json.status).toBe("failed");

    expect(failedJobs.has("req_fail_001")).toBe(true);
    const failed = failedJobs.get("req_fail_001")!;
    expect(failed.error).toBe("Out of memory");
    expect(pendingJobs.has("req_fail_001")).toBe(false);
  });

  test("failed: removes job from pendingJobs", async () => {
    pendingJobs.set("req_fail_clean", { modelId: "fal-ai/flux/schnell", project: "test-project" });

    const req = makeRequest({ request_id: "req_fail_clean", status: "failed", error: "timeout" });
    await POST(req);

    expect(pendingJobs.has("req_fail_clean")).toBe(false);
  });

  // ── other statuses ──
  test("acknowledges in-progress status without side effects", async () => {
    const req = makeRequest({ request_id: "req_progress", status: "IN_QUEUE" });
    const res = await POST(req);
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.status).toBe("IN_QUEUE");
  });

  // ── bad JSON ──
  test("returns 400 for malformed JSON", async () => {
    const rawBody = "not-json";
    const sig = makeSignature(rawBody, SECRET);
    const req = new Request("http://localhost/api/webhooks/fal", {
      method: "POST",
      headers: { "x-fal-signature": sig },
      body: rawBody,
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });
});
