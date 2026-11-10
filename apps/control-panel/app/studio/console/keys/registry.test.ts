import { describe, expect, it } from "vitest";
import { PAGES, navLabelOf, railPages } from "../pages";
import { parseChord } from "./match";
import { BINDINGS, cheatSheetRows, filterCommands, paletteCommands } from "./registry";

describe("binding registry", () => {
  it("has unique ids and parseable chords", () => {
    const ids = BINDINGS.map((b) => b.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const b of BINDINGS) for (const k of b.keys) expect(() => parseChord(k), `${b.id} ${k}`).not.toThrow();
  });

  it("has no duplicate chord within a scope", () => {
    const seen = new Set<string>();
    for (const b of BINDINGS) for (const k of b.keys) {
      const slot = `${b.scope}:${k}`;
      expect(seen.has(slot), slot).toBe(false);
      seen.add(slot);
    }
  });

  it("has no chord shared across scopes, so one key never means two things", () => {
    const owner = new Map<string, string>();
    for (const b of BINDINGS) for (const k of b.keys) {
      expect(owner.has(k) ? owner.get(k) : b.scope, k).toBe(b.scope);
      owner.set(k, b.scope);
    }
  });

  it("keeps bare letters out of the global scope", () => {
    for (const b of BINDINGS.filter((x) => x.scope === "global")) for (const k of b.keys) {
      const c = parseChord(k);
      if (!c.mod) expect(["?", "Escape"], b.id).toContain(c.key);
    }
  });

  it("cheat sheet rows are exactly the bindings that have keys", () => {
    const rows = cheatSheetRows(BINDINGS).map((r) => r.id);
    expect(rows).toEqual(BINDINGS.filter((b) => b.keys.length > 0).map((b) => b.id));
  });

  it("ties the rail to the palette: every rail page has a 'Go to <rail label>' command, placeholders stay out of the rail", () => {
    const rail = railPages();
    expect(rail.map((p) => p.slug)).toEqual(PAGES.filter((p) => p.kind !== "placeholder").map((p) => p.slug));
    const cmds = paletteCommands(BINDINGS, () => true);
    for (const p of rail) {
      expect(p.domain, `${p.slug} needs a domain for its rail icon`).toBeTruthy();
      expect(p.sub, `${p.slug} needs a rail sub-line`).toBeTruthy();
      const cmd = cmds.find((c) => c.id === `nav.${p.slug}`);
      expect(cmd?.label, p.slug).toBe(`Go to ${navLabelOf(p)}`);
    }
    for (const p of PAGES.filter((x) => x.kind === "placeholder")) {
      expect(cmds.some((c) => c.id === `nav.${p.slug}`), `${p.slug} is palette-only`).toBe(true);
      expect(rail.includes(p), p.slug).toBe(false);
    }
  });

  it("palette search finds the navigation commands by the keywords they had before the routing change", () => {
    const cmds = paletteCommands(BINDINGS, () => true);
    const find = (q: string) => filterCommands(cmds, q).map((c) => c.id);
    expect(find("cost")).toContain("nav.analytics");
    expect(find("render")).toContain("nav.legacy-generation");
    expect(find("cut")).toContain("nav.legacy-assembly");
    expect(find("takes")).toContain("nav.legacy-review");
    expect(find("llm")).toContain("nav.chat");
    expect(find("stages")).toContain("nav.run");
    expect(find("ec2")).toEqual(["box.start", "box.stop"]);
    expect(find("zzz-nothing")).toEqual([]);
    expect(find("   ")).toHaveLength(cmds.length);
  });

  it("generates palette commands from the table and only for registered handlers", () => {
    expect(paletteCommands(BINDINGS, () => false)).toEqual([]);
    const cmds = paletteCommands(BINDINGS, () => true);
    const labels = cmds.map((c) => c.label);
    expect(labels).toContain("Go to Pipeline");
    expect(labels).toContain("Go to Ideation & Scripting");
    expect(labels).toContain("Go to Studio Control Plane");
    expect(labels).toContain("Start GPU Box");
    expect(labels).toContain("Show keyboard cheat sheet");
    expect(labels.filter((l) => l.startsWith("Go to ")).length).toBe(PAGES.length);
    expect(cmds.map((c) => c.category)).toEqual([...cmds.map((c) => c.category)].sort(
      (a, b) => ["Navigate", "Box", "Help"].indexOf(a) - ["Navigate", "Box", "Help"].indexOf(b)));
  });

  it("claims nothing that is not implemented, and labels J as half speed", () => {
    const text = cheatSheetRows(BINDINGS).map((r) => `${r.description} ${r.group}`).join(" | ");
    expect(text).not.toMatch(/jump to stage/i);
    expect(text).not.toMatch(/waveform/i);
    const j = BINDINGS.find((b) => b.id === "review.rate-half")!;
    expect(j.description).toBe("Play at half speed");
    expect(j.description).not.toMatch(/reverse/i);
  });
});
