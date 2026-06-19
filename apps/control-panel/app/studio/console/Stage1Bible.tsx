"use client";
import { useEffect, useState } from "react";

// Stage-1 Bible checklist panel. Data-driven from apps/auto-studio/bible_checklist.json (served
// by the pipeline service). Each of the 6 dimensions surfaces its elements as a checklist with
// the inputs that element accepts: text, a generation prompt (Midjourney/Astria style), image or
// video evidence, harvested refs, a file (release), or json. Completion is read from the backend
// (bible_scaffold.status), so the folder tree and this UI never drift.
//
// Backend contract (pipeline service — see docs/BIBLE_OP.md):
//   GET  {pipe}/bible/{project}/checklist           -> { dimensions:[{key,name,what,elements:[
//          {key,name,what,required,inputs,done,detail,value?}]}] }
//   POST {pipe}/bible/{project}/element  {dim,key,text}
//   POST {pipe}/bible/{project}/generate {dim,key,prompt,model_family}   -> astria_refine/gather
//   POST {pipe}/bible/{project}/media    (multipart: dim,key,file)

type El = { key: string; name: string; what: string; required: boolean; inputs: string[]; done: boolean; detail: string; value?: string };
type Dim = { key: string; name: string; what: string; elements: El[] };

const DOT = (e: El) => e.done ? "#57c97a" : e.required ? "#ef6f6c" : "#8a8a8a";

export default function Stage1Bible({ pipe, project }: { pipe: string; project: string }) {
  const [dims, setDims] = useState<Dim[]>([]);
  const [open, setOpen] = useState<Record<string, boolean>>({ narrative: true });
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    try {
      const r = await fetch(`${pipe}/bible/${project}/checklist`);
      const d = await r.json(); setDims(d.dimensions || []);
    } catch { setMsg(`Pipeline service offline at ${pipe} — start studio_pipeline_service.py.`); }
  }
  useEffect(() => { if (project) load(); }, [project]);

  const k = (dim: string, el: string) => `${dim}.${el}`;
  async function post(path: string, body: any, tag: string) {
    setBusy(tag); setMsg("");
    try {
      const r = await fetch(`${pipe}/bible/${project}/${path}`, {
        method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
      const d = await r.json(); setMsg(d.ok ? "saved" : (d.error || "failed")); await load();
    } catch (e: any) { setMsg(`unreachable: ${e.message}`); } finally { setBusy(""); }
  }
  async function upload(dim: string, el: string, file: File) {
    setBusy(k(dim, el));
    const b64 = await new Promise<string>((res) => { const r = new FileReader(); r.onload = () => res(r.result as string); r.readAsDataURL(file); });
    try { await fetch(`${pipe}/bible/${project}/media`, { method: "POST", headers: { "content-type": "application/json" },
            body: JSON.stringify({ dim, key: el, filename: file.name, b64 }) }); setMsg("attached"); await load(); }
    catch (e: any) { setMsg(`upload failed: ${e.message}`); } finally { setBusy(""); }
  }

  const total = dims.flatMap(d => d.elements);
  const doneN = total.filter(e => e.done).length;
  const reqMissing = total.filter(e => e.required && !e.done).length;

  return (
    <div className="space-y-3 mb-4">
      <div className="flex items-center gap-3 text-[13px]">
        <span className="text-fg font-medium">Stage 1 — Bible</span>
        <span className="text-dim">{doneN}/{total.length} elements · </span>
        <span style={{ color: reqMissing ? "#ef6f6c" : "#57c97a" }}>{reqMissing} required missing</span>
        {msg && <span className="text-dim ml-2">{msg}</span>}
      </div>

      {dims.map((dim) => {
        const dDone = dim.elements.filter(e => e.done).length;
        return (
          <div key={dim.key} className="bg-ink border border-edge rounded-lg">
            <button onClick={() => setOpen(o => ({ ...o, [dim.key]: !o[dim.key] }))}
              className="w-full flex items-center justify-between px-3 py-2 text-left">
              <span className="text-[13px] text-fg">{dim.name} <span className="text-dim font-normal">— {dim.what}</span></span>
              <span className="text-[12px] text-dim">{dDone}/{dim.elements.length} {open[dim.key] ? "▾" : "▸"}</span>
            </button>

            {open[dim.key] && (
              <div className="px-3 pb-3 space-y-3 border-t border-edge pt-2">
                {dim.elements.map((el) => (
                  <div key={el.key} className="grid grid-cols-[10px_1fr] gap-2">
                    <span className="mt-1.5 w-2 h-2 rounded-full" style={{ background: DOT(el) }} title={el.done ? "done" : el.required ? "required" : "optional"} />
                    <div>
                      <div className="text-[12px] text-fg">{el.name}
                        {el.required && <span className="text-[10px] text-mauve ml-1">required</span>}
                        <span className="text-[11px] text-dim ml-2">{el.inputs.join(" · ")}</span>
                      </div>
                      <div className="text-[11px] text-dim mb-1">{el.what}</div>

                      {/* text / json input */}
                      {(el.inputs.includes("text") || el.inputs.includes("json")) && (
                        <div className="flex gap-1 mb-1">
                          <textarea value={draft[k(dim.key, el.key)] ?? el.value ?? ""} rows={2}
                            onChange={(e) => setDraft(s => ({ ...s, [k(dim.key, el.key)]: e.target.value }))}
                            placeholder={el.what} className="flex-1 bg-panel border border-edge rounded-md text-fg text-[12px] p-1.5" />
                          <button disabled={busy === k(dim.key, el.key)} onClick={() => post("element", { dim: dim.key, key: el.key, text: draft[k(dim.key, el.key)] || "" }, k(dim.key, el.key))}
                            className="text-[11px] border border-edge text-fg rounded-md px-2 self-start py-1 disabled:opacity-50">save</button>
                        </div>
                      )}

                      {/* generation prompt (Midjourney/Astria) */}
                      {el.inputs.includes("prompt") && (
                        <div className="flex gap-1 mb-1">
                          <input value={draft[k(dim.key, el.key) + ".p"] ?? ""} placeholder="generation prompt → Astria/Midjourney"
                            onChange={(e) => setDraft(s => ({ ...s, [k(dim.key, el.key) + ".p"]: e.target.value }))}
                            className="flex-1 bg-panel border border-mauve/40 rounded-md text-fg text-[12px] p-1.5" />
                          <button disabled={busy === k(dim.key, el.key)} onClick={() => post("generate", { dim: dim.key, key: el.key, prompt: draft[k(dim.key, el.key) + ".p"] || "", model_family: "flux" }, k(dim.key, el.key))}
                            className="text-[11px] border border-mauve/40 text-mauve rounded-md px-2 self-start py-1 disabled:opacity-50">generate</button>
                        </div>
                      )}

                      {/* image / video / file upload */}
                      {(el.inputs.includes("image") || el.inputs.includes("video") || el.inputs.includes("file")) && (
                        <label className="inline-block text-[11px] text-dim border border-dashed border-edge rounded-md px-2 py-1 cursor-pointer mb-1">
                          + attach {el.inputs.filter(i => ["image", "video", "file"].includes(i)).join("/")}
                          <input type="file" className="hidden"
                            accept={el.inputs.includes("video") ? "video/*" : el.inputs.includes("image") ? "image/*" : undefined}
                            onChange={(e) => e.target.files?.[0] && upload(dim.key, el.key, e.target.files[0])} />
                        </label>
                      )}

                      {/* harvested refs link */}
                      {el.inputs.includes("refs") && (
                        <div className="text-[11px] text-dim">refs: <span className="font-mono">{el.detail}</span></div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
