import { describe, expect, it } from "vitest"
import { buildReport, failedVerdicts, revisionFeedback, supportedSourceIds } from "./verify"
import type { ClaimVerdict } from "./db"

const verdicts: ClaimVerdict[] = [
  { claim: "156-bed hospital approved", segmentIndex: 1, kind: "event", verdict: "supported", sourceIds: ["S1"], note: "stated in S1" },
  { claim: "costs $900 million", segmentIndex: 3, kind: "statistic", verdict: "unsupported", sourceIds: [], note: "no source mentions cost" },
  { claim: "opens next spring", segmentIndex: 4, kind: "event", verdict: "contradicted", sourceIds: ["S2"], note: "S2 says 2028" },
]

describe("failedVerdicts", () => {
  it("keeps only unsupported and contradicted", () => {
    const failed = failedVerdicts(verdicts)
    expect(failed).toHaveLength(2)
    expect(failed.map((f) => f.verdict)).toEqual(["unsupported", "contradicted"])
  })
})

describe("supportedSourceIds", () => {
  it("collects source ids from supported claims only", () => {
    const ids = supportedSourceIds(verdicts)
    expect([...ids]).toEqual(["S1"])
  })
})

describe("revisionFeedback", () => {
  it("names each failed claim with its segment and verdict", () => {
    const fb = revisionFeedback(failedVerdicts(verdicts))
    expect(fb).toContain('[segment 3] "costs $900 million" — unsupported')
    expect(fb).toContain('[segment 4] "opens next spring" — contradicted')
    expect(fb).toContain("REMOVE")
  })
})

describe("buildReport", () => {
  it("stamps passedAt only on pass", () => {
    expect(buildReport(verdicts, true, false).passedAt).toBeNull()
    expect(buildReport(verdicts, true, true).passedAt).toBeTruthy()
    expect(buildReport(verdicts, true, true).revised).toBe(true)
  })
})
