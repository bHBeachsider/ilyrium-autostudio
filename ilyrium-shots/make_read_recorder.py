#!/usr/bin/env python3
"""
make_read_recorder.py — generate a per-strip LINE-READ recorder page.

Takes a strip project, joins each scene card's dialogue (and voiceover) to its
panel image, and emits ONE self-contained HTML file (panels embedded as base64)
that a remote contributor opens in any browser: they see the panel, the line,
and the delivery note, record per line, and download takes named to match the
pipeline (sNN__speaker__who_takeN.webm). No server, nothing uploaded.

USAGE
  python ilyrium-shots/make_read_recorder.py --project projects/broderick/broderick_torg
  python ilyrium-shots/make_read_recorder.py --project <dir> --character torg
  # -> <project>/06_audio/voice/read_recorder_<slug>[__<character>].html

Panel->card mapping mirrors panels_to_dataset.py (1:1 by order; evenly-divisible
chunking when one image holds several drawn panels).
"""
import argparse
import base64
import glob
import html
import json
import os
import sys

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp"}


def map_cards(images, cards):
    n_i, n_c = len(images), len(cards)
    if n_i == n_c:
        return {c["scene_number"]: images[i] for i, c in enumerate(cards)}
    if n_c > n_i and n_i and n_c % n_i == 0:
        k = n_c // n_i
        return {c["scene_number"]: images[min(i // k, n_i - 1)]
                for i, c in enumerate(cards)}
    return {c["scene_number"]: (images[i] if i < n_i else images[-1])
            for i, c in enumerate(cards)}


def b64(path):
    ext = os.path.splitext(path)[1].lower()
    data = base64.b64encode(open(path, "rb").read()).decode()
    return f"data:{MIME.get(ext,'image/png')};base64,{data}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--character", help="only lines for this speaker key "
                                        "(voiceover lines use key 'narrator')")
    a = ap.parse_args()

    proj = a.project.rstrip("/\\")
    slug = os.path.basename(proj)
    cards = json.load(open(os.path.join(proj, "02_script", "scenes.json"),
                           encoding="utf-8"))
    panels = [p for p in sorted(glob.glob(
        os.path.join(proj, "01_development", "bible", "panels", "*")))
        if os.path.splitext(p)[1].lower() in IMAGE_EXTS]
    if not panels:
        sys.exit(f"no panels in {proj}")
    panel_for = map_cards(panels, cards)

    jobs, img_cache = [], {}
    for c in cards:
        sn = c["scene_number"]
        lines = [(d.get("speaker", "unknown"), d.get("line", ""),
                  d.get("delivery", "")) for d in c.get("dialogue", [])]
        if c.get("voiceover"):
            lines.append(("narrator", c["voiceover"], c.get("performance", "")))
        for speaker, line, delivery in lines:
            if not line.strip():
                continue
            if a.character and speaker != a.character:
                continue
            src = panel_for.get(sn)
            if src not in img_cache:
                img_cache[src] = b64(src)
            jobs.append({"scene": sn, "speaker": speaker, "line": line,
                         "delivery": delivery, "img": img_cache[src]})
    if not jobs:
        sys.exit("no matching lines")

    cards_html = []
    for i, j in enumerate(jobs):
        cards_html.append(f"""
<div class="card line" data-stem="s{j['scene']:02d}__{html.escape(j['speaker'])}">
  <img src="{j['img']}" alt="panel s{j['scene']}">
  <div class="meta">
    <div class="who">Scene {j['scene']} — <b>{html.escape(j['speaker'])}</b>
      {('<span class="dir">[' + html.escape(j['delivery']) + ']</span>') if j['delivery'] else ''}</div>
    <div class="text">{html.escape(j['line'])}</div>
    <div class="ctl">
      <button class="rec">● Record</button>
      <button class="stop" disabled>■ Stop</button>
      <span class="timer">0:00</span>
    </div>
    <div class="takes"></div>
  </div>
</div>""")

    title = f"{slug}" + (f" — {a.character}" if a.character else "")
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Line reads — {html.escape(title)}</title>
<style>
 body{{font-family:system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 1rem;background:#161616;color:#eee}}
 h1{{font-size:1.25rem}} .card{{background:#222;border-radius:10px;padding:1rem 1.2rem;margin:.8rem 0}}
 .line{{display:flex;gap:1rem}} .line img{{width:300px;height:auto;align-self:flex-start;border-radius:6px;background:#fff}}
 .meta{{flex:1;min-width:0}} .who{{color:#bbb;margin-bottom:.3rem}} .dir{{color:#e8b339;margin-left:.4rem}}
 .text{{font-size:1.05rem;background:#1b1b1b;border-left:3px solid #c9302a;padding:.6rem .8rem;white-space:pre-wrap}}
 .ctl{{margin:.6rem 0}} button{{font-size:.95rem;padding:.45rem 1.1rem;border-radius:8px;border:0;cursor:pointer;margin-right:.5rem}}
 .rec{{background:#c9302a;color:#fff}} .stop{{background:#555;color:#fff}} button:disabled{{opacity:.4;cursor:default}}
 .take{{display:flex;align-items:center;gap:.6rem;margin:.35rem 0}} .take audio{{flex:1;height:30px}} a.dl{{color:#7ab8ff}}
 #level{{height:8px;background:#333;border-radius:4px;overflow:hidden;margin:.5rem 0}} #bar{{height:100%;width:0;background:#3fa34d}}
</style></head><body>
<h1>Line reads — {html.escape(title)}</h1>
<div class="card">
 <p>For each line: look at the panel, take the delivery note in <span class="dir">[amber]</span>, hit <b>Record</b>, read, <b>Stop</b>, then download the take. Quiet room, 15–20&nbsp;cm from the mic, no headphones. Stumble? Just record another take — keep them all.</p>
 <label>Your name: <input id="who" placeholder="e.g. brendan" style="background:#1b1b1b;color:#eee;border:1px solid #444;border-radius:6px;padding:.35rem"></label>
 <div id="level"><div id="bar"></div></div>
</div>
{''.join(cards_html)}
<script>
let ctx,analyser,stream,mediaRecorder,chunks=[],timerInt,active=null;
async function init(){{
 stream=await navigator.mediaDevices.getUserMedia({{audio:{{echoCancellation:false,noiseSuppression:false,autoGainControl:false,channelCount:1}}}});
 ctx=new AudioContext({{sampleRate:48000}});
 const src=ctx.createMediaStreamSource(stream);
 analyser=ctx.createAnalyser();analyser.fftSize=2048;src.connect(analyser);
 const mime=MediaRecorder.isTypeSupported('audio/webm;codecs=opus')?'audio/webm;codecs=opus':'';
 mediaRecorder=new MediaRecorder(stream,mime?{{mimeType:mime,audioBitsPerSecond:256000}}:{{}});
 mediaRecorder.ondataavailable=e=>chunks.push(e.data);
 mediaRecorder.onstop=saveTake;
 (function loop(){{const d=new Uint8Array(analyser.fftSize);analyser.getByteTimeDomainData(d);
  let p=0;for(const v of d)p=Math.max(p,Math.abs(v-128)/128);
  const bar=document.getElementById('bar');bar.style.width=(p*100)+'%';
  bar.style.background=p>.9?'#c9302a':p>.6?'#e8b339':'#3fa34d';requestAnimationFrame(loop);}})();
}}
document.querySelectorAll('.line').forEach(card=>{{
 const rec=card.querySelector('.rec'),stop=card.querySelector('.stop'),timer=card.querySelector('.timer');
 rec.onclick=async()=>{{if(!mediaRecorder)await init();
  chunks=[];active=card;mediaRecorder.start();const t0=Date.now();
  timerInt=setInterval(()=>{{const s=Math.floor((Date.now()-t0)/1000);timer.textContent=`${{Math.floor(s/60)}}:${{String(s%60).padStart(2,'0')}}`}},250);
  document.querySelectorAll('.rec').forEach(b=>b.disabled=true);stop.disabled=false;}};
 stop.onclick=()=>{{mediaRecorder.stop();clearInterval(timerInt);
  document.querySelectorAll('.rec').forEach(b=>b.disabled=false);stop.disabled=true;}};
}});
function saveTake(){{
 const card=active,who=(document.getElementById('who').value||'speaker').trim().toLowerCase().replace(/[^a-z0-9]+/g,'_');
 const n=card.querySelectorAll('.take').length+1;
 const blob=new Blob(chunks,{{type:mediaRecorder.mimeType||'audio/webm'}});
 const url=URL.createObjectURL(blob);
 const name=`${{card.dataset.stem}}__${{who}}_take${{n}}.webm`;
 const div=document.createElement('div');div.className='take';
 div.innerHTML=`<span>#${{n}}</span><audio controls src="${{url}}"></audio><a class="dl" href="${{url}}" download="${{name}}">⬇ ${{name}}</a>`;
 card.querySelector('.takes').appendChild(div);
}}
</script></body></html>"""

    out_dir = os.path.join(proj, "06_audio", "voice")
    os.makedirs(out_dir, exist_ok=True)
    suffix = f"__{a.character}" if a.character else ""
    out = os.path.join(out_dir, f"read_recorder_{slug}{suffix}.html")
    open(out, "w", encoding="utf-8").write(page)
    print(f"[ok] {out}  ({len(jobs)} lines, {len(img_cache)} panels embedded, "
          f"{os.path.getsize(out)//1024} KB)")


if __name__ == "__main__":
    main()
