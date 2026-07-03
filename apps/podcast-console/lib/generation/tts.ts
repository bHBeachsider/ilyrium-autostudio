import type { Segment } from "@/lib/db"

// Two-host TTS via ElevenLabs, shared by /api/synthesize and the production
// pipeline. One call per host turn; buffers are concatenated (ffmpeg re-encodes
// downstream, so naive MP3 concatenation is fine).

const API_BASE = "https://api.elevenlabs.io/v1/text-to-speech"
const OUTPUT_FORMAT = "mp3_44100_128"

// Long-standing ElevenLabs default voices; override per your library via env.
const VOICE_A = process.env.ELEVENLABS_VOICE_A || "21m00Tcm4TlvDq8ikWAM" // Rachel (US, warm)
const VOICE_B = process.env.ELEVENLABS_VOICE_B || "JBFqnCBsd6RMkjVDRZzb" // George (UK, narration)
const MODEL_ID = process.env.ELEVENLABS_MODEL_ID || "eleven_multilingual_v2"

/** Cap to keep synthesis within a single route/step time budget. */
export const MAX_TTS_SEGMENTS = 40

export function ttsReady(): boolean {
  return !!process.env.ELEVENLABS_API_KEY
}

async function synthesizeSegment(text: string, voiceId: string, apiKey: string): Promise<Buffer> {
  const url = `${API_BASE}/${voiceId}?output_format=${OUTPUT_FORMAT}`
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "xi-api-key": apiKey,
      "Content-Type": "application/json",
      Accept: "audio/mpeg",
    },
    body: JSON.stringify({
      text,
      model_id: MODEL_ID,
      voice_settings: {
        stability: 0.5,
        similarity_boost: 0.75,
        style: 0.0,
        use_speaker_boost: true,
      },
    }),
  })

  if (!res.ok) {
    // ElevenLabs returns a JSON error body on failure.
    const detail = await res.text().catch(() => "")
    throw new Error(`ElevenLabs TTS failed (${res.status}): ${detail.slice(0, 200)}`)
  }

  return Buffer.from(await res.arrayBuffer())
}

export async function synthesizeSegments(segments: Segment[]): Promise<{ audio: Buffer; synthesized: number }> {
  const apiKey = process.env.ELEVENLABS_API_KEY
  if (!apiKey) {
    throw new Error("ELEVENLABS_API_KEY is not set. Add it to apps/podcast-console/.env.local and restart dev.")
  }
  const usable = segments.filter((s) => s?.text?.trim()).slice(0, MAX_TTS_SEGMENTS)
  if (usable.length === 0) throw new Error("No script segments to synthesize.")

  const buffers: Buffer[] = []
  for (const seg of usable) {
    const voiceId = seg.speaker === "Host B" ? VOICE_B : VOICE_A
    buffers.push(await synthesizeSegment(seg.text.trim(), voiceId, apiKey))
  }
  return { audio: Buffer.concat(buffers), synthesized: usable.length }
}
