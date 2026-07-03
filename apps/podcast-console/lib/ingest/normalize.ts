import type { Segment } from "@/lib/db"

// Mapping from the PermitHub producer's script.json to the console's segment shape.
// Producer contract (PermitHub-API scripts/intelligence/podcast/script_synthesizer.py):
//   { episode_meta: {week_of, jurisdiction},
//     segments: [{type, turns: [{speaker: "host_a"|"host_b", text}], clip_cues}] }

const SPEAKER_LABELS: Record<string, string> = {
  host_a: "Host A",
  host_b: "Host B",
}

export function speakerLabel(speaker: string): string {
  return SPEAKER_LABELS[speaker] ?? speaker
}

type ProducerTurn = { speaker?: unknown; text?: unknown }
type ProducerSegment = { turns?: unknown }
export type ProducerScript = {
  episode_meta?: { week_of?: unknown; jurisdiction?: unknown }
  segments?: unknown
}

/** Flatten producer segments[].turns into the console's flat {speaker,text}[] list.
 * Tolerant of malformed input: anything unusable yields []. */
export function flattenProducerScript(script: unknown): Segment[] {
  const doc = script as ProducerScript | null
  if (!doc || !Array.isArray(doc.segments)) return []
  const out: Segment[] = []
  for (const seg of doc.segments as ProducerSegment[]) {
    if (!seg || !Array.isArray(seg.turns)) continue
    for (const turn of seg.turns as ProducerTurn[]) {
      const text = typeof turn?.text === "string" ? turn.text.trim() : ""
      if (!text) continue
      const speaker = typeof turn?.speaker === "string" ? speakerLabel(turn.speaker) : "Host A"
      out.push({ speaker, text })
    }
  }
  return out
}

export function scriptMeta(script: unknown): { weekOf: string | null; jurisdiction: string | null } {
  const meta = (script as ProducerScript | null)?.episode_meta
  return {
    weekOf: typeof meta?.week_of === "string" ? meta.week_of : null,
    jurisdiction: typeof meta?.jurisdiction === "string" ? meta.jurisdiction : null,
  }
}

/** Parse itunes-style durations ("3123", "52:03", "1:02:03") into seconds. */
export function parseDurationSeconds(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return Math.round(value)
  if (typeof value !== "string" || !value.trim()) return null
  const parts = value.trim().split(":").map((p) => Number(p))
  if (parts.some((n) => !Number.isFinite(n))) return null
  return parts.reduce((acc, n) => acc * 60 + n, 0)
}
