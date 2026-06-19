// apps/control-panel/lib/adapter-bus.ts
import { MediaAdapter, GenerateRequest, GenerateResponse } from "./adapters/types";
import { insertAsset, writeRightsRecord, logTelemetry } from "./db"; // Mocked Neon DB imports
import { uploadToR2, generatePresignedUrl } from "./storage"; // Mocked Cloudflare R2 imports

// In reality, these would be imported from their respective files in lib/adapters/
const registeredAdapters: MediaAdapter[] = [
  // Mock examples of your live/in-flight adapters
  { id: "google-veo-3.1", mediaType: "video", tags: ["high_res", "cinematic"], baseCostEstimate: 200, generate: async () => ({ uri: "...", cost_cents: 200, latency_ms: 15000 }) },
  { id: "grok-imagine", mediaType: "video", tags: ["fast"], baseCostEstimate: 100, generate: async () => ({ uri: "...", cost_cents: 100, latency_ms: 8000 }) },
  { id: "elevenlabs", mediaType: "audio", tags: ["multilingual"], baseCostEstimate: 50, generate: async () => ({ uri: "...", cost_cents: 45, latency_ms: 3000 }) },
];

export async function executeGeneration(req: GenerateRequest): Promise<GenerateResponse> {
  const startTime = Date.now();
  const fallbackChain: string[] = [];

  // 1. Filter adapters by capability and cost ceiling
  let availableAdapters = registeredAdapters.filter(a => 
    a.mediaType === req.media && 
    a.baseCostEstimate <= req.cost_ceiling_cents
  );

  // 2. Sort by preferred tags (routing bias)
  if (req.prefer_tags && req.prefer_tags.length > 0) {
    availableAdapters.sort((a, b) => {
      const aMatches = a.tags.filter(t => req.prefer_tags!.includes(t)).length;
      const bMatches = b.tags.filter(t => req.prefer_tags!.includes(t)).length;
      return bMatches - aMatches; // Highest matches first
    });
  }

  if (availableAdapters.length === 0) {
    return { ok: false, media: req.media, fallback_chain: [], approved_for_release: false, error: "No adapters available matching constraints." };
  }

  // 3. Fallback Loop execution
  for (const adapter of availableAdapters) {
    fallbackChain.push(adapter.id);
    try {
      // Attempt generation
      const result = await adapter.generate(req);

      // 4. Persistence & Governance (If successful)
      const r2Uri = await uploadToR2(result.uri, req.project);
      const previewUrl = await generatePresignedUrl(r2Uri);
      
      // Default to FL §540.08 / SAG-AFTRA compliance: unreleased.
      const assetId = await insertAsset(req.project, r2Uri, req.media);
      await writeRightsRecord(assetId, { approved: false, trigger: "auto-quarantine" });

      // Telemetry
      const totalLatency = Date.now() - startTime;
      await logTelemetry({ assetId, adapter: adapter.id, cost: result.cost_cents, latency: totalLatency, chain: fallbackChain });

      return {
        ok: true,
        media: req.media,
        asset_id: assetId,
        adapter_id: adapter.id,
        fallback_chain: fallbackChain,
        uri: r2Uri,
        preview_url: previewUrl,
        duration_seconds: req.duration_seconds,
        resolution: req.resolution,
        cost_cents: result.cost_cents,
        latency_ms: totalLatency,
        approved_for_release: false // Enforced by rights ledger
      };

    } catch (error) {
      console.warn(`Adapter ${adapter.id} failed. Falling back...`, error);
      // Loop continues to the next adapter
    }
  }

  // If we exhaust all adapters
  return {
    ok: false,
    media: req.media,
    fallback_chain: fallbackChain,
    approved_for_release: false,
    error: "All adapters in fallback chain failed."
  };
}