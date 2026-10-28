"use client";

import { useEffect, useState } from "react";

// A single take row as returned by GET /api/studio/takes or the pipeline service.
export interface ReviewTake {
  id: string;
  shotId: string;
  songId: string;
  sceneNumber: number;
  model: string | null;
  publicUrl: string;
  c2paStatus: string;
  hidden: boolean;
  createdAt: string;
}

interface ReviewRoomProps {
  songId: string;
  // Optional pre-loaded shots from the pipeline service (server component pass-through).
  initialShots?: ReviewTake[];
}

const STATUS_COLOR: Record<string, string> = {
  valid: "#3fb950",
  missing: "#d29922",
  invalid: "#f85149",
};

function TakeCard({ take }: { take: ReviewTake }) {
  return (
    <div className="bg-ink border border-edge rounded-lg p-3 flex gap-3 items-start">
      {take.publicUrl && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={take.publicUrl}
          alt={`take ${take.id}`}
          className="w-20 h-14 object-cover rounded shrink-0 bg-panel"
          onError={(e) => ((e.currentTarget as HTMLImageElement).style.display = "none")}
        />
      )}
      <div className="flex-1 min-w-0 text-xs">
        <div className="flex justify-between items-baseline mb-1">
          <span className="font-mono text-dim text-[10px]">{take.id.slice(0, 10)}…</span>
          <span style={{ color: STATUS_COLOR[take.c2paStatus] ?? "#888" }} className="font-semibold">
            C2PA: {take.c2paStatus}
          </span>
        </div>
        <div className="text-fg">
          Scene {take.sceneNumber} · Shot <span className="font-mono">{take.shotId.slice(0, 8)}…</span>
        </div>
        {take.model && <div className="text-dim mt-0.5">model: {take.model}</div>}
      </div>
    </div>
  );
}

// ReviewPanel: fetches shots from the pipeline service, falling back to the
// /api/studio/takes endpoint when the pipeline returns zero shots.
export function ReviewPanel({ songId, initialShots }: ReviewRoomProps) {
  const [takes, setTakes] = useState<ReviewTake[]>(initialShots ?? []);
  const [loading, setLoading] = useState(!initialShots);
  const [source, setSource] = useState<"pipeline" | "takes" | "initial">(
    initialShots ? "initial" : "pipeline",
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialShots && initialShots.length > 0) return;

    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        // 1. Try the pipeline service first.
        const pipelineRes = await fetch(`/api/studio/pipeline?externalId=${encodeURIComponent(songId)}`);
        if (!cancelled && pipelineRes.ok) {
          const pipelineData = await pipelineRes.json();
          const shots: ReviewTake[] = pipelineData?.shots ?? [];
          if (shots.length > 0) {
            setTakes(shots);
            setSource("pipeline");
            setLoading(false);
            return;
          }
        }

        // 2. Fallback: pull from the takes table.
        const takesRes = await fetch(`/api/studio/takes?songId=${encodeURIComponent(songId)}`);
        if (!cancelled) {
          if (takesRes.ok) {
            const takesData = await takesRes.json();
            const grouped: Record<string, ReviewTake[]> = takesData?.shots ?? {};
            const flat = Object.values(grouped).flat();
            setTakes(flat);
            setSource("takes");
          } else {
            setError("Failed to load takes.");
          }
        }
      } catch (e: unknown) {
        if (!cancelled) setError((e as Error)?.message ?? "Network error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [songId, initialShots]);

  if (loading) {
    return <div className="text-dim text-[13px] p-4">Loading review room…</div>;
  }
  if (error) {
    return <div className="text-[#f85149] text-[13px] p-4">Error: {error}</div>;
  }

  return (
    <section className="bg-panel border border-edge rounded-xl p-4">
      <div className="flex justify-between items-baseline mb-3">
        <h2 className="m-0 text-[15px] font-semibold">Review Room</h2>
        <span className="text-[11px] text-dim">
          {takes.length} take{takes.length !== 1 ? "s" : ""} · via {source}
        </span>
      </div>
      {takes.length === 0 ? (
        <div className="text-dim text-[13px]">No takes registered yet for song {songId}.</div>
      ) : (
        <div className="flex flex-col gap-2">
          {takes.map((t) => (
            <TakeCard key={t.id} take={t} />
          ))}
        </div>
      )}
    </section>
  );
}

// Default export: the full Review Room page wrapper.
export default function ReviewRoom({ songId, initialShots }: ReviewRoomProps) {
  return <ReviewPanel songId={songId} initialShots={initialShots} />;
}
