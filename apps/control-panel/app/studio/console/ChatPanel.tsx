"use client";
import { useEffect, useRef, useState } from "react";
import type { BoxStatus } from "./BoxPanel";

// Multi-provider studio chat. A plain text conversation routed — message by
// message — to the provider picked in the dropdown, via POST /api/llm/chat
// (server-side dispatch; keys never reach the browser). Default = local qwen3
// on the box through the ollama tunnel. Unavailable providers stay listed but
// locked, so it's obvious what would light up if a key were configured.
type Prov = { id: string; label: string; available: boolean };
// A message is chat text OR a rendered image (with a download url).
type Msg = { role: "user" | "assistant"; content: string; provider?: string;
  imageUrl?: string; downloadUrl?: string; model?: string };

// Where the pipeline service lives (same host it uses elsewhere).
const PIPE = process.env.NEXT_PUBLIC_PIPE || "http://127.0.0.1:8800";
// On-box image models the render bar can drive (t2i slice).
const RENDER_MODELS = [
  { id: "comfyui:flux2", label: "FLUX.2 (flux2)" },
  { id: "comfyui:zimage", label: "Z-Image Turbo" },
];

export default function ChatPanel({ boxStatus }: { boxStatus?: BoxStatus | null }) {
  const [providers, setProviders] = useState<Prov[]>([]);
  const [provider, setProvider] = useState("local-qwen");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [renderModel, setRenderModel] = useState(RENDER_MODELS[0].id);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/llm/chat")
      .then((r) => r.json())
      .then((d) => {
        setProviders(d.providers || []);
        if (d.default) setProvider(d.default);
      })
      .catch(() => setErr("Could not load the provider list (/api/llm/chat)."));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [msgs, busy]);

  const tunnelDown = provider === "local-qwen" && boxStatus != null &&
    (boxStatus.state !== "running" || !boxStatus.tunnel_up);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setErr(""); setInput(""); setBusy(true);
    const history = [...msgs, { role: "user" as const, content: text }];
    setMsgs(history);
    try {
      const r = await fetch("/api/llm/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          provider,
          messages: history.map(({ role, content }) => ({ role, content })),
        }),
      });
      const d = await r.json();
      if (d.ok && typeof d.reply === "string") {
        // The chat route may attach an image when the model chose to generate one.
        setMsgs((m) => [...m, {
          role: "assistant", content: d.reply, provider: d.provider,
          imageUrl: d.image?.url, downloadUrl: d.image?.downloadUrl, model: d.image?.model,
        }]);
      } else {
        setErr(d.error || `request failed (${r.status})`);
      }
    } catch (e: any) {
      setErr(`chat request failed: ${e?.message || e}`);
    } finally {
      setBusy(false);
    }
  }

  // Render a still on the box from the prompt (text→image), show it inline with a download link.
  async function render() {
    const prompt = input.trim();
    if (!prompt || busy) return;
    setErr(""); setInput(""); setBusy(true);
    setMsgs((m) => [...m, { role: "user", content: `🎨 render: ${prompt}` }]);
    try {
      const r = await fetch(`${PIPE}/studio/render`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ prompt, model: renderModel }),
      });
      const d = await r.json();
      if (d.ok && d.url) {
        const url = `${PIPE}${d.url}`;
        setMsgs((m) => [...m, { role: "assistant", content: prompt, model: d.model,
          imageUrl: url, downloadUrl: `${url}&download=1` }]);
      } else {
        setErr(d.error || `render failed (${r.status})`);
      }
    } catch (e: any) {
      setErr(`render request failed (is the pipeline service + box up?): ${e?.message || e}`);
    } finally {
      setBusy(false);
    }
  }

  const current = providers.find((p) => p.id === provider);

  return (
    <div className="bg-panel border border-edge rounded-xl flex flex-col min-h-[60vh]">
      {/* header: provider picker */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-edge flex-wrap">
        <h3 className="text-[15px] font-semibold">💬 Studio Chat</h3>
        <select value={provider} onChange={(e) => { setProvider(e.target.value); setErr(""); }}
          className="bg-raised border border-edge rounded-md text-fg text-[13px] px-2 py-1.5 font-mono">
          {providers.map((p) => (
            <option key={p.id} value={p.id} disabled={!p.available}>
              {p.available ? "○ " : "🔒 "}{p.label}{p.available ? "" : " — no key set"}
            </option>
          ))}
        </select>
        <span className="text-[12px] text-dim">
          {provider === "local-qwen"
            ? "runs on your box via the ollama tunnel — no external provider in the loop"
            : "external provider — uses its server-side API key"}
        </span>
      </div>

      {/* transcript */}
      <div ref={scrollRef} className="flex-1 overflow-auto p-4 space-y-3">
        {msgs.length === 0 && (
          <div className="text-dim text-[14px]">
            Pick a provider and say something. Default is <span className="font-mono">local qwen3</span> on
            the EC2 box — start the box + tunnel in the Box panel if it isn&apos;t up.
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div className={"max-w-[85%] rounded-lg px-3 py-2 border text-[14px] whitespace-pre-wrap " +
              (m.role === "user" ? "bg-raised border-edge" : "bg-ink border-edge")}>
              {m.content}
              {m.imageUrl && (
                <div className="mt-2">
                  <img src={m.imageUrl} alt={m.content} className="rounded-md border border-edge max-w-full" />
                  <div className="flex items-center gap-3 mt-1.5 text-[11px]">
                    <a href={m.downloadUrl} download className="text-accent hover:underline">⬇ download</a>
                    <a href={m.imageUrl} target="_blank" rel="noreferrer" className="text-dim hover:underline">open full size</a>
                    {m.model && <span className="text-dim font-mono">{m.model}</span>}
                  </div>
                </div>
              )}
              {m.role === "assistant" && !m.imageUrl && (
                <div className="text-[11px] text-dim font-mono mt-1.5">— {m.provider}</div>
              )}
            </div>
          </div>
        ))}
        {busy && <div className="text-dim text-[13px]">… {current?.label || provider} is replying</div>}
      </div>

      {/* errors + hints */}
      {(err || tunnelDown) && (
        <div className="px-4 pb-1 space-y-1">
          {err && <div className="text-[13px]" style={{ color: "#ef6f6c" }}>{err}</div>}
          {tunnelDown && (
            <div className="text-[12px]" style={{ color: "#e0a13a" }}>
              local qwen3 needs the box + tunnel — use ▶ Start then 🔌 Tunnel in the Box panel.
            </div>
          )}
        </div>
      )}

      {/* composer — Send routes text to the LLM; Render makes an image on the box */}
      <div className="p-3 border-t border-edge space-y-2">
        <div className="flex gap-2">
          <textarea value={input} rows={2} placeholder={`Message ${current?.label || provider}…  (or type a prompt and hit Render)`}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            className="flex-1 bg-ink border border-edge rounded-md text-fg text-[14px] p-2 resize-none" />
          <button onClick={send} disabled={busy || !input.trim()}
            className="text-accent border border-accent/40 rounded-md px-4 text-[14px] disabled:opacity-40"
            style={{ background: "rgba(91,157,255,0.12)" }}>
            {busy ? "…" : "Send"}
          </button>
        </div>
        <div className="flex items-center gap-2 text-[12px]">
          <span className="text-dim">🎨 image:</span>
          <select value={renderModel} onChange={(e) => setRenderModel(e.target.value)}
            className="bg-raised border border-edge rounded-md text-fg text-[12px] px-2 py-1 font-mono">
            {RENDER_MODELS.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
          </select>
          <button onClick={render} disabled={busy || !input.trim()}
            className="text-mauve border border-mauve/40 rounded-md px-3 py-1 text-[12px] disabled:opacity-40"
            style={{ background: "rgba(180,142,255,0.12)" }}>
            {busy ? "rendering…" : "Render"}
          </button>
          <span className="text-dim">renders on the box → inline + download</span>
        </div>
      </div>
    </div>
  );
}
