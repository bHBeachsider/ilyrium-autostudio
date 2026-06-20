// apps/control-panel/lib/adapter-bus.ts
// Phase 1: wired onto the REAL asset graph. The broken ./db (insertAsset/writeRightsRecord/
// logTelemetry) and ./storage (uploadToR2/generatePresignedUrl) mock imports are gone;
// generation now persists via the shared studio writers (asset + paired rights_records +
// agent_runs trace). R2 upload is out of scope (no storage layer yet) — the adapter-returned
// uri is recorded as-is and used as the preview. approved_for_release stays false (governed
// by the rights ledger; cleared only via /api/studio/approve).
import { MediaAdapter, GenerateRequest, GenerateResponse, MediaType } from "./adapters/types";
import { getOrCreateProject, createAssetWithRights } from "./studio-writes";
import studioDb from "./studio-db";

const registeredAdapters: MediaAdapter[] = [
  { id: "google-veo-3.1", mediaType: "video", tags: ["high_res", "cinematic"], baseCostEstimate: 200, generate: async () => ({ uri: "vendor://veo/clip", cost_cents: 200, latency_ms: 15000 }) },
  { id: "grok-imagine", mediaType: "video", tags: ["fast"], baseCostEstimate: 100, generate: async () => ({ uri: "vendor://grok/clip", cost_cents: 100, latency_ms: 8000 }) },
  { id: "elevenlabs", mediaType: "audio", tags: ["multilingual"], baseCostEstimate: 50, generate: async () => ({ uri: "vendor://elevenlabs/audio", cost_cents: 45, latency_ms: 3000 }) },
];

// media -> real asset_type CHECK value (audio is voiced narration in this pipeline).
const MEDIA_TO_ASSET_TYPE: Record<MediaType, string> = { image: "image", video: "video", audio: "voice" };

export async function executeGeneration(req: GenerateRequest): Promise<GenerateResponse> {
  const startTime = Date.now();
  const fallbackChain: string[] = [];

  // 1. Filter adapters by capability + cost ceiling.
  const availableAdapters = registeredAdapters.filter(
    (a) => a.mediaType === req.media && a.baseCostEstimate <= req.cost_ceiling_cents,
  );

  // 2. Sort by preferred tags (routing bias).
  if (req.prefer_tags && req.prefer_tags.length > 0) {
    availableAdapters.sort((a, b) => {
      const am = a.tags.filter((t) => req.prefer_tags!.includes(t)).length;
      const bm = b.tags.filter((t) => req.prefer_tags!.includes(t)).length;
      return bm - am;
    });
  }

  if (availableAdapters.length === 0) {
    return { ok: false, media: req.media, fallback_chain: [], approved_for_release: false, error: "No adapters available matching constraints." };
  }

  // Resolve the project once (get-or-create by title).
  const project = await getOrCreateProject({ title: req.project });
  if (!project) {
    return { ok: false, media: req.media, fallback_chain: [], approved_for_release: false, error: "Could not resolve a project for the generation request." };
  }

  // 3. Fallback loop.
  for (const adapter of availableAdapters) {
    fallbackChain.push(adapter.id);
    try {
      const result = await adapter.generate(req);
      const totalLatency = Date.now() - startTime;

      // 4. Persistence + governance: asset + paired rights_records (auto-quarantined) + trace.
      const { asset } = await createAssetWithRights({
        projectId: project.id,
        assetType: MEDIA_TO_ASSET_TYPE[req.media] ?? "video",
        uri: result.uri,
        modelId: adapter.id,
      });

      await studioDb.run.create({
        data: {
          agentName: adapter.id,
          plane: "production",
          modelUsed: adapter.id,
          costCents: Math.round(result.cost_cents),
          latencyMs: totalLatency,
          completedAt: new Date(),
        },
      });

      return {
        ok: true,
        media: req.media,
        asset_id: asset.id,
        adapter_id: adapter.id,
        fallback_chain: fallbackChain,
        uri: result.uri,
        preview_url: result.uri,
        duration_seconds: req.duration_seconds,
        resolution: req.resolution,
        cost_cents: result.cost_cents,
        latency_ms: totalLatency,
        approved_for_release: false, // Enforced by the rights ledger.
      };
    } catch (error) {
      console.warn(`Adapter ${adapter.id} failed. Falling back...`, error);
    }
  }

  return { ok: false, media: req.media, fallback_chain: fallbackChain, approved_for_release: false, error: "All adapters in fallback chain failed." };
}
