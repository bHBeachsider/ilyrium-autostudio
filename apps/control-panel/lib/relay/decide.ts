// Relay decide() — the single governed gate, as a PURE deterministic function.
// Contract + rules are specified in docs/relay/DECIDE_DESIGN.md (slice 1).
// No DB, no network, no clock, no randomness. Branches solely on `rating`.

export type Rating = "clean" | "mature" | "uncensored";
export type Target = "public_web" | "discord" | "republic_archive";
export type Tier = "public" | "gated";

export interface DecideInput {
  assetId: string; // echo-only; NOT a logic input
  rating: Rating; // the sole logic input
  allowed: boolean; // re-asserted (defense in depth)
}

export interface Policy {
  version: string;
  rules: Record<Rating, { targets: Target[]; tier: Tier }>;
}

export interface Decision {
  assetId: string;
  rating: Rating;
  targets: Target[];
  tier: Tier;
  reasons: string[];
  policyVersion: string;
}

/** Thrown when decide() is called on a non-release-approved asset (caller bug, not a business state). */
export class DecideContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DecideContractError";
  }
}

/**
 * Decide, for an already release-approved asset, HOW it may be distributed (targets) and
 * monetized (tier). Pure + total-except-on-contract-violation; `policy` is passed in (not
 * fetched) so this stays deterministic and exhaustively testable.
 */
export function decide(input: DecideInput, policy: Policy): Decision {
  // Precondition: only ever called when release-gate returned allowed===true. allowed!==true
  // is a caller bug — fail loud rather than mimic a legitimate "nothing eligible" result.
  if (input.allowed !== true) {
    throw new DecideContractError(
      `decide() requires a release-approved asset (allowed===true); got allowed=${String(input.allowed)} for asset ${input.assetId}.`,
    );
  }

  const rule = policy.rules[input.rating];

  // Fail-closed: an unrecognized rating yields the most-restrictive decision (deny).
  if (!rule) {
    return {
      assetId: input.assetId,
      rating: input.rating,
      targets: [],
      tier: "gated",
      reasons: [`unrecognized rating '${String(input.rating)}' -> fail-closed (no targets, gated)`],
      policyVersion: policy.version,
    };
  }

  return {
    assetId: input.assetId,
    rating: input.rating,
    targets: [...rule.targets], // fresh copy — never leak/alias the policy's array
    tier: rule.tier,
    reasons: [
      `rating '${input.rating}' -> ${rule.targets.length} target(s), tier '${rule.tier}' (policy ${policy.version})`,
    ],
    policyVersion: policy.version,
  };
}
