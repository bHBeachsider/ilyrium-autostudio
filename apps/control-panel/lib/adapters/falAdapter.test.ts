import { describe, test, expect, vi, beforeEach, afterEach } from "vitest";
import fs from "fs";
import path from "path";

// vi.mock is hoisted — factory must not reference outer variables
vi.mock("@fal-ai/client", () => ({
  fal: {
    config: vi.fn(),
    queue: {
      submit: vi.fn(),
      status: vi.fn(),
      cancel: vi.fn(),
    },
  },
}));

// Import mocked module AFTER vi.mock so we get the mock instances
import { fal } from "@fal-ai/client";
import {
  falVideoAdapter,
  falImageAdapter,
  pendingJobs,
  appendLedgerEntry,
} from "./falAdapter";

describe("falAdapter", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    pendingJobs.clear();
    process.env.FAL_KEY = "test-key";
  });

  afterEach(() => {
    delete process.env.FAL_KEY;
  });

  // ── generate() returns pending URI ──
  test("falVideoAdapter.generate() submits to queue and returns pending URI", async () => {
    vi.mocked(fal.queue.submit).mockResolvedValueOnce({
      status: "IN_QUEUE",
      request_id: "req_video_123",
      response_url: "",
      status_url: "",
      cancel_url: "",
      queue_position: 0,
    });

    const result = await falVideoAdapter.generate({
      media: "video",
      prompt: "A cinematic sunset over Malibu",
      project: "stripe-cast",
      cost_ceiling_cents: 500,
    });

    expect(fal.queue.submit).toHaveBeenCalledOnce();
    expect(fal.queue.submit).toHaveBeenCalledWith(
      "fal-ai/wan-i2v",
      expect.objectContaining({ input: expect.objectContaining({ prompt: "A cinematic sunset over Malibu" }) }),
    );
    expect(result.uri).toBe("fal://queue/fal-ai/wan-i2v/req_video_123");
    expect(result.cost_cents).toBeGreaterThan(0);
    expect(result.latency_ms).toBeGreaterThanOrEqual(0);
  });

  test("falImageAdapter.generate() submits to correct model and returns pending URI", async () => {
    vi.mocked(fal.queue.submit).mockResolvedValueOnce({
      status: "IN_QUEUE",
      request_id: "req_img_456",
      response_url: "",
      status_url: "",
      cancel_url: "",
      queue_position: 0,
    });

    const result = await falImageAdapter.generate({
      media: "image",
      prompt: "Abstract album art",
      project: "stripe-cast",
      cost_ceiling_cents: 100,
    });

    expect(fal.queue.submit).toHaveBeenCalledWith("fal-ai/flux/schnell", expect.anything());
    expect(result.uri).toBe("fal://queue/fal-ai/flux/schnell/req_img_456");
  });

  // ── generate() appends to pendingJobs ──
  test("generate() registers the job in pendingJobs", async () => {
    vi.mocked(fal.queue.submit).mockResolvedValueOnce({
      status: "IN_QUEUE",
      request_id: "req_pending_789",
      response_url: "",
      status_url: "",
      cancel_url: "",
      queue_position: 0,
    });

    await falVideoAdapter.generate({
      media: "video",
      prompt: "Test",
      project: "my-project",
      cost_ceiling_cents: 500,
    });

    expect(pendingJobs.has("req_pending_789")).toBe(true);
    expect(pendingJobs.get("req_pending_789")).toMatchObject({
      modelId: "fal-ai/wan-i2v",
      project: "my-project",
    });
  });

  // ── getStatus() delegates to fal.queue ──
  test("getStatus() calls fal.queue.status with the correct requestId", async () => {
    vi.mocked(fal.queue.status).mockResolvedValueOnce({ status: "IN_PROGRESS" } as any);

    const status = await falVideoAdapter.getStatus("req_status_abc");

    expect(fal.queue.status).toHaveBeenCalledWith("fal-ai/wan-i2v", { requestId: "req_status_abc" });
    expect(status).toEqual({ status: "IN_PROGRESS" });
  });

  // ── cancel() delegates to fal.queue ──
  test("cancel() calls fal.queue.cancel", async () => {
    vi.mocked(fal.queue.cancel).mockResolvedValueOnce(undefined);

    await falVideoAdapter.cancel("req_cancel_abc");

    expect(fal.queue.cancel).toHaveBeenCalledWith("fal-ai/wan-i2v", { requestId: "req_cancel_abc" });
  });

  // ── adapter interface fields ──
  test("falVideoAdapter exposes correct mediaType and tags", () => {
    expect(falVideoAdapter.mediaType).toBe("video");
    expect(falVideoAdapter.tags).toContain("fal");
  });

  test("falImageAdapter exposes correct mediaType", () => {
    expect(falImageAdapter.mediaType).toBe("image");
  });

  // ── appendLedgerEntry ──
  test("appendLedgerEntry writes a JSONL line to the ledger file", () => {
    const tmpDir = path.join(
      process.env.TEMP ?? process.env.TMPDIR ?? "/tmp",
      `fal-ledger-test-${Date.now()}`,
    );
    const origCwd = process.cwd;
    process.cwd = () => path.join(tmpDir, "apps", "control-panel");

    try {
      appendLedgerEntry("song-abc", { asset_url: "https://cdn.fal.ai/test.mp4", cost_cents: 200 });

      const ledgerPath = path.join(tmpDir, "ilyrium-shots", "ledger", "song-abc.jsonl");
      expect(fs.existsSync(ledgerPath)).toBe(true);

      const lines = fs.readFileSync(ledgerPath, "utf8").trim().split("\n");
      expect(lines).toHaveLength(1);

      const parsed = JSON.parse(lines[0]);
      expect(parsed.asset_url).toBe("https://cdn.fal.ai/test.mp4");
      expect(parsed.cost_cents).toBe(200);
      expect(parsed.ts).toBeTruthy();
    } finally {
      process.cwd = origCwd;
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });

  test("appendLedgerEntry appends multiple entries", () => {
    const tmpDir = path.join(
      process.env.TEMP ?? process.env.TMPDIR ?? "/tmp",
      `fal-ledger-test2-${Date.now()}`,
    );
    const origCwd = process.cwd;
    process.cwd = () => path.join(tmpDir, "apps", "control-panel");

    try {
      appendLedgerEntry("song-multi", { seq: 1 });
      appendLedgerEntry("song-multi", { seq: 2 });

      const ledgerPath = path.join(tmpDir, "ilyrium-shots", "ledger", "song-multi.jsonl");
      const lines = fs.readFileSync(ledgerPath, "utf8").trim().split("\n");
      expect(lines).toHaveLength(2);
      expect(JSON.parse(lines[0]).seq).toBe(1);
      expect(JSON.parse(lines[1]).seq).toBe(2);
    } finally {
      process.cwd = origCwd;
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });
});
