// The key dispatcher (ILY-206 task 13): pure, no React, no DOM. KeysProvider attaches one
// window listener that calls dispatch(); everything that decides whether a key fires is
// here so node-only vitest can cover it.

import { isActivatable, isTextEntry, matches, parseChord, type Chord, type KeyLike, type TargetLike } from "./match";
import { BINDINGS, type BindingDef, type Scope } from "./registry";

export type KeyEventLike = KeyLike & {
  target?: TargetLike; repeat?: boolean; isComposing?: boolean; defaultPrevented?: boolean;
  preventDefault: () => void;
};
export type Handler = (e: KeyEventLike | null) => void;

export type KeyStore = ReturnType<typeof createKeyStore>;

export function createKeyStore(defs: readonly BindingDef[] = BINDINGS) {
  const strict = process.env.NODE_ENV !== "production";
  const byId = new Map(defs.map((d) => [d.id, d]));
  const chords = new Map(defs.map((d) => [d.id, d.keys.map(parseChord)] as [string, Chord[]]));
  const handlers = new Map<string, Handler[]>();
  const stack: Scope[] = [];   // active non-global scopes, oldest first
  let modalDepth = 0;

  const known = (id: string) => {
    if (!byId.has(id) && strict) throw new Error(`unknown key binding id "${id}"`);
    return byId.has(id);
  };

  return {
    /** Activate a scope; the returned function deactivates it. Global is always active. */
    pushScope(scope: Scope) {
      stack.push(scope);
      return () => { const i = stack.lastIndexOf(scope); if (i >= 0) stack.splice(i, 1); };
    },
    /** Register a handler for a binding id; the returned function removes exactly it. */
    register(id: string, handler: Handler) {
      if (!known(id)) return () => {};
      handlers.set(id, [...(handlers.get(id) ?? []), handler]);
      return () => {
        const rest = (handlers.get(id) ?? []).filter((h) => h !== handler);
        if (rest.length) handlers.set(id, rest); else handlers.delete(id);
      };
    },
    /** A modal (palette, cheat sheet, reject dialog) is open until the returned function is called. */
    modal() {
      modalDepth++;
      let done = false;
      return () => { if (!done) { done = true; modalDepth--; } };
    },
    has(id: string) { known(id); return handlers.has(id); },
    /** Run a binding's handler without a keyboard event (palette rows, buttons). */
    invoke(id: string) {
      known(id);
      const hs = handlers.get(id);
      if (!hs) return false;
      hs[hs.length - 1](null);
      return true;
    },
    /**
     * Returns true when a handler ran. Guard order matters:
     * composing/handled events first, then the chord, then focus (text fields and Space/Enter
     * on native controls), then modals, then scope and handler. Auto-repeat is last: it
     * swallows the default action without re-firing the handler.
     * Scopes are searched latest-pushed first and the first match wins, so exactly one
     * handler fires per key.
     */
    dispatch(e: KeyEventLike): boolean {
      if (e.isComposing || e.defaultPrevented) return false;
      const order: Scope[] = [...stack].reverse();
      order.push("global");
      for (const scope of order) {
        for (const def of defs) {
          if (def.scope !== scope) continue;
          const hit = chords.get(def.id)!.find((c) => matches(c, e));
          if (!hit) continue;
          if (isTextEntry(e.target) && !def.inFields) continue;
          if ((hit.key === " " || hit.key === "Enter") && isActivatable(e.target)) continue;
          if (modalDepth > 0 && !def.allowInModal && def.scope !== "palette") continue;
          const hs = handlers.get(def.id);
          if (!hs) continue;
          if (def.preventDefault !== false) e.preventDefault();
          // A held key still owns its default action (a held Space must not scroll the page),
          // but only bindings that opt in re-fire their handler.
          if (e.repeat && !def.repeat) return false;
          hs[hs.length - 1](e);
          return true;
        }
      }
      return false;
    },
  };
}
