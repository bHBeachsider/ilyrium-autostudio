"use client";

// Catches errors thrown by a page under the console layout. The layout (and Run's state)
// stays mounted. It does NOT catch errors from the layout itself; app/studio/error.tsx does.
export default function ConsoleError({ error, retry }: { error: unknown; retry: () => void }) {
  const message = error instanceof Error ? error.message : String(error);
  const digest = (error as { digest?: string } | null)?.digest;
  return (
    <section role="alert" className="bg-panel border border-edge rounded-xl p-8 max-w-xl">
      <h1 className="text-[20px] font-semibold mb-2">Something went wrong</h1>
      <p className="text-dim text-[14px] font-mono mb-1">{message}</p>
      {digest && <p className="text-dim text-[12px] font-mono mb-4">digest {digest}</p>}
      <button onClick={() => retry()} className="border border-edge text-fg rounded-md px-3 py-1.5 text-[14px] mt-2">Try again</button>
    </section>
  );
}
