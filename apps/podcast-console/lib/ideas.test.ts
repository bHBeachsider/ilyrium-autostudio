import { describe, expect, it } from "vitest"
import { canDecide } from "./ideas"
import { isDuplicateTitle } from "./agents/idea-generator"

describe("canDecide", () => {
  it("allows reviewer decisions from proposed", () => {
    expect(canDecide("proposed", "approved")).toBe(true)
    expect(canDecide("proposed", "rejected")).toBe(true)
    expect(canDecide("proposed", "needs_changes")).toBe(true)
  })
  it("allows approve/reject (not needs_changes) from needs_changes", () => {
    expect(canDecide("needs_changes", "approved")).toBe(true)
    expect(canDecide("needs_changes", "rejected")).toBe(true)
    expect(canDecide("needs_changes", "needs_changes")).toBe(false)
  })
  it("blocks decisions once an idea is past review", () => {
    for (const status of ["approved", "rejected", "producing", "produced", "published"] as const) {
      expect(canDecide(status, "approved")).toBe(false)
      expect(canDecide(status, "rejected")).toBe(false)
    }
  })
})

describe("isDuplicateTitle", () => {
  const existing = [
    "The Marina District Rezoning Fight in Boca Raton",
    "Permit Fee Waivers: Jupiter's Storm Repair Push",
  ]
  it("catches exact and near-identical titles", () => {
    expect(isDuplicateTitle("The Marina District Rezoning Fight in Boca Raton", existing)).toBe(true)
    expect(isDuplicateTitle("marina district rezoning fight in boca raton!", existing)).toBe(true)
  })
  it("catches high token overlap", () => {
    expect(isDuplicateTitle("Boca Raton's Marina District Rezoning Fight", existing)).toBe(true)
  })
  it("passes genuinely distinct titles", () => {
    expect(isDuplicateTitle("Impact Fees 101: What Builders Pay and Why", existing)).toBe(false)
  })
  it("handles empty inputs", () => {
    expect(isDuplicateTitle("Anything", [])).toBe(false)
  })
})
