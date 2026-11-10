import { describe, expect, it } from "vitest";
import { isActivatable, isTextEntry, matches, parseChord, type KeyLike } from "./match";

const ev = (key: string, mods: Partial<KeyLike> = {}): KeyLike => ({ key, ...mods });
const hit = (chord: string, e: KeyLike) => matches(parseChord(chord), e);

describe("matches", () => {
  it("a matches a and Caps-Lock A, but not Shift+A, Ctrl+A, Meta+A or Alt+A", () => {
    expect(hit("a", ev("a"))).toBe(true);
    expect(hit("a", ev("A"))).toBe(true);
    expect(hit("a", ev("A", { shiftKey: true }))).toBe(false);
    expect(hit("a", ev("a", { ctrlKey: true }))).toBe(false);
    expect(hit("a", ev("a", { metaKey: true }))).toBe(false);
    expect(hit("a", ev("a", { altKey: true }))).toBe(false);
  });

  it("bare k does not match Ctrl+K or Cmd+K, while mod+k matches both", () => {
    expect(hit("k", ev("k", { ctrlKey: true }))).toBe(false);
    expect(hit("k", ev("k", { metaKey: true }))).toBe(false);
    expect(hit("mod+k", ev("k", { ctrlKey: true }))).toBe(true);
    expect(hit("mod+k", ev("k", { metaKey: true }))).toBe(true);
    expect(hit("mod+k", ev("k"))).toBe(false);
  });

  it("? and backslash ignore shift", () => {
    expect(hit("?", ev("?", { shiftKey: true }))).toBe(true);
    expect(hit("?", ev("?"))).toBe(true);
    expect(hit("\\", ev("\\"))).toBe(true);
    expect(hit("\\", ev("\\", { shiftKey: true }))).toBe(true);
    expect(hit("?", ev("?", { ctrlKey: true }))).toBe(false);
  });

  it("an AltGr-typed printable non-letter matches its bare chord, a letter never does", () => {
    expect(hit("\\", ev("\\", { ctrlKey: true, altKey: true }))).toBe(true);
    expect(hit("\\", ev("\\", { getModifierState: (k: string) => k === "AltGraph" }))).toBe(true);
    expect(hit("?", ev("?", { ctrlKey: true, altKey: true, shiftKey: true }))).toBe(true);
    expect(hit("k", ev("k", { ctrlKey: true, altKey: true }))).toBe(false);
    // Ctrl or Alt alone still blocks a bare chord, and a mod chord is unaffected.
    expect(hit("\\", ev("\\", { ctrlKey: true }))).toBe(false);
    expect(hit("\\", ev("\\", { altKey: true }))).toBe(false);
    expect(hit("mod+k", ev("k", { ctrlKey: true, altKey: true }))).toBe(false);
  });

  it("shift+left matches only with Shift, and bare left still rejects it", () => {
    expect(hit("shift+left", ev("ArrowLeft", { shiftKey: true }))).toBe(true);
    expect(hit("shift+left", ev("ArrowLeft"))).toBe(false);
    expect(hit("shift+left", ev("ArrowLeft", { shiftKey: true, altKey: true }))).toBe(false);
  });

  it("named keys match exactly", () => {
    expect(hit("left", ev("ArrowLeft"))).toBe(true);
    expect(hit("left", ev("ArrowLeft", { altKey: true }))).toBe(false);
    expect(hit("left", ev("ArrowLeft", { shiftKey: true }))).toBe(false);
    expect(hit("space", ev(" "))).toBe(true);
    expect(hit("esc", ev("Escape"))).toBe(true);
    expect(hit("enter", ev("Enter"))).toBe(true);
  });

  it("rejects malformed chords", () => {
    expect(() => parseChord("hyper+k")).toThrow();
    expect(() => parseChord("")).toThrow();
    expect(() => parseChord("arrowleft")).toThrow();
  });
});

const el = (tagName: string, extra: object = {}) => ({ tagName, ...extra });

describe("isTextEntry", () => {
  it("is true for text fields, selects and contentEditable", () => {
    expect(isTextEntry(el("INPUT", { type: "text" }))).toBe(true);
    expect(isTextEntry(el("INPUT"))).toBe(true);
    expect(isTextEntry(el("TEXTAREA"))).toBe(true);
    expect(isTextEntry(el("SELECT"))).toBe(true);
    expect(isTextEntry(el("DIV", { isContentEditable: true }))).toBe(true);
    expect(isTextEntry(el("DIV", { getAttribute: (n: string) => (n === "role" ? "textbox" : null) }))).toBe(true);
  });

  it("is false for checkboxes, buttons, body and a window-like synthetic target", () => {
    expect(isTextEntry(el("INPUT", { type: "checkbox" }))).toBe(false);
    expect(isTextEntry(el("BUTTON"))).toBe(false);
    expect(isTextEntry(el("BODY"))).toBe(false);
    expect(isTextEntry({} as object)).toBe(false);
    expect(isTextEntry(null)).toBe(false);
    expect(isTextEntry(undefined)).toBe(false);
  });
});

describe("isActivatable", () => {
  it("is true for buttons, links with href, summary, role=button and checkboxes", () => {
    expect(isActivatable(el("BUTTON"))).toBe(true);
    expect(isActivatable(el("A", { getAttribute: (n: string) => (n === "href" ? "/x" : null) }))).toBe(true);
    expect(isActivatable(el("SUMMARY"))).toBe(true);
    expect(isActivatable(el("DIV", { getAttribute: (n: string) => (n === "role" ? "button" : null) }))).toBe(true);
    expect(isActivatable(el("INPUT", { type: "checkbox" }))).toBe(true);
  });

  it("is false for text inputs, an anchor with no href, body and a window-like target", () => {
    expect(isActivatable(el("INPUT", { type: "text" }))).toBe(false);
    expect(isActivatable(el("A", { getAttribute: () => null }))).toBe(false);
    expect(isActivatable(el("BODY"))).toBe(false);
    expect(isActivatable({} as object)).toBe(false);
    expect(isActivatable(null)).toBe(false);
  });
});
