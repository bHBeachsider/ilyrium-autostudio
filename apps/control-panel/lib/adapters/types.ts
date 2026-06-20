// apps/control-panel/lib/adapters/types.ts

export type MediaType = "image" | "video" | "audio";

export interface GenerateRequest {
  media: MediaType;
  prompt: string;
  project: string;
  aspect?: "1:1" | "16:9" | "9:16" | "4:3" | "3:4" | "21:9";
  duration_seconds?: number;
  resolution?: "720p" | "1080p" | "4k";
  loras?: string[];
  references?: string[];
  cost_ceiling_cents: number;
  prefer_tags?: string[];
}

export interface AdapterResponse {
  uri: string; // Temporary or direct vendor URL before R2 upload
  cost_cents: number;
  latency_ms: number;
}

export interface GenerateResponse {
  ok: boolean;
  media: MediaType;
  asset_id?: string;
  adapter_id?: string;
  fallback_chain: string[];
  uri?: string;
  preview_url?: string;
  duration_seconds?: number;
  resolution?: string;
  cost_cents?: number;
  latency_ms?: number;
  approved_for_release: boolean;
  error?: string;
}

// Every vendor (Veo, Grok, ElevenLabs) MUST implement this interface
export interface MediaAdapter {
  id: string;
  mediaType: MediaType;
  tags: string[];
  baseCostEstimate: number; // For cost ceiling pre-checks
  generate(req: GenerateRequest): Promise<AdapterResponse>;
}