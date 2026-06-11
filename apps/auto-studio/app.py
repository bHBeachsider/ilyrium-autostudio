import streamlit as st
import os
import json
import base64
import anthropic
import requests
from dotenv import load_dotenv

# Load environment variables immediately so media scripts can see them.
# override=True forces .env to win over any stale inherited vars (e.g. a leftover
# XAI_API_KEY in the shell/profile that shadows the correct key in .env).
load_dotenv(override=True)

# Local render orchestrator (xAI video + ElevenLabs audio + moviepy + R2)
from producer import produce_campaign, render_shot, assemble_cut
import project_store as ps
import ad_studio_agent
import otio_export
import stage_agents
from media import apiframe as apiframe_client

# --- PAGE CONFIG ---
st.set_page_config(page_title="Ilyrium Auto-Studio", page_icon="🎬", layout="wide")

# --- CUSTOM CSS FOR UPLOADER BUTTONS ---
st.markdown("""
<style>
    /* Target the file uploader delete 'X' button */
    [data-testid="stFileUploaderDeleteBtn"] {
        background-color: #ff4b4b; /* Streamlit red */
        color: white;
        transform: scale(1.5); /* Make it 50% bigger */
        margin-right: 5px; /* Give it a little breathing room */
        border-radius: 50%;
    }
    
    /* Make it darker red when you hover over it */
    [data-testid="stFileUploaderDeleteBtn"]:hover {
        background-color: #c93a3a;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- HISTORIC CAMPAIGN LOADER HELPER ---
def get_saved_campaigns():
    """Scan outputs/ for past runs (newest first). Prefer manifest.json, but fall
    back to project.json — campaigns produced by the director / 'Render Now' path
    save project.json (not manifest.json), so they were previously invisible here.
    project.json shots are normalized to the manifest 'scenes' shape so loading works."""
    campaigns = {}
    outputs_dir = "outputs"
    if not os.path.exists(outputs_dir):
        return campaigns
    folders = [f for f in os.listdir(outputs_dir) if os.path.isdir(os.path.join(outputs_dir, f))]
    for folder in sorted(folders, reverse=True):  # timestamped names -> newest first
        fp = os.path.join(outputs_dir, folder)
        manifest_path = os.path.join(fp, "manifest.json")
        project_path = os.path.join(fp, "project.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    campaigns[folder] = json.load(f)
                    continue
            except Exception:
                pass
        if os.path.exists(project_path):
            try:
                with open(project_path, "r", encoding="utf-8") as f:
                    p = json.load(f)
                campaigns[folder] = {
                    "business_name": p.get("business_name"),
                    "vibe": p.get("vibe"),
                    "format": p.get("format"),
                    "scenes": [
                        {"scene_number": s.get("scene_number"),
                         "visual_prompt": s.get("visual_prompt", ""),
                         "voiceover": s.get("voiceover", "")}
                        for s in sorted(p.get("shots", []), key=lambda x: x.get("scene_number", 0))
                    ],
                }
            except Exception:
                pass
    return campaigns

# Initialize session states
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "draft_scenes" not in st.session_state:
    st.session_state.draft_scenes = []
if "loaded_business_name" not in st.session_state:
    st.session_state.loaded_business_name = "Ilyrium Bar & Grill"
if "loaded_vibe" not in st.session_state:
    st.session_state.loaded_vibe = "High-Energy & Loud"
if "loaded_format" not in st.session_state:
    st.session_state.loaded_format = "9:16 (Instagram Reels/TikTok)"
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "active_project_dir" not in st.session_state:
    st.session_state.active_project_dir = None

# --- SIDEBAR: NEW PROJECT ---
st.sidebar.header("🎬 Project")
if st.sidebar.button("🆕 New Project", use_container_width=True,
                     help="Clear the current script, chat, and uploads and start a fresh project."):
    st.session_state.chat_history = []
    st.session_state.draft_scenes = []
    st.session_state.loaded_business_name = "Ilyrium Bar & Grill"
    st.session_state.loaded_vibe = "High-Energy & Loud"
    st.session_state.loaded_format = "9:16 (Instagram Reels/TikTok)"
    st.session_state.uploader_key += 1
    st.session_state.active_project_dir = None
    st.toast("Started a new project.", icon="🆕")
    st.rerun()
st.sidebar.divider()

# --- SIDEBAR HISTORY PANEL ---
st.sidebar.header("📁 Campaign History")
saved_runs = get_saved_campaigns()

if saved_runs:
    selected_run = st.sidebar.selectbox("Select a past run", options=list(saved_runs.keys()))
    if st.sidebar.button("📂 Load Selected Campaign", use_container_width=True):
        manifest_data = saved_runs[selected_run]
        st.session_state.draft_scenes = manifest_data.get("scenes", [])
        st.session_state.loaded_business_name = manifest_data.get("business_name", "Ilyrium Bar & Grill")
        st.session_state.loaded_vibe = manifest_data.get("vibe", "High-Energy & Loud")
        st.session_state.loaded_format = manifest_data.get("format", "9:16 (Instagram Reels/TikTok)")
        # If this run has a project.json, make it the active project so the
        # Production Console can revise it shot by shot.
        st.session_state.active_project_dir = os.path.join("outputs", selected_run)
        st.sidebar.success(f"Loaded: {selected_run}")
        st.rerun()
else:
    st.sidebar.info("No saved local campaigns found yet. Run your first complete production to start a history!")

# --- SIDEBAR: CLOUD GPU (EC2 — ComfyUI / Unreal host) ---
st.sidebar.divider()
st.sidebar.header("☁️ Cloud GPU")
_ec2_action = None
try:
    import ec2_session
    _ec2 = ec2_session.status()
    _state = _ec2["state"]
    _emoji = {"running": "🟢", "stopped": "⚪", "pending": "🟡", "stopping": "🟡"}.get(_state, "⚪")
    st.sidebar.caption(f"{_emoji} {_state} · {_ec2.get('public_ip') or 'no public IP'}")
    _g1, _g2 = st.sidebar.columns(2)
    if _g1.button("▶ Start", use_container_width=True, disabled=(_state == "running")):
        _ec2_action = "start"
    if _g2.button("⏹ Stop", use_container_width=True, disabled=(_state == "stopped")):
        _ec2_action = "stop"
    st.sidebar.caption("ComfyUI: " + ("🟢 reachable" if ec2_session.is_comfyui_up() else "⚪ not reachable — start tunnel"))
except Exception as _ec2_err:
    st.sidebar.caption(f"EC2 status unavailable ({_ec2_err}). Check AWS creds / boto3.")

if _ec2_action:
    import ec2_session
    with st.spinner(f"{_ec2_action.capitalize()}ing the GPU box…"):
        (ec2_session.ensure_running if _ec2_action == "start" else ec2_session.stop)()
    st.rerun()

# --- MAIN UI ---
st.title("🎬 Ilyrium Auto-Studio")
st.subheader("AI Social Media Content Generator for Local Businesses")
st.divider()

# --- AD STUDIO: conversational director (primary, intuitive surface) ---
st.header("🎬 Ad Studio — talk to the director")
st.caption(
    "Describe your business and what you want. The director focuses the brief, writes the "
    "script, produces it, and revises it as you chat. Renders cost money and take a few minutes. "
    "(The manual tools below still work for hands-on control.)"
)

if "ad_messages" not in st.session_state:
    st.session_state.ad_messages = []      # Anthropic-format running conversation (with tool calls)
if "ad_display" not in st.session_state:
    st.session_state.ad_display = []       # [{role, text}] for rendering the chat

for _m in st.session_state.ad_display:
    with st.chat_message(_m["role"]):
        st.markdown(_m["text"])

with st.form("ad_studio_form", clear_on_submit=True):
    _ad_prompt = st.text_area(
        "Message the director",
        placeholder="e.g., I run a taco bar in Ft. Pierce and need a punchy 15s Instagram ad",
        height=80, label_visibility="collapsed",
    )
    _ad_files = st.file_uploader(
        "📎 Attach reference images and/or docs for the director — optional (style, product, character, brief, brand guide)",
        type=["png", "jpg", "jpeg", "webp", "md", "txt", "csv", "json"],
        accept_multiple_files=True, key="ad_dir_uploader",
    )
    _ad_sent = st.form_submit_button("➤ Send to director", use_container_width=True)

if _ad_sent and _ad_prompt.strip():
    # Thread attachments to the director: images -> vision blocks (Claude sees them);
    # text docs -> inline context. Images are persisted so they can later be locked
    # as a shot's first frame via set_script(source_image=...).
    _content, _n_imgs, _saved, _docs = [], 0, [], ""
    for _f in (_ad_files or []):
        try:
            _ext = _f.name.rsplit(".", 1)[-1].lower()
            if _ext in ("png", "jpg", "jpeg", "webp"):
                _mt = "image/jpeg" if _ext in ("jpg", "jpeg") else f"image/{_ext}"
                _content.append({"type": "image", "source": {
                    "type": "base64", "media_type": _mt,
                    "data": base64.b64encode(_f.getvalue()).decode("utf-8")}})
                _refdir = os.path.join("outputs", "_director_refs")
                os.makedirs(_refdir, exist_ok=True)
                _sp = os.path.join(_refdir, _f.name)
                with open(_sp, "wb") as _out:
                    _out.write(_f.getbuffer())
                _saved.append(_sp.replace("\\", "/"))
                _n_imgs += 1
            else:  # md / txt / csv / json -> inline text context
                _docs += f"\n\n--- Attached document: {_f.name} ---\n{_f.getvalue().decode('utf-8', errors='replace')[:8000]}\n"
        except Exception:
            pass
    _text = _ad_prompt
    if _docs:
        _text += "\n\n[Reference documents the user attached:]" + _docs
    if _saved:
        _text += ("\n\n[Reference image(s) attached and saved at: " + ", ".join(_saved) +
                  ". To lock a shot to one of these, set that scene's source_image to its path in set_script.]")
    _content.append({"type": "text", "text": _text})
    st.session_state.ad_display.append({"role": "user", "text": _ad_prompt + (f"  📎 {_n_imgs} image(s)" if _n_imgs else "")})
    st.session_state.ad_messages.append({"role": "user", "content": _content if _n_imgs else _ad_prompt})
    _ad_err = None
    with st.status("🎬 Director working… (focusing, scripting, or rendering)", expanded=True) as _adstat:
        try:
            _res = ad_studio_agent.run_agent_turn(
                st.session_state.ad_messages,
                st.session_state.get("active_project_dir"),
                progress_cb=lambda msg: st.write(msg),
            )
            st.session_state.ad_messages = _res["messages"]
            if _res.get("project_dir"):
                st.session_state.active_project_dir = _res["project_dir"]
            st.session_state.ad_display.append({"role": "assistant", "text": _res["assistant_text"]})
            _adstat.update(label="Director responded", state="complete")
        except Exception as e:
            _ad_err = e
            _adstat.update(label="Director error", state="error")
    if _ad_err:
        st.error(f"Ad Studio error: {_ad_err}")
    else:
        st.rerun()

st.divider()

# --- 1. CONSOLIDATED BRAND KIT & ARTIFACTS ---
st.header("🎯 1. Brand Kit & Campaign Context")
st.write("Define your brand settings and upload any text, images, or reference videos to ground the AI.")

# Create two columns to consolidate the UI
col1, col2 = st.columns(2)

with col1:
    business_name = st.text_input("Business Name", value=st.session_state.loaded_business_name)
    brand_color = st.color_picker("Primary Brand Color", "#D9534F")
    
    vibe_opts = ["High-Energy & Loud", "Chill & Relaxed", "Professional"]
    vibe_idx = vibe_opts.index(st.session_state.loaded_vibe) if st.session_state.loaded_vibe in vibe_opts else 0
    vibe = st.selectbox("Content Vibe", vibe_opts, index=vibe_idx)
    
    format_opts = ["9:16 (Instagram Reels/TikTok)", "16:9 (YouTube)"]
    format_idx = format_opts.index(st.session_state.loaded_format) if st.session_state.loaded_format in format_opts else 0
    output_format = st.selectbox("Output Format", format_opts, index=format_idx)

with col2:
    # 1. The Clear Button
    if st.button("🗑️ Clear Uploads", use_container_width=True, help="Wipe all uploaded files to start fresh."):
        st.session_state.uploader_key += 1 # Changing the key forces the uploader to reset
        st.rerun()

    # 2. Multimodal Uploader (Now using the dynamic key)
    uploaded_files = st.file_uploader(
        "Upload reference documents & media", 
        type=["txt", "md", "csv", "json", "png", "jpg", "jpeg", "mp4", "mov"], 
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.uploader_key}"
    )
    
    # Process files into memory
    text_context = ""
    image_context = []
    
    if uploaded_files:
        with st.expander("Preview Uploaded Artifacts", expanded=False):
            for file in uploaded_files:
                ext = file.name.split(".")[-1].lower()
                
                # 1. Handle Text
                if ext in ["txt", "md", "csv", "json"]:
                    try:
                        content = file.getvalue().decode("utf-8")
                        text_context += f"\n--- Document: {file.name} ---\n{content}\n"
                        st.caption(f"📄 Text loaded: {file.name}")
                    except Exception as e:
                        st.error(f"Could not read {file.name}: {e}")
                        
                # 2. Handle Images (Base64 encoding for Claude Vision)
                elif ext in ["png", "jpg", "jpeg"]:
                    st.image(file, caption=file.name, use_container_width=True)
                    encoded = base64.b64encode(file.getvalue()).decode("utf-8")
                    media_type = f"image/{ext if ext != 'jpg' else 'jpeg'}"
                    image_context.append({
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": encoded}
                    })
                    
                # 3. Handle Video (UI preview only)
                elif ext in ["mp4", "mov"]:
                    st.video(file)
                    st.caption(f"🎥 Video reference loaded: {file.name} (Visual reference only)")

st.divider()

# --- 2. SCRIPT GENERATION CHAT ---
st.header("💬 2. Script Generation Chat")

# Container to render the ongoing chat conversation safely
chat_container = st.container()

with chat_container:
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            if isinstance(msg["content"], list):
                for block in msg["content"]:
                    if block["type"] == "text":
                        st.markdown(block["text"])
                    elif block["type"] == "image":
                        st.caption("📎 [Image provided to AI]")
            else:
                st.markdown(msg["content"])

# Accept user chat inputs
if user_prompt := st.chat_input(f"e.g., Draft a script for {business_name}..."):
    
    # 1. Build the User Message Payload
    message_content = []
    
    if image_context:
        message_content.extend(image_context)
    
    message_content.append({"type": "text", "text": user_prompt})
    
    st.session_state.chat_history.append({"role": "user", "content": message_content})
    with chat_container:
        with st.chat_message("user"):
            st.markdown(user_prompt)
            if image_context:
                st.caption(f"📎 [+ {len(image_context)} image(s) attached]")
        
        # 2. Query Anthropic
        with st.chat_message("assistant"):
            with st.spinner("🧠 Claude is analyzing artifacts & thinking..."):
                client = anthropic.Anthropic()
                
                artifact_injection = ""
                if text_context:
                    artifact_injection = f"\n\n=== PROVIDED TEXT ARTIFACTS ===\n{text_context}\n===================================="
                
                system_prompt = f"""
                You are a creative director and social media manager. We are brainstorming video concepts for a local business.
                Business Profile: {business_name}
                Target Content Vibe: {vibe}
                Target Dimensions: {output_format}{artifact_injection}
                
                CRITICAL CONSISTENCY & SAFETY RULES:
                1. VISUAL ANCHORING (NO MEMORY): The video AI has zero memory between scenes. If your script features a specific person, you MUST copy/paste their exact physical description into EVERY SINGLE `visual_prompt`. 
                2. AUDIO SAFETY: The `voiceover` field MUST contain ONLY the exact English words to be spoken. NEVER use stage directions.
                
                FINALIZING THE SCRIPT: 
                Only when the user explicitly approves a final script, output the final script as a JSON array inside a markdown code block (using triple backticks and the word json). Each scene MUST have keys: "scene_number", "visual_prompt", "voiceover".
                """
            
                try:
                    response = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=3000,
                        system=system_prompt,
                        messages=st.session_state.chat_history
                    )
                    
                    claude_reply = response.content[0].text
                    st.markdown(claude_reply)
                    
                    st.session_state.chat_history.append({"role": "assistant", "content": claude_reply})
                    
                    # 3. Automatic JSON Extraction
                    if "```json" in claude_reply:
                        try:
                            raw_json = claude_reply.split("```json")[1].split("```")[0].strip()
                            st.session_state.draft_scenes = json.loads(raw_json)
                            st.toast("✨ Script successfully parsed!", icon="🚀")
                        except Exception as json_err:
                            st.error(f"⚠️ Failed to parse JSON: {json_err}")
                            
                except Exception as api_err:
                    st.error(f"❌ Anthropic API Connection Error: {api_err}")

# --- 3. REVIEW, EDIT & RENDER ---
if st.session_state.draft_scenes:
    st.divider()
    st.header("✍️ 3. Review & Edit Formatted Script")
    
    edited_scenes = []
    for i, scene in enumerate(st.session_state.draft_scenes):
        st.markdown(f"### Scene {i + 1}")
        
        col_v, col_a = st.columns(2)
        
        with col_v:
            visual_edit = st.text_area(
                "Visual Prompt", 
                value=scene.get("visual_prompt", ""), 
                key=f"visual_{i}",
                height=150
            )
        
        with col_a:
            audio_edit = st.text_area(
                "Voiceover",
                value=scene.get("voiceover", ""),
                key=f"audio_{i}",
                height=150
            )

        # Per-prompt input source (optional): attach a reference IMAGE (used as the
        # shot's keyframe first-frame -> continuity) or a CLIP (ingested directly).
        src_up = st.file_uploader(
            "📎 Reference image (keyframe first-frame) or clip — optional",
            type=["png", "jpg", "jpeg", "webp", "mp4", "mov", "m4v"],
            key=f"src_{i}",
            help="Image → used as the first frame and animated (locks the look across shots). "
                 "Video → ingested directly as this shot's clip (no generation).",
        )
        source_image = source_clip = None
        if src_up is not None:
            _updir = os.path.join("outputs", "_prompt_uploads")
            os.makedirs(_updir, exist_ok=True)
            _dest = os.path.join(_updir, f"scene{i + 1}_{src_up.name}")
            with open(_dest, "wb") as _f:
                _f.write(src_up.getbuffer())
            if (src_up.type or "").startswith("video"):
                source_clip = _dest
                st.caption(f"🎞️ Clip attached — will be ingested directly: {src_up.name}")
            else:
                source_image = _dest
                st.image(_dest, width=160, caption="Keyframe first-frame")

        _sc = {
            "scene_number": i + 1,
            "visual_prompt": visual_edit,
            "voiceover": audio_edit,
        }
        if source_image:
            _sc["source_image"] = source_image
        if source_clip:
            _sc["source_clip"] = source_clip
        edited_scenes.append(_sc)
        
    st.divider()
    
    # --- 4. PRODUCTION PIPELINE ---
    st.header("🎬 4. Send to Studio OS Pipeline")
    st.write("Ready to build? This will send your approved script to your Next.js backend for database tracking and async rendering.")
    
    if st.button("🚀 Send to Production Pipeline", use_container_width=True, type="primary"):
        import time
        
        # 1. Prepare the payload for Next.js mapping
        mapped_scenes = []
        for scene in edited_scenes:
            mapped_scenes.append({
                "scene_number": scene["scene_number"],
                "technical_visual_prompt": scene["visual_prompt"], 
                "clean_voiceover": scene["voiceover"] 
            })
            
        campaign_title = f"{business_name} - {vibe} Campaign"
        payload = {
            "title": campaign_title,
            "scenes": mapped_scenes
        }

        # 2. Fire to Next.js Database
        st.info("📡 Connecting to Studio OS API...")
        NEXTJS_API_URL = "http://localhost:3000/api/campaigns"
        
        try:
            response = requests.post(NEXTJS_API_URL, json=payload)
            
            if response.status_code == 201:
                data = response.json()
                st.success(f"✅ Success! Campaign ID: `{data['campaignId']}` created in Neon Database with {data['sceneCount']} scenes.")
                st.balloons()
                
                # 3. Save locally to maintain Streamlit sidebar history
                run_id = f"campaign_{int(time.time())}"
                output_dir = os.path.join("outputs", run_id)
                os.makedirs(output_dir, exist_ok=True)
                
                manifest_data = {
                    "business_name": business_name,
                    "vibe": vibe,
                    "format": output_format,
                    "scenes": edited_scenes
                }
                with open(os.path.join(output_dir, "manifest.json"), "w") as f:
                    json.dump(manifest_data, f, indent=4)
                    
            else:
                st.error(f"❌ Failed to send to Studio OS. Status Code: {response.status_code}")
                st.write(response.text)
                
        except requests.exceptions.ConnectionError:
            st.error("🚨 Could not connect to Studio OS. Is your Next.js server running on `http://localhost:3000`?")

    # --- 5. RENDER THE ACTUAL VIDEO (LOCAL + R2) ---
    st.divider()
    st.header("🎥 5. Render the Video")
    st.write(
        "Run the full production pipeline now: **xAI Grok** renders each scene, "
        "**ElevenLabs** generates the voiceovers, the clips are stitched into one "
        "commercial, and the master is uploaded to your **R2** bucket. "
        "This calls paid APIs and can take several minutes."
    )

    if st.button("🎬 Render Video Now (Local + R2)", use_container_width=True):
        with st.status("Rendering campaign… this can take a few minutes.", expanded=True) as status:

            def _cb(msg):
                st.write(msg)

            try:
                result = produce_campaign(
                    business_name=business_name,
                    vibe=vibe,
                    output_format=output_format,
                    scenes=edited_scenes,
                    upload_to_r2=True,
                    progress_cb=_cb,
                )
                st.session_state.active_project_dir = result.get("project_dir")

                final_video = result.get("final_video")
                if final_video and os.path.exists(final_video):
                    status.update(label="✅ Render complete!", state="complete")
                    st.success(f"Final video saved to: `{final_video}`")
                    st.video(final_video)
                    if result.get("public_url"):
                        st.write(f"☁️ **R2 URL:** {result['public_url']}")
                    # Surface any scenes that failed to render
                    failed = [s["scene_number"] for s in result.get("scene_results", []) if not s["video_ok"]]
                    if failed:
                        st.warning(f"Note: scene(s) {failed} failed to render and were skipped.")
                else:
                    status.update(label="❌ Render failed", state="error")
                    st.error("No final video was produced. Check the log above for which scenes failed.")

            except Exception as e:
                status.update(label="❌ Render crashed", state="error")
                st.error(f"Render error: {e}")


# --- 6. PRODUCTION CONSOLE: revise the project shot by shot (non-destructive) ---
_proj_dir = st.session_state.get("active_project_dir")
if _proj_dir and os.path.exists(os.path.join(_proj_dir, "project.json")):
    project = ps.load_project(_proj_dir)
    if project:
        st.divider()
        st.header("🎛️ 6. Production Console — revise shot by shot")
        st.caption(
            f"Project `{project['campaign_id']}` · regenerating a shot adds a new "
            f"take and never overwrites the others. Pick the take you want, then re-assemble the cut."
        )

        for shot in sorted(project["shots"], key=lambda s: s["scene_number"]):
            n = shot["scene_number"]
            st.markdown(f"#### Shot {n}")
            ok_takes = [t for t in shot.get("takes", []) if t.get("video")]

            col_prev, col_ctrl = st.columns([2, 1])
            with col_prev:
                sel_id = shot.get("selected_take")
                sel = ps.get_take(shot, sel_id) if sel_id else None
                if sel and sel.get("video") and os.path.exists(sel["video"]):
                    st.video(sel["video"])
                    st.caption(f"Selected: {sel_id} · model {sel.get('model')} · {len(ok_takes)} take(s)")
                else:
                    st.info("No usable take yet for this shot.")
                st.caption(shot.get("visual_prompt", "")[:160])

            with col_ctrl:
                if ok_takes:
                    options = [t["take_id"] for t in ok_takes]
                    current = sel_id if sel_id in options else options[0]
                    chosen = st.radio(
                        "Take in the cut", options, index=options.index(current),
                        key=f"take_select_{n}",
                    )
                    if chosen != shot.get("selected_take"):
                        ps.set_selected_take(project, n, chosen)
                        ps.save_project(_proj_dir, project)
                        st.rerun()

                _model = st.selectbox(
                    "Model", ["grok-imagine", "veo3", "veo3.1", "kling", "comfyui", "ue", "keyframe"],
                    key=f"model_{n}",
                    help="grok = fast draft · veo/kling = premium w/ dialogue · comfyui = self-hosted "
                         "controlled (EC2) · ue = Unreal 3D (prompt=level-sequence) · keyframe = "
                         "Midjourney still -> image-to-video (kernel-styled, consistent)",
                )
                _regen = st.button(f"🔄 Regenerate shot {n}", key=f"regen_{n}", use_container_width=True)
            if _regen:
                _err = None
                with st.status(f"Regenerating shot {n} via {_model}…", expanded=True) as s_status:
                    try:
                        render_shot(project, _proj_dir, n, model=_model, progress_cb=lambda m: st.write(m))
                        s_status.update(label=f"Shot {n}: new take added", state="complete")
                    except Exception as e:
                        _err = e
                        s_status.update(label="Regen failed", state="error")
                if _err:
                    st.error(f"{_err}")
                else:
                    st.rerun()

        st.divider()
        if st.button("🎬 Re-assemble cut from selected takes", use_container_width=True, type="primary"):
            with st.status("Assembling new cut…", expanded=True) as c_status:
                try:
                    cut = assemble_cut(project, _proj_dir, upload_to_r2=True,
                                       progress_cb=lambda m: st.write(m))
                    if cut.get("final_video") and os.path.exists(cut["final_video"]):
                        c_status.update(label=f"{cut['cut_id']} ready", state="complete")
                        st.success(f"New cut: {cut['final_video']}")
                        st.video(cut["final_video"])
                        if cut.get("public_url"):
                            st.write(f"☁️ R2: {cut['public_url']}")
                    else:
                        c_status.update(label="Assembly failed", state="error")
                        st.error("No cut produced — make sure shots have selected takes.")
                except Exception as e:
                    c_status.update(label="Assembly crashed", state="error")
                    st.error(f"{e}")

        # --- Music bed + finishing ---
        st.divider()
        st.subheader("🎵 Music & finishing")
        _mc1, _mc2 = st.columns(2)
        with _mc1:
            _music_file = st.file_uploader("Music bed (mp3/wav)", type=["mp3", "wav", "m4a"], key="music_up")
            _gain = st.slider("Music volume", 0.0, 1.0, float(project.get("music_gain", 0.15)), 0.05, key="music_gain_sl")
            if _music_file is not None:
                _music_path = os.path.join(_proj_dir, "music_bed" + os.path.splitext(_music_file.name)[1])
                with open(_music_path, "wb") as _mf:
                    _mf.write(_music_file.getvalue())
                project["music"] = _music_path
                project["music_gain"] = _gain
                ps.save_project(_proj_dir, project)
                st.caption(f"Music: {os.path.basename(_music_path)} — re-assemble the cut to hear it.")
            elif _gain != project.get("music_gain", 0.15):
                project["music_gain"] = _gain
                ps.save_project(_proj_dir, project)
            if project.get("music"):
                st.caption(f"Current music: {os.path.basename(project['music'])}")
            with st.expander("✨ Generate music with Suno (APIFrame)"):
                _sp = st.text_input("Describe the music", placeholder="upbeat warm acoustic, ~90 bpm", key="suno_prompt")
                _si = st.checkbox("Instrumental", value=True, key="suno_inst")
                if st.button("Generate music", key="suno_gen", use_container_width=True) and _sp.strip():
                    with st.status("Generating music via Suno…", expanded=True) as _ms:
                        try:
                            _mp = apiframe_client.generate_music(
                                _sp, os.path.join(_proj_dir, "music_bed.mp3"), instrumental=_si)
                            project["music"] = _mp
                            ps.save_project(_proj_dir, project)
                            _ms.update(label="Music generated", state="complete")
                            st.audio(_mp)
                            st.caption("Set as the bed — re-assemble the cut to mix it in.")
                        except Exception as e:
                            _ms.update(label="Music generation failed", state="error")
                            st.error(f"{e}")
        with _mc2:
            st.caption("Hand the rough cut to DaVinci Resolve for trims, color, and master render.")
            if st.button("🎞️ Export timeline (.otio) for DaVinci", use_container_width=True):
                try:
                    _otio = otio_export.export_project_otio(project, _proj_dir)
                    st.success(f"Exported: {_otio}")
                except Exception as e:
                    st.error(f"OTIO export failed: {e}")


# --- STUDIO ROOMS: per-stage ideation/refinement agents for scaffold film projects ---
st.divider()
st.header("🏛️ Studio Rooms — per-stage ideation agents")
st.caption(
    "Each pipeline stage of a scaffolded film project has a dedicated agent (Story Architect, "
    "Screenwriter, Cinematographer, …) grounded in the project's Style Kernel + casting canon. "
    "It reads project context and writes drafts into the stage folder. Autonomy A1: it proposes, you accept."
)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ilyrium-autostudio
_PROJECTS_DIR = os.path.join(_REPO_ROOT, "projects")
import project_paths as _project_paths
_room_project_map = dict(_project_paths.list_projects())   # "client/proj" or "proj" -> abs path
_room_projects = sorted(_room_project_map)

if not _room_projects:
    st.caption("No scaffolded projects yet — run `python scaffold.py \"Title\"` to create one under projects/.")
else:
    if "room_convos" not in st.session_state:
        st.session_state.room_convos = {}
    if "room_display" not in st.session_state:
        st.session_state.room_display = {}

    _rc1, _rc2 = st.columns(2)
    _sel_proj = _rc1.selectbox("Project", _room_projects, key="room_proj")
    _stages = stage_agents.list_stage_agents()
    _labels = [f"{f} · {persona}" for f, persona, title in _stages]
    _sel_i = _rc2.selectbox("Room (stage)", range(len(_stages)),
                            format_func=lambda i: _labels[i], key="room_stage")
    _stage_folder, _persona = _stages[_sel_i][0], _stages[_sel_i][1]
    _proj_path = _room_project_map.get(_sel_proj) or os.path.join(_PROJECTS_DIR, _sel_proj)
    _ckey = f"{_sel_proj}::{_stage_folder}"
    _disp = st.session_state.room_display.setdefault(_ckey, [])

    for _m in _disp:
        with st.chat_message(_m["role"]):
            st.markdown(_m["text"])

    with st.form(f"room_form_{_ckey}", clear_on_submit=True):
        _msg = st.text_area(f"Talk to the {_persona}", height=80, label_visibility="collapsed",
                            placeholder="e.g., draft a logline and three recurring world motifs")
        _room_files = st.file_uploader(
            "📎 Attach references/docs — optional",
            type=["png", "jpg", "jpeg", "webp", "md", "txt", "csv", "json"],
            accept_multiple_files=True, key=f"room_up_{_ckey}",
        )
        _send = st.form_submit_button(f"➤ Send to {_persona}", use_container_width=True)

    if _send and _msg.strip():
        _convo = st.session_state.room_convos.setdefault(_ckey, [])
        # Thread images as vision blocks + docs as inline text, like the director.
        _rc_content, _rc_docs, _rc_imgs = [], "", 0
        for _rf in (_room_files or []):
            try:
                _re = _rf.name.rsplit(".", 1)[-1].lower()
                if _re in ("png", "jpg", "jpeg", "webp"):
                    _rmt = "image/jpeg" if _re in ("jpg", "jpeg") else f"image/{_re}"
                    _rc_content.append({"type": "image", "source": {"type": "base64",
                        "media_type": _rmt, "data": base64.b64encode(_rf.getvalue()).decode("utf-8")}})
                    _rc_imgs += 1
                else:
                    _rc_docs += f"\n\n--- {_rf.name} ---\n{_rf.getvalue().decode('utf-8', errors='replace')[:8000]}\n"
            except Exception:
                pass
        _rc_text = _msg + (("\n\n[Attached documents:]" + _rc_docs) if _rc_docs else "")
        _rc_content.append({"type": "text", "text": _rc_text})
        _convo.append({"role": "user", "content": _rc_content if (_rc_imgs or _rc_docs) else _msg})
        _disp.append({"role": "user", "text": _msg + (f"  📎 {_rc_imgs} image(s)" if _rc_imgs else "") + (" 📄 doc(s)" if _rc_docs else "")})
        _rerr = None
        with st.status(f"{_persona} working…", expanded=True) as _rstat:
            try:
                _rres = stage_agents.run_stage_agent(_stage_folder, _proj_path, _convo,
                                                     progress_cb=lambda m: st.write(m))
                st.session_state.room_convos[_ckey] = _rres["messages"]
                _disp.append({"role": "assistant", "text": _rres["assistant_text"]})
                _rstat.update(label=f"{_persona} responded", state="complete")
            except Exception as e:
                _rerr = e
                _rstat.update(label="Room error", state="error")
        if _rerr:
            st.error(f"Studio Room error: {_rerr}")
        else:
            st.rerun()