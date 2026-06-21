import type { Policy } from "./decide";

// relay-policy-v1 — the confirmed rating -> { targets, tier } mapping (DECIDE_DESIGN.md §3).
// This is DATA: changing distribution targets / tiers is a data edit, not a logic change.
export const RELAY_POLICY_V1: Policy = {
  version: "relay-policy-v1",
  rules: {
    clean: { targets: ["public_web", "discord", "republic_archive"], tier: "public" },
    mature: { targets: ["discord", "republic_archive"], tier: "gated" },
    uncensored: { targets: ["republic_archive"], tier: "gated" }, // intentionally tighter than mature
  },
};
