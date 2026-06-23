import { describe, it, expect } from "vitest";
import { stubConnector, STUB_CONNECTORS } from "./connector";

// v1 connector = a DEFINED SEAM only. The stub does not publish and does not transition
// status (scheduled is v1-terminal); it freezes the contract for the deferred worker slice.
describe("connector seam (v1 stub — no publish)", () => {
  it("stubConnector carries its target and is a no-op success", async () => {
    const c = stubConnector("discord");
    expect(c.target).toBe("discord");
    expect(await c.publish({ id: "r1", masterAssetId: "a1", projectId: "p1", platform: "discord" })).toEqual({
      ok: true,
    });
  });

  it("STUB_CONNECTORS defines exactly one seam per target", () => {
    expect(Object.keys(STUB_CONNECTORS).sort()).toEqual(["discord", "public_web", "republic_archive"]);
    expect(STUB_CONNECTORS.republic_archive.target).toBe("republic_archive");
  });
});
