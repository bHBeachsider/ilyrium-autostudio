export type CostBreakdown = {
  shots: number;
  secPerShot: number;
  totalSec: number;
  centsPerSec: number;
  estimateCents: number;
};

/**
 * Estimate render cost for a batch of shots.
 * centsPerSec comes from DB kpis.costPerRenderSecCents.
 */
export function estimateCost(
  shots: number,
  secPerShot: number,
  centsPerSec: number
): CostBreakdown {
  const totalSec = shots * secPerShot;
  const estimateCents = totalSec * centsPerSec;
  return { shots, secPerShot, totalSec, centsPerSec, estimateCents };
}

/**
 * True when adding a new job would put session spend over the hard cap.
 * Equality is not over-budget — the cap is exclusive.
 */
export function wouldExceedBudget(
  sessionCents: number,
  estimateCents: number,
  budgetCents: number
): boolean {
  return sessionCents + estimateCents > budgetCents;
}

/**
 * True when actual is within `tolerancePct`% of estimate (symmetric).
 * Used in tests to verify pre-submit estimates match real spend.
 */
export function withinTolerance(
  actual: number,
  estimate: number,
  tolerancePct: number
): boolean {
  if (estimate === 0) return actual === 0;
  return Math.abs(actual - estimate) / estimate <= tolerancePct / 100;
}

/** Format cents as a human-readable string. */
export function fmtCents(cents: number): string {
  if (cents < 100) return `${cents.toFixed(1)}c`;
  return `$${(cents / 100).toFixed(2)}`;
}
