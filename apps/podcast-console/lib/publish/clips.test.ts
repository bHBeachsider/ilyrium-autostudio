import { describe, expect, it } from "vitest"
import { segmentWindows } from "./clips"

describe("segmentWindows", () => {
  it("prorates duration by character length and stays contiguous", () => {
    const segments = [
      { speaker: "Host A", text: "a".repeat(100) },
      { speaker: "Host B", text: "b".repeat(300) },
    ]
    const windows = segmentWindows(segments, 120)
    expect(windows[0].start).toBe(0)
    expect(windows[0].end).toBeCloseTo(30, 5)
    expect(windows[1].start).toBeCloseTo(30, 5)
    expect(windows[1].end).toBeCloseTo(120, 5)
  })
  it("survives empty-ish text", () => {
    const windows = segmentWindows([{ speaker: "Host A", text: " " }], 10)
    expect(windows).toHaveLength(1)
    expect(windows[0].end).toBeCloseTo(10, 5)
  })
})
