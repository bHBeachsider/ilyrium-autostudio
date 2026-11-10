"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import { createKeyStore, type Handler, type KeyStore } from "./store";
import type { Scope } from "./registry";

const KeysContext = createContext<KeyStore | null>(null);

// The only keydown listener in the console. Mounted in console/layout.tsx.
export function KeysProvider({ children }: { children: React.ReactNode }) {
  const [store] = useState(createKeyStore);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { store.dispatch(e); };
    window.addEventListener("keydown", onKey);
    // Lets Playwright check that every cheat-sheet row has a live handler.
    if (process.env.NODE_ENV !== "production") (window as any).__ilyriumKeys = store;
    return () => window.removeEventListener("keydown", onKey);
  }, [store]);
  return <KeysContext.Provider value={store}>{children}</KeysContext.Provider>;
}

function useStore(): KeyStore {
  const store = useContext(KeysContext);
  if (!store) throw new Error("KeysProvider is missing");
  return store;
}

/** `invoke` runs a binding's handler with no key event; `has` says whether one is registered. */
export function useKeys() {
  const store = useStore();
  return { invoke: store.invoke, has: store.has };
}

/**
 * Register handlers for a scope while `active`. The set of handler ids must be the same on
 * every render of a call site; the handlers themselves are read from a ref refreshed each
 * render, so they always see current state and the effect never re-subscribes for them.
 * `active` is the owner's "I am visible" flag, not DOM focus.
 */
export function useKeyBindings(scope: Scope, active: boolean, handlers: Record<string, Handler>) {
  const store = useStore();
  const ref = useRef(handlers);
  ref.current = handlers;
  useEffect(() => {
    if (!active) return;
    const offs = scope === "global" ? [] : [store.pushScope(scope)];
    for (const id of Object.keys(ref.current)) offs.push(store.register(id, (e) => ref.current[id]?.(e)));
    return () => offs.forEach((off) => off());
  }, [store, scope, active]);
}

/** While `open`, only bindings marked allowInModal (and the palette's own) can fire. */
export function useKeyModal(open: boolean) {
  const store = useStore();
  useEffect(() => {
    if (!open) return;
    return store.modal();
  }, [store, open]);
}
