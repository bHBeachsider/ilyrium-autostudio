import { describe, test, expect, vi, beforeEach, afterEach } from "vitest";

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

});
