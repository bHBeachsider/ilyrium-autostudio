import type { Target } from "./decide";

// v1 connector = a DEFINED SEAM only (DISTRIBUTION_DESIGN.md §5). A connector is where the
// deferred distribution-worker slice will hook in to actually publish. The v1 stub does NOT
// publish and does NOT transition status (scheduled is v1-terminal), and distribute() does not
// invoke it — it exists to freeze the contract for the worker.

export type PublishResult = { ok: true; externalRef?: string } | { ok: false; error: string };

/** The minimal persisted-release shape a (future) connector receives. */
export interface ReleaseRow {
  id: string;
  masterAssetId: string;
  projectId: string | null;
  platform: string;
}

/** How a distribution target receives content. Real connectors implement this in a later slice. */
export interface Connector {
  readonly target: Target;
  publish(release: ReleaseRow): Promise<PublishResult>;
}

/** v1 stub: a no-op seam. Logs intent; performs no I/O; never publishes. */
export function stubConnector(target: Target): Connector {
  return {
    target,
    async publish(release: ReleaseRow): Promise<PublishResult> {
      console.log(`[relay] connector seam (no publish in v1): ${release.masterAssetId} -> ${release.platform}`);
      return { ok: true };
    },
  };
}

/** v1 registry: one defined seam per target. */
export const STUB_CONNECTORS: Record<Target, Connector> = {
  public_web: stubConnector("public_web"),
  discord: stubConnector("discord"),
  republic_archive: stubConnector("republic_archive"),
};
