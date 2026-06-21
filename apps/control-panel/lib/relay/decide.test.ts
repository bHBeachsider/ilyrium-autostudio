import { describe, test, expect } from "vitest";
import { decide, DecideContractError } from "./decide";
import { RELAY_POLICY_V1 } from "./policy";

const approved = (rating: any) => ({ assetId: "asset-123", rating, allowed: true });

describe("decide() — Relay slice 1 (per DECIDE_DESIGN.md)", () => {
  // 1. each valid rating -> exact {targets, tier}
  test("clean -> public_web/discord/republic_archive, public tier", () => {
    const d = decide(approved("clean"), RELAY_POLICY_V1);
    expect(d.targets).toEqual(["public_web", "discord", "republic_archive"]);
    expect(d.tier).toBe("public");
  });

  test("mature -> discord/republic_archive, gated tier", () => {
    const d = decide(approved("mature"), RELAY_POLICY_V1);
    expect(d.targets).toEqual(["discord", "republic_archive"]);
    expect(d.tier).toBe("gated");
  });

  test("uncensored -> republic_archive only (more restricted than mature), gated tier", () => {
    const d = decide(approved("uncensored"), RELAY_POLICY_V1);
    expect(d.targets).toEqual(["republic_archive"]);
    expect(d.tier).toBe("gated");
  });

  // contract echoes + stamps
  test("echoes assetId and rating into the Decision", () => {
    const d = decide({ assetId: "echo-me", rating: "mature", allowed: true }, RELAY_POLICY_V1);
    expect(d.assetId).toBe("echo-me");
    expect(d.rating).toBe("mature");
  });

  test("stamps policyVersion from the policy on every Decision", () => {
    const d = decide(approved("clean"), RELAY_POLICY_V1);
    expect(d.policyVersion).toBe("relay-policy-v1");
    expect(d.policyVersion).toBe(RELAY_POLICY_V1.version);
  });

  test("populates a non-empty reasons rationale", () => {
    const d = decide(approved("clean"), RELAY_POLICY_V1);
    expect(Array.isArray(d.reasons)).toBe(true);
    expect(d.reasons.length).toBeGreaterThan(0);
  });

  // 2. fail-closed: unrecognized rating -> no targets, gated
  test("unrecognized rating -> fail-closed: no targets, gated tier", () => {
    const d = decide(approved("bogus"), RELAY_POLICY_V1);
    expect(d.targets).toEqual([]);
    expect(d.tier).toBe("gated");
    expect(d.reasons.join(" ")).toMatch(/fail-closed|unrecognized/i);
  });

  // 3. allowed === false -> throws DecideContractError (caller bug, not a business state)
  test("allowed === false -> throws DecideContractError", () => {
    expect(() => decide({ assetId: "x", rating: "clean", allowed: false }, RELAY_POLICY_V1)).toThrow(
      DecideContractError,
    );
  });

  // 4. determinism
  test("deterministic: same input -> identical Decision", () => {
    const input = { assetId: "det", rating: "uncensored" as const, allowed: true };
    expect(decide(input, RELAY_POLICY_V1)).toEqual(decide(input, RELAY_POLICY_V1));
  });

  // 5. purity: input is not mutated
  test("does not mutate input or leak the policy's target array", () => {
    const input = { assetId: "pure", rating: "clean" as const, allowed: true };
    const d = decide(input, RELAY_POLICY_V1);
    d.targets.push("MUTATED" as any);
    expect(RELAY_POLICY_V1.rules.clean.targets).toEqual(["public_web", "discord", "republic_archive"]);
    expect(input).toEqual({ assetId: "pure", rating: "clean", allowed: true });
  });
});
