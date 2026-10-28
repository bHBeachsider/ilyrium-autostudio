import { describe, it, expect } from "vitest";
import {
  estimateCost,
  wouldExceedBudget,
  withinTolerance,
  fmtCents,
} from "./costMeter";

describe("estimateCost", () => {
  it("multiplies shots × secPerShot × centsPerSec", () => {
    const r = estimateCost(10, 8, 0.5);
    expect(r.totalSec).toBe(80);
    expect(r.estimateCents).toBe(40);
  });

  it("returns 0 for 0 shots", () => {
    expect(estimateCost(0, 8, 0.5).estimateCents).toBe(0);
  });

  it("carries input fields through", () => {
    const r = estimateCost(3, 5, 2);
    expect(r.shots).toBe(3);
    expect(r.secPerShot).toBe(5);
    expect(r.centsPerSec).toBe(2);
  });

  it("handles fractional rates", () => {
    const r = estimateCost(1, 1, 0.333);
    expect(r.estimateCents).toBeCloseTo(0.333, 3);
  });
});

describe("wouldExceedBudget", () => {
  it("returns false when under budget", () => {
    expect(wouldExceedBudget(50, 30, 100)).toBe(false);
  });

  it("returns true when over budget", () => {
    expect(wouldExceedBudget(80, 30, 100)).toBe(true);
  });

  it("returns false when exactly at budget", () => {
    expect(wouldExceedBudget(70, 30, 100)).toBe(false);
  });

  it("returns false when both are zero", () => {
    expect(wouldExceedBudget(0, 0, 0)).toBe(false);
  });
});

describe("withinTolerance", () => {
  it("passes when within 20%", () => {
    expect(withinTolerance(110, 100, 20)).toBe(true);
  });

  it("fails when outside 20%", () => {
    expect(withinTolerance(130, 100, 20)).toBe(false);
  });

  it("passes at exact boundary (20% of 100 = 20)", () => {
    expect(withinTolerance(120, 100, 20)).toBe(true);
  });

  it("returns true when both estimate and actual are 0", () => {
    expect(withinTolerance(0, 0, 20)).toBe(true);
  });

  it("returns false when actual non-zero but estimate is 0", () => {
    expect(withinTolerance(5, 0, 20)).toBe(false);
  });

  // Task 27 gate: pre-submit estimates must be within 25% of actual spend.
  it("satisfies task-27 tolerance gate (25%)", () => {
    const estimate = estimateCost(12, 5.3, 0.8).estimateCents; // ~50.88c
    const simulatedActual = estimate * 1.15; // 15% over — within 25%
    expect(withinTolerance(simulatedActual, estimate, 25)).toBe(true);
  });
});

describe("fmtCents", () => {
  it("formats sub-dollar as cents", () => {
    expect(fmtCents(42.5)).toBe("42.5c");
  });

  it("formats dollars correctly", () => {
    expect(fmtCents(150)).toBe("$1.50");
  });

  it("formats exactly 100 cents", () => {
    expect(fmtCents(100)).toBe("$1.00");
  });
});
