"use client";

import { Activity, useLayoutEffect, useRef } from "react";

// Keeps Run alive while another page is open. Workspace lives in console/layout.tsx and
// renders Run itself (never [page]/page.tsx, whose client state would be lost on every
// navigation), so Run's stage, edits and open project survive leaving and returning.
//
// Activity hides the subtree with display:none, cleans up its effects (the 3 s run poll
// stops, WaveSurfer is destroyed, hotkey scopes deregister) and keeps state and DOM. On
// reveal every effect re-runs, so Run refetches GET /pipeline as before.
export default function RunSurface({ visible, children }: { visible: boolean; children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);

  // display:none does not stop media; a video left playing would keep its audio.
  useLayoutEffect(() => {
    if (!visible) return;
    const el = ref.current;
    return () => { el?.querySelectorAll("video, audio").forEach((m) => (m as HTMLMediaElement).pause()); };
  }, [visible]);

  return (
    <div ref={ref}>
      <Activity mode={visible ? "visible" : "hidden"}>{children}</Activity>
    </div>
  );
}
