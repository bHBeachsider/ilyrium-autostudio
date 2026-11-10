import { describe, expect, it, vi } from "vitest";
import { createKeyStore, type KeyEventLike } from "./store";

function key(k: string, extra: Partial<KeyEventLike> = {}) {
  const e = { key: k, target: { tagName: "BODY" }, preventDefault: vi.fn(), ...extra } as KeyEventLike & { preventDefault: ReturnType<typeof vi.fn> };
  return e;
}

/** A store with the review scope active and a spy on every review handler. */
function withReview() {
  const store = createKeyStore();
  const spies: Record<string, any> = {};
  const offs: (() => void)[] = [store.pushScope("review")];
  for (const id of ["review.approve", "review.reject", "review.pause", "review.playpause", "review.next", "review.frame-back"]) {
    spies[id] = vi.fn();
    offs.push(store.register(id, spies[id]));
  }
  return { store, spies, off: () => offs.forEach((f) => f()) };
}

describe("key store dispatch", () => {
  it("fires review bindings only while the scope is registered, and stops after unregister", () => {
    const store = createKeyStore();
    const approve = vi.fn();
    const unreg = store.register("review.approve", approve);
    expect(store.dispatch(key("a"))).toBe(false);          // scope not active yet
    const pop = store.pushScope("review");
    expect(store.dispatch(key("a"))).toBe(true);
    expect(approve).toHaveBeenCalledTimes(1);
    pop();
    expect(store.dispatch(key("a"))).toBe(false);
    pop(); unreg();
    expect(approve).toHaveBeenCalledTimes(1);
  });

  it("does not fire a bare key while a text field or select has focus", () => {
    const { store, spies } = withReview();
    expect(store.dispatch(key("a", { target: { tagName: "INPUT", type: "text" } }))).toBe(false);
    expect(store.dispatch(key("a", { target: { tagName: "SELECT" } }))).toBe(false);
    expect(spies["review.approve"]).not.toHaveBeenCalled();
  });

  it("still fires on a checkbox", () => {
    const { store, spies } = withReview();
    expect(store.dispatch(key("a", { target: { tagName: "INPUT", type: "checkbox" } }))).toBe(true);
    expect(spies["review.approve"]).toHaveBeenCalledTimes(1);
  });

  it("Ctrl+K fires palette.toggle once and never review.pause", () => {
    const { store, spies } = withReview();
    const toggle = vi.fn();
    store.register("palette.toggle", toggle);
    expect(store.dispatch(key("k", { ctrlKey: true }))).toBe(true);
    expect(toggle).toHaveBeenCalledTimes(1);
    expect(spies["review.pause"]).not.toHaveBeenCalled();
  });

  it("palette.toggle works while typing in a field", () => {
    const store = createKeyStore();
    const toggle = vi.fn();
    store.register("palette.toggle", toggle);
    expect(store.dispatch(key("k", { metaKey: true, target: { tagName: "TEXTAREA" } }))).toBe(true);
    expect(toggle).toHaveBeenCalledTimes(1);
  });

  it("does not prevent Alt+ArrowLeft (browser history)", () => {
    const { store } = withReview();
    const e = key("ArrowLeft", { altKey: true });
    expect(store.dispatch(e)).toBe(false);
    expect(e.preventDefault).not.toHaveBeenCalled();
  });

  it("prevents r, so the keystroke cannot land in the reject dialog's textarea", () => {
    const { store, spies } = withReview();
    const e = key("r");
    expect(store.dispatch(e)).toBe(true);
    expect(e.preventDefault).toHaveBeenCalledTimes(1);
    expect(spies["review.reject"]).toHaveBeenCalledTimes(1);
  });

  it("modal depth blocks review.approve but allows overlay.close and palette.toggle", () => {
    const { store, spies } = withReview();
    const close = vi.fn(), toggle = vi.fn();
    store.register("overlay.close", close);
    store.register("palette.toggle", toggle);
    const release = store.modal();
    expect(store.dispatch(key("a"))).toBe(false);
    expect(spies["review.approve"]).not.toHaveBeenCalled();
    expect(store.dispatch(key("Escape"))).toBe(true);
    expect(store.dispatch(key("k", { ctrlKey: true }))).toBe(true);
    expect(close).toHaveBeenCalledTimes(1);
    expect(toggle).toHaveBeenCalledTimes(1);
    release();
    expect(store.dispatch(key("a"))).toBe(true);
  });

  it("palette scope keys work inside the input while the palette is open", () => {
    const store = createKeyStore();
    const down = vi.fn();
    store.register("palette.down", down);
    expect(store.dispatch(key("ArrowDown", { target: { tagName: "INPUT", type: "text" } }))).toBe(false); // scope closed
    store.pushScope("palette");
    const release = store.modal();
    expect(store.dispatch(key("ArrowDown", { target: { tagName: "INPUT", type: "text" } }))).toBe(true);
    expect(down).toHaveBeenCalledTimes(1);
    release();
  });

  it("skips space on a button so it keeps its native activation", () => {
    const { store, spies } = withReview();
    const e = key(" ", { target: { tagName: "BUTTON" } });
    expect(store.dispatch(e)).toBe(false);
    expect(e.preventDefault).not.toHaveBeenCalled();
    expect(store.dispatch(key(" "))).toBe(true);
    expect(spies["review.playpause"]).toHaveBeenCalledTimes(1);
  });

  it("drops auto-repeat except for frame step", () => {
    const { store, spies } = withReview();
    expect(store.dispatch(key("a", { repeat: true }))).toBe(false);
    expect(store.dispatch(key("ArrowLeft", { repeat: true }))).toBe(true);
    expect(spies["review.approve"]).not.toHaveBeenCalled();
    expect(spies["review.frame-back"]).toHaveBeenCalledTimes(1);
  });

  it("a held Space keeps its default prevented (no page scroll) but never re-fires the handler", () => {
    const { store, spies } = withReview();
    const first = key(" ");
    expect(store.dispatch(first)).toBe(true);
    expect(spies["review.playpause"]).toHaveBeenCalledTimes(1);
    const held = key(" ", { repeat: true });
    expect(store.dispatch(held)).toBe(false);
    expect(held.preventDefault).toHaveBeenCalledTimes(1);
    expect(spies["review.playpause"]).toHaveBeenCalledTimes(1);
  });

  it("a repeated key in a text field, on a button or with no handler is left alone", () => {
    const { store } = withReview();
    const inField = key(" ", { repeat: true, target: { tagName: "TEXTAREA" } });
    const onButton = key(" ", { repeat: true, target: { tagName: "BUTTON" } });
    const unbound = key("n", { repeat: true });
    store.dispatch(inField); store.dispatch(onButton);
    expect(inField.preventDefault).not.toHaveBeenCalled();
    expect(onButton.preventDefault).not.toHaveBeenCalled();
    const bare = createKeyStore();
    bare.pushScope("review");
    expect(bare.dispatch(unbound)).toBe(false);          // no handler registered
    expect(unbound.preventDefault).not.toHaveBeenCalled();
  });

  it("Shift+Arrow still steps a frame, and holding it repeats", () => {
    const { store, spies } = withReview();
    expect(store.dispatch(key("ArrowLeft", { shiftKey: true }))).toBe(true);
    expect(store.dispatch(key("ArrowLeft", { shiftKey: true, repeat: true }))).toBe(true);
    expect(spies["review.frame-back"]).toHaveBeenCalledTimes(2);
  });

  it("an AltGr-typed backslash cycles A/B, but Ctrl+Alt+K is not K", () => {
    const store = createKeyStore();
    store.pushScope("review");
    const ab = vi.fn(), pause = vi.fn();
    store.register("review.ab", ab);
    store.register("review.pause", pause);
    expect(store.dispatch(key("\\", { ctrlKey: true, altKey: true }))).toBe(true);
    expect(ab).toHaveBeenCalledTimes(1);
    expect(store.dispatch(key("k", { ctrlKey: true, altKey: true }))).toBe(false);
    expect(pause).not.toHaveBeenCalled();
  });

  it("ignores composing and already-handled events", () => {
    const { store, spies } = withReview();
    expect(store.dispatch(key("a", { isComposing: true }))).toBe(false);
    expect(store.dispatch(key("a", { defaultPrevented: true }))).toBe(false);
    expect(spies["review.approve"]).not.toHaveBeenCalled();
  });

  it("fires exactly one handler per key, the latest registered for an id", () => {
    const store = createKeyStore();
    store.pushScope("review");
    const first = vi.fn(), second = vi.fn();
    store.register("review.approve", first);
    const off = store.register("review.approve", second);
    store.dispatch(key("a"));
    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledTimes(1);
    off();
    store.dispatch(key("a"));
    expect(first).toHaveBeenCalledTimes(1);
  });

  it("a synthetic window-like target does not break the guards", () => {
    const { store, spies } = withReview();
    expect(store.dispatch(key("a", { target: {} }))).toBe(true);
    expect(spies["review.approve"]).toHaveBeenCalledTimes(1);
  });

  it("invoke runs a handler without an event, and an unknown id throws", () => {
    const store = createKeyStore();
    const toggle = vi.fn();
    store.register("palette.toggle", toggle);
    expect(store.invoke("palette.toggle")).toBe(true);
    expect(toggle).toHaveBeenCalledWith(null);
    expect(store.invoke("box.start")).toBe(false);
    expect(() => store.invoke("nope.nope")).toThrow();
    expect(() => store.register("nope.nope", () => {})).toThrow();
  });
});
