import { describe, expect, it } from "vitest"
import { flattenProducerScript, parseDurationSeconds, scriptMeta, speakerLabel } from "./normalize"

const producerScript = {
  episode_meta: { week_of: "2026-06-08", jurisdiction: "Palm Beach County" },
  segments: [
    {
      type: "development_news",
      turns: [
        { speaker: "host_a", text: "Welcome back to the show." },
        { speaker: "host_b", text: "Big week for permits." },
      ],
      clip_cues: [{ clip_id: 12, after_turn_index: 0 }],
    },
    {
      type: "local_roundup",
      turns: [{ speaker: "host_a", text: "Now the roundup." }],
      clip_cues: [],
    },
  ],
}

describe("speakerLabel", () => {
  it("maps producer speakers to console hosts", () => {
    expect(speakerLabel("host_a")).toBe("Host A")
    expect(speakerLabel("host_b")).toBe("Host B")
  })
  it("passes through unknown speakers", () => {
    expect(speakerLabel("narrator")).toBe("narrator")
  })
})

describe("flattenProducerScript", () => {
  it("flattens both segments' turns in order with mapped speakers", () => {
    expect(flattenProducerScript(producerScript)).toEqual([
      { speaker: "Host A", text: "Welcome back to the show." },
      { speaker: "Host B", text: "Big week for permits." },
      { speaker: "Host A", text: "Now the roundup." },
    ])
  })
  it("returns [] for malformed input", () => {
    expect(flattenProducerScript(null)).toEqual([])
    expect(flattenProducerScript({})).toEqual([])
    expect(flattenProducerScript({ segments: "nope" })).toEqual([])
    expect(flattenProducerScript({ segments: [{ turns: [{ speaker: "host_a" }] }] })).toEqual([])
  })
})

describe("scriptMeta", () => {
  it("extracts week_of and jurisdiction", () => {
    expect(scriptMeta(producerScript)).toEqual({ weekOf: "2026-06-08", jurisdiction: "Palm Beach County" })
  })
  it("tolerates missing meta", () => {
    expect(scriptMeta({})).toEqual({ weekOf: null, jurisdiction: null })
  })
})

describe("parseDurationSeconds", () => {
  it("handles seconds, mm:ss, hh:mm:ss and numbers", () => {
    expect(parseDurationSeconds("3123")).toBe(3123)
    expect(parseDurationSeconds("52:03")).toBe(3123)
    expect(parseDurationSeconds("1:02:03")).toBe(3723)
    expect(parseDurationSeconds(90.4)).toBe(90)
  })
  it("returns null for junk", () => {
    expect(parseDurationSeconds("")).toBeNull()
    expect(parseDurationSeconds("abc")).toBeNull()
    expect(parseDurationSeconds(undefined)).toBeNull()
  })
})
